# Julep AI w/ Llama Setup Guide

## Tech Stack Overview
1. **Core**: Python 3.12+ with Julep SDK
2. **Database**: SQLite for persistent storage
3. **Vector Store**: ChromaDB for embeddings and semantic search
4. **Cache**: Redis for session management
5. **API**: Custom Llama endpoint via OpenAI-compatible API

## Detailed Configuration Steps

### Dependencies (requirements.txt)
```
julep==1.48.1
python-dotenv==1.0.1
redis==5.0.1
chromadb==0.4.22
sentence-transformers==2.5.1
python-magic==0.4.27
PyYAML==6.0.1
pydantic>=1.9.0
httpx>=0.23.0
ruamel-yaml>=0.18.6
```

### Environment Variables (.env)
```bash
# Required
JULEP_API_KEY=your_julep_api_key_here

# Optional (defaults shown)
OPENAI_API_BASE=https://api.openai.com
OPENAI_API_KEY=not-needed
SQLITE_DB_PATH=/workspaces/julep/storage/julep.db
CHROMA_DB_DIR=/workspaces/julep/storage/chromadb
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
LOG_LEVEL=INFO
LOG_FILE=/workspaces/julep/storage/logs/julep.log
```

### Project Structure
```
/workspaces/julep/
├── config/
│   ├── agent_config.example.yaml  # Template for agent configuration
│   ├── agent_config.yaml         # Your custom agent config (git-ignored)
│   └── memory_config.yaml       # Memory settings
├── storage/
│   ├── chromadb/
│   ├── logs/
│   └── julep.db
├── .env
├── .env.example
├── main.py
└── requirements.txt
```

### Agent Configuration Template (agent_config.example.yaml)
```yaml
name: "YourAgentName"
description: "Description of your agent"
model:
  provider: "openai"
  name: "gpt-4o-mini"  # Default model, can be overridden in .env
  settings:
    api_base: "https://api.openai.com"  # Default endpoint, can be overridden in .env
    max_tokens: 4096
    temperature: 0.7
    top_p: 0.95
memory:
  type: "persistent"
  storage:
    provider: "julep"
    backend: "sqlite"
    vector_store: "chroma"
    cache: "redis"
  settings:
    context_window: 4096
    max_tokens: 8192
    retention_period: "30d"
    embedding_model: "all-MiniLM-L6-v2"
    chunk_size: 512
    chunk_overlap: 50
session:
  type: "persistent"
  storage: "redis"
  settings:
    ttl: 86400  # 24 hours
    max_sessions_per_user: 10
    context_strategy: "sliding_window"
```

### Memory Configuration (memory_config.yaml)
```yaml
vector_store:
  provider: "chroma"
  settings:
    collection_name: "julep_memories"
    persist_directory: "/workspaces/julep/storage/chromadb"
    embedding_function: "all-MiniLM-L6-v2"

persistent_storage:
  provider: "sqlite"
  settings:
    database_path: "/workspaces/julep/storage/julep.db"
    tables:
      conversations: "conversations"
      messages: "messages"
      metadata: "conversation_metadata"

cache:
  provider: "redis"
  settings:
    ttl:
      session: 86400
      context: 3600
```

## Quick Start Steps

1. Create required directories:
```bash
mkdir -p /workspaces/julep/storage/{chromadb,logs}
touch storage/.gitkeep
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up agent configuration:
```bash
cp config/agent_config.example.yaml config/agent_config.yaml
# Edit agent_config.yaml with your model settings
```

5. Start Redis:
```bash
redis-server --daemonize yes
```

6. Run the application:
```bash
python main.py
```

## Component Details

### SQLite (Persistent Storage)
- Single-file database for conversations and metadata
- Zero-configuration required
- Built-in Python support
- Automatic schema creation

### ChromaDB (Vector Store)
- Embedded vector database
- Efficient semantic search
- Local storage of embeddings
- Automatic persistence

### Redis (Session Management)
- Fast in-memory caching
- Session state management
- Real-time context handling
- Configurable TTLs

## System Benefits
- Minimal setup requirements
- No external services needed (except Redis)
- Persistent storage in workspace
- Efficient memory management
- Full Julep compatibility
- Development ready

## Security Notes
- API keys stored in .env (not in git)
- Agent configuration stored separately (not in git)
- Default OpenAI API base in code, override in .env
- Redis runs locally by default
- All storage paths configurable
- Sensitive data handled securely
