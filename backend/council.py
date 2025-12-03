"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
import re
import toon
import json
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from .tools import get_available_tools
from .memory import CouncilMemorySystem


async def stage1_collect_responses(
    user_query: str,
    context: Optional[List[Dict[str, Any]]] = None,
    conversation_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        context: Previous messages for conversation continuity

    Returns:
        Tuple of (stage1_results, tool_outputs)
    """
    # Build messages with context
    messages = []

    # Add context if available
    if context and len(context) > 0:
        # Take last 6 messages (3 exchanges) to avoid token limit
        recent_context = context[-6:]

        # Build context summary
        context_text = "Previous conversation:\n\n"
        for msg in recent_context:
            if msg['role'] == 'user':
                context_text += f"User: {msg['content']}\n\n"
            elif msg['role'] == 'assistant' and 'stage3' in msg:
                # Use final council answer from Stage 3
                final_answer = msg['stage3']['response']
                # Truncate if too long (keep first 200 chars)
                if len(final_answer) > 200:
                    final_answer = final_answer[:200] + "..."
                context_text += f"Council: {final_answer}\n\n"

        # Add context as system message
        messages.append({
            "role": "system",
            "content": context_text.strip()
        })

    # Memory-based context
    memory_ctx = ""
    if conversation_id:
        memory = CouncilMemorySystem(conversation_id)
        memory_ctx = memory.get_context(user_query)
        if memory_ctx:
            messages.append({"role": "system", "content": f"Relevant past exchanges:\n{memory_ctx}"})

    # Add tool context if the query suggests tool usage
    tool_outputs: List[Dict[str, str]] = []
    if requires_tools(user_query):
        tool_outputs = run_tools_for_query(user_query)
        if tool_outputs:
            tool_text = "Tool outputs:\n" + "\n".join(
                f"- {item['tool']}: {item['result']}" for item in tool_outputs
            )
            messages.append({"role": "system", "content": tool_text})

    # Add current query
    messages.append({"role": "user", "content": user_query})

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results, tool_outputs


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    tool_outputs: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman using TOON format
    # TOON reduces token usage by 30-60% compared to JSON/text formatting
    stage1_text = toon.encode(stage1_results)
    stage2_text = toon.encode(stage2_results)

    tools_text = ""
    if tool_outputs:
        tools_text = "TOOL OUTPUTS:\n" + "\n".join(
            f"- {t.get('tool')}: {t.get('result')}" for t in tool_outputs
        )

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses (TOON format):
{stage1_text}

STAGE 2 - Peer Rankings (TOON format):
{stage2_text}

{tools_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def _has_finance_signal(query: str) -> bool:
    q = query.lower()
    finance_signals = {"price", "stock", "stocks", "shares", "ticker", "market cap", "quote"}
    return any(sig in q for sig in finance_signals)


def _has_calc_signal(query: str) -> bool:
    q = query.lower()
    calc_signals = {"calculate", "compute", "math", "sum", "multiply", "divide", "add", "subtract"}
    return any(sig in q for sig in calc_signals)


def _has_search_signal(query: str) -> bool:
    q = query.lower()
    search_signals = {"search", "latest", "news", "current", "recent"}
    return any(sig in q for sig in search_signals)


def _has_research_signal(query: str) -> bool:
    q = query.lower()
    research_signals = {"wikipedia", "wiki", "research", "paper", "arxiv", "definition", "history"}
    return any(sig in q for sig in research_signals)


def requires_tools(query: str) -> bool:
    """Heuristic: only run tools when signals are clear."""
    return (
        _has_finance_signal(query)
        or _has_calc_signal(query)
        or _has_search_signal(query)
        or _has_research_signal(query)
    )


def run_tools_for_query(query: str, limit: int = 3) -> List[Dict[str, str]]:
    """
    Run available tools against the query to enrich context.
    Returns a list of {tool, result} entries.
    """
    results: List[Dict[str, str]] = []
    tools = get_available_tools()
    stock_tool = next((t for t in tools if t.name == "stock_data"), None)
    web_tool = next((t for t in tools if t.name == "web_search"), None)
    finance_intent = _has_finance_signal(query)

    # If ticker-like symbols are present, try them first (in order)
    if finance_intent:
        tickers = extract_ticker_candidates(query)
        if tickers and stock_tool:
            results.extend(run_stock_for_tickers(stock_tool, tickers, limit))
            if results:
                return results

        # Fallback: try to infer tickers from web search output, then query stock tool
        if not results and stock_tool and web_tool:
            try:
                web_output = web_tool.run(query)
                inferred_tickers = extract_ticker_candidates(str(web_output))
                if inferred_tickers:
                    results.extend(run_stock_for_tickers(stock_tool, inferred_tickers, limit))
                    if results:
                        return results
            except Exception:
                pass

    for tool in tools:
        # Skip stock tool here; handled above
        if tool.name == "stock_data":
            continue
        # Skip web tool if it was already used for inference
        if tool.name == "web_search" and web_tool is not None:
            continue
        if len(results) >= limit:
            break
        # Skip tools that don't match intent
        if tool.name == "calculator":
            if not _has_calc_signal(query):
                continue
        if tool.name == "wikipedia" or tool.name == "arxiv":
            if not _has_research_signal(query):
                continue
        if tool.name == "web_search":
            if not _has_search_signal(query):
                continue
        try:
            output = tool.run(query)
            if output:
                # Truncate very long outputs to keep prompts tight
                if isinstance(output, str) and len(output) > 500:
                    output = output[:500] + "..."
                results.append({"tool": tool.name, "result": str(output)})
        except Exception:
            # Silently skip tool failures to avoid breaking the request path
            continue

    return results


def run_stock_for_tickers(stock_tool, tickers: List[str], limit: int) -> List[Dict[str, str]]:
    """Run stock tool for a list of tickers and return valid price outputs."""
    results: List[Dict[str, str]] = []
    seen = set()

    for ticker in tickers:
        if len(results) >= limit:
            break
        if ticker in seen:
            continue
        seen.add(ticker)
        try:
            output = stock_tool.run(ticker)
            if not output:
                continue
            output_str = str(output)
            # Treat responses with a dollar sign or price marker as valid
            if "$" in output_str or "price=" in output_str.lower():
                results.append({"tool": stock_tool.name, "result": output_str})
        except Exception:
            continue

    return results


def extract_ticker_candidates(text: str) -> List[str]:
    """
    Extract probable stock tickers from text.
    Returns a list ordered by appearance; includes simple name->ticker mappings.
    """
    if not text:
        return []

    stop_words = {
        "THE", "AND", "FOR", "WITH", "TODAY", "PRICE", "STOCK", "STOCKS", "HOW",
        "WHAT", "IS", "ARE", "OF", "IN", "ON", "TO", "BY", "VS", "VERSUS", "GOOD",
        "BETTER", "BAD", "SHARE", "SHARES", "MARKET", "QUESTION", "ABOUT"
    }

    name_map = {
        "APPLE": "AAPL",
        "TESLA": "TSLA",
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "MICROSOFT": "MSFT",
        "AMAZON": "AMZN",
        "META": "META",
        "FACEBOOK": "META",
        "NVIDIA": "NVDA",
        "NETFLIX": "NFLX",
        "AMD": "AMD",
        "IBM": "IBM",
        "SHOPIFY": "SHOP",
        "SNOW": "SNOW",
    }

    tokens = re.findall(r"\b[A-Z]{1,10}\b", text.upper())
    seen = set()
    candidates: List[str] = []

    for tok in tokens:
        mapped = name_map.get(tok)
        if mapped:
            if mapped not in seen:
                seen.add(mapped)
                candidates.append(mapped)
            continue

        if tok in stop_words:
            continue

        if 1 <= len(tok) <= 5:
            if tok not in seen:
                seen.add(tok)
                candidates.append(tok)

    return candidates


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str, conversation_id: Optional[str] = None) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses (+ tool outputs)
    stage1_results, tool_outputs = await stage1_collect_responses(user_query, conversation_id=conversation_id)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        tool_outputs=tool_outputs
    )

    # Save exchange to memory
    if conversation_id:
        memory = CouncilMemorySystem(conversation_id)
        memory.save_exchange(user_query, stage3_result.get("response", ""))

    # Calculate token savings from TOON
    token_savings = calculate_token_savings(stage1_results, stage2_results)

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "token_savings": token_savings,
        "tool_outputs": tool_outputs
    }

    return stage1_results, stage2_results, stage3_result, metadata


def calculate_token_savings(
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate token savings from using TOON format.

    Args:
        stage1_results: Stage 1 responses
        stage2_results: Stage 2 rankings

    Returns:
        Dict with token counts and savings
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")

        # Calculate tokens for JSON format
        json_str = json.dumps({"stage1": stage1_results, "stage2": stage2_results})
        json_tokens = len(enc.encode(json_str))

        # Calculate tokens for TOON format
        toon_str = toon.encode({"stage1": stage1_results, "stage2": stage2_results})
        toon_tokens = len(enc.encode(toon_str))

        saved = json_tokens - toon_tokens
        percent = (saved / json_tokens * 100) if json_tokens > 0 else 0

        return {
            "json_tokens": json_tokens,
            "toon_tokens": toon_tokens,
            "saved_tokens": saved,
            "saved_percent": round(percent, 1)
        }
    except Exception as e:
        # If token calculation fails, return empty dict
        return {
            "json_tokens": 0,
            "toon_tokens": 0,
            "saved_tokens": 0,
            "saved_percent": 0,
            "error": str(e)
        }
