# LLM Council - Features

## Overview
LLM Council is a multi-model AI system that combines responses from multiple AI models through a democratic voting process, delivering superior answers through collective intelligence.

---

## Core Features

### 🎯 **3-Stage Council Process**
The heart of LLM Council - a democratic approach to AI responses:

1. **Stage 1: Individual Responses**
   - Multiple AI models respond independently to your question
   - Each model brings its unique perspective and strengths
   - Responses are collected in parallel for speed

2. **Stage 2: Peer Ranking**
   - Each model evaluates and ranks all responses anonymously
   - Blind peer review eliminates model bias
   - Aggregate rankings determine the best answers

3. **Stage 3: Final Synthesis**
   - Chairman model synthesizes insights from all stages
   - Combines best aspects of top-ranked responses
   - Delivers a comprehensive, well-reasoned answer

**Models Used:**
- Council Members: `google/gemini-2.0-flash-exp`, `anthropic/claude-3.5-sonnet`, `qwen/qwen2.5-7b-instruct`
- Chairman: `anthropic/claude-3.5-sonnet`

---

## Feature 1: TOON Integration

### 📦 **Token Optimization via TOON Format**
TOON (Tree Object Notation) reduces token usage by 30-60% compared to JSON/text.

**Benefits:**
- Saves costs on API calls
- Faster response times
- More efficient data transfer
- Real-time token savings display in UI

**Implementation:**
- Stage 1 & 2 responses compressed with TOON
- Automatic token counting with tiktoken
- Displays: `JSON tokens`, `TOON tokens`, `Saved %`

---

## Feature 2: Database Migration

### 💾 **Multi-Database Storage Backend**
Flexible storage with automatic switching based on configuration.

**Supported Backends:**
- **JSON Files** (default) - Zero setup, works immediately
- **PostgreSQL** - Production-ready, ACID compliant
- **MySQL** - Popular, widely supported

**Key Features:**
- Unified storage API - same code works with all backends
- Automatic database initialization
- SQLAlchemy models for PostgreSQL/MySQL
- Environment variable configuration (`DATABASE_TYPE`)

**Storage Schema:**
```sql
conversations (
  id VARCHAR(36) PRIMARY KEY,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  title VARCHAR(500),
  messages JSON  -- Native JSONB in PostgreSQL
)
```

---

## Feature 3: Follow-up Questions with Context

### 💬 **Conversation Memory & Context**
Natural multi-turn conversations with full context awareness.

**How It Works:**
- Last 6 messages (3 exchanges) sent as context
- Context passed to all council members
- Enables follow-up questions and clarifications
- Seamless conversation continuity

**Benefits:**
- "What about X?" style questions work naturally
- Models understand conversation history
- No need to repeat previous information
- Smarter, context-aware responses

---

## Feature 4: Advanced AI Capabilities

### 🛠️ **Tool Integration**
5 free tools + 1 optional paid tool for enhanced capabilities.

**FREE Tools (Always Available):**
1. **Calculator** - Python REPL for calculations
2. **Wikipedia** - Factual information lookup
3. **ArXiv** - Research paper search
4. **DuckDuckGo** - Web search for current info
5. **Yahoo Finance** - Stock prices and market data

**PAID Tools (Optional):**
- **Tavily** - Advanced web search (requires API key + flag)

**Auto-Detection:**
- System detects when tools are needed
- Automatically selects appropriate tool
- Results fed into council discussion
- Tool outputs shown in metadata

### 🧠 **Memory System**
Vector-based memory for conversation recall across sessions.

**Features:**
- ChromaDB vector store per conversation
- Semantic search for relevant past exchanges
- FREE local embeddings (HuggingFace)
- OPTIONAL OpenAI embeddings (better quality)

**How It Works:**
- Each conversation has its own memory collection
- Past exchanges stored as vectors
- Relevant context retrieved automatically
- Enhances long-term conversation continuity

### 🔀 **LangGraph Support**
Graph-based workflow orchestration (advanced feature).

**Status:** Framework ready, disabled by default
- Set `ENABLE_LANGGRAPH=true` to activate
- Complex routing and conditional workflows
- Most users don't need this

---

## Feature 5: Conversation Management

### 🗑️ **Delete Conversations**
Remove unwanted conversations with confirmation.

**Features:**
- 3-dot menu (⋮) for actions
- Confirmation dialog before deletion
- Works with all storage backends
- Auto-clears current conversation if deleted

### ✏️ **Edit Conversation Titles**
Inline title editing for better organization.

**Features:**
- Click ✏️ in 3-dot menu
- Inline text input appears
- Press Enter to save, Escape to cancel
- Real-time UI updates across all views

