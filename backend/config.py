"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
# NOTE: Free-tier friendly defaults; swap back to premium list when you add credit.
# Premium set (commented): 
# COUNCIL_MODELS = [
#     "openai/gpt-5.1",
#     "google/gemini-3-pro-preview",
#     "anthropic/claude-sonnet-4.5",
#     "x-ai/grok-4",
# ]
COUNCIL_MODELS = [
    "google/gemma-2-9b-it",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen2.5-7b-instruct",
    "meta-llama/llama-3.2-3b-instruct",
]

# Chairman model - synthesizes final response
# CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
CHAIRMAN_MODEL = "google/gemma-2-9b-it"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