**Keyboard Shortcuts:**
- `Enter` - Save changes
- `Escape` - Cancel editing

### 💬 **Temporary Chat Mode**
Private conversations that don't save to storage.

**Use Cases:**
- Sensitive queries
- Quick one-off questions
- Testing without cluttering history

**Implementation:**
- Backend API ready (`temporary: true` flag)
- No storage persistence
- No title generation
- No memory tracking

---

## Additional Features

### 🎨 **Modern UI/UX**
- Clean, professional interface
- Real-time streaming responses
- Stage-by-stage progress indicators
- Token savings display
- Responsive design

### 🔒 **Privacy & Security**
- Local-first JSON storage option
- Optional database backends
- Temporary chat mode for sensitive data
- No data leaves your server (except API calls to AI providers)

### ⚡ **Performance**
- Parallel API calls to all models
- Streaming responses for instant feedback
- TOON compression saves 30-60% tokens
- Efficient database queries with indexes

### 🔧 **Configuration**
- Environment variable based setup
- Flag-based feature control
- Easy API key management
- Multiple storage backend options

---

## Technical Stack

### Backend:
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - ORM for database operations
- **LangChain** - Tool integration framework
- **ChromaDB** - Vector database for memory
- **TOON** - Token-efficient data format

### Frontend:
- **React** - UI library
- **Vite** - Build tool and dev server
- **Server-Sent Events** - Real-time streaming

### AI/ML:
- **OpenRouter** - Multi-model API gateway
- **HuggingFace** - Free local embeddings
- **Sentence Transformers** - Text embedding models

---

## Configuration Flags

### Database:
```bash
DATABASE_TYPE=json          # json, postgresql, or mysql
POSTGRESQL_URL=...          # If using PostgreSQL
MYSQL_URL=...               # If using MySQL
```

### Feature 4 - Tools & Memory:
```bash
# Free tools (always enabled)
# - Calculator, Wikipedia, ArXiv, DuckDuckGo, Yahoo Finance

# Paid tools (optional)
ENABLE_TAVILY=false         # Advanced web search
TAVILY_API_KEY=

# Memory system
ENABLE_MEMORY=true          # Vector-based conversation memory
ENABLE_OPENAI_EMBEDDINGS=false  # Use OpenAI embeddings (vs free local)
OPENAI_API_KEY=

# Advanced features
ENABLE_LANGGRAPH=false      # Graph-based workflows
```

---

## Feature Comparison

| Feature | Free Tier | Premium (Optional) |
|---------|-----------|-------------------|
| 3-Stage Council | ✅ | ✅ |
| TOON Compression | ✅ | ✅ |
| Database Storage | ✅ | ✅ |
| Context Memory | ✅ | ✅ |
| Calculator | ✅ | ✅ |
| Wikipedia | ✅ | ✅ |
| ArXiv Search | ✅ | ✅ |
| DuckDuckGo Search | ✅ | ✅ |
| Yahoo Finance | ✅ | ✅ |
| Local Embeddings | ✅ | ✅ |
| Conversation Management | ✅ | ✅ |
| Tavily Search | ❌ | ✅ (API key) |
| OpenAI Embeddings | ❌ | ✅ (API key) |
| LangGraph | ✅ | ✅ |

---

## Roadmap

### Planned Features:
- [ ] Conversation folders/tags
- [ ] Export conversations (Markdown, PDF)
- [ ] Custom model selection
- [ ] Prompt templates
- [ ] API usage statistics
- [ ] Multi-user support
- [ ] Dark mode
- [ ] Mobile responsive design
- [ ] Keyboard shortcuts
- [ ] Conversation search

### Potential Integrations:
- [ ] More AI providers (Groq, Together AI)
- [ ] More tools (Google Scholar, WolframAlpha)
- [ ] Voice input/output
- [ ] Image generation
- [ ] Code execution sandbox
- [ ] Document Q&A

---

## Credits

**Core Technologies:**
- OpenRouter for multi-model API access
- TOON format for token optimization
- LangChain for tool orchestration
- ChromaDB for vector storage

**Open Source Libraries:**
- FastAPI, React, SQLAlchemy, Vite
- HuggingFace Transformers
- Sentence Transformers

---

## License & Contributing

This is an open-source project. Contributions welcome!

**Key Features for Contributors:**
- Clean, modular architecture
- Storage backend abstraction
- Flag-based feature control
- Comprehensive documentation
- Professional code standards

For detailed implementation guides, see:
- `contributions/feature1_plan.md` - TOON Integration
- `contributions/feature2_plan.md` - Database Migration
- `contributions/feature3_plan.md` - Context & Follow-ups
- `contributions/feature4_plan.md` - Tools & Memory
- `contributions/feature5.md` - Conversation Management
