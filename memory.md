# Memory System Analysis

## Documentation References
- SQLite: https://sqlite.org/docs.html
- ChromaDB: https://docs.trychroma.com/
- Redis: https://redis.io/docs/latest/
- Julep API: https://dev.julep.ai/api/docs

## Overview
The memory system in this Julep AI implementation uses a multi-layered approach:
- SQLite for persistent storage of conversations and metadata
- ChromaDB for vector embeddings and semantic search
- Redis for fast session-based memory caching

## SQLite Integration

### Database Schema
```sql
-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Messages table with foreign key constraint
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    content TEXT NOT NULL,
    role TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE
);

-- Memory facts table
CREATE TABLE memory_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_type TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Create indexes for performance
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_memory_facts_type ON memory_facts(fact_type);
```

### SQLite Configuration
```python
# Database connection with recommended pragmas
pragmas = {
    'journal_mode': 'WAL',          # Write-Ahead Logging for better concurrency
    'cache_size': -64 * 1000,       # 64MB cache
    'foreign_keys': 'ON',           # Enable foreign key constraints
    'synchronous': 'NORMAL',        # Balance durability and speed
    'temp_store': 'MEMORY',         # Store temp tables in memory
    'mmap_size': 64 * 1024 * 1024  # 64MB mmap size
}
```

## ChromaDB Integration

### Collection Strategy
```python
# Collection naming convention
collection_name: "julep_memories"  # Matches our agent_config.yaml

# Metadata structure
metadata = {
    "source": "user_input",
    "timestamp": "ISO-8601 timestamp",
    "session_id": "unique_session_id",
    "type": "fact|context|preference"
}

# Document structure
documents = {
    "text": "processed_user_input",
    "embeddings": "all-MiniLM-L6-v2 vectors",
    "metadata": metadata
}
```

### Embedding Configuration
- Model: all-MiniLM-L6-v2 (384-dimensional embeddings)
- Chunking: 512 tokens with 50 token overlap
- Distance Function: Cosine Similarity (ChromaDB default)
- Persistence: Local disk storage in storage/chromadb/

### Query Strategy
```python
# Example query configuration
query_config = {
    "n_results": 5,  # Top relevant memories
    "where": {"type": "fact"},  # Metadata filtering
    "where_document": {"$contains": "relevant_context"}
}
```

## Redis Integration

### Session Configuration
```python
# Redis connection settings
redis_config = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Connection pool for better performance
pool = redis.ConnectionPool(**redis_config)
redis_client = redis.Redis(connection_pool=pool)
```

### Data Structures
```python
# Session data using Redis Hash
session_key = f"session:{session_id}"
session_data = {
    "user_id": user_id,
    "current_topic": "Python frameworks",
    "context": json.dumps(context_data),
    "last_active": timestamp
}
redis_client.hset(session_key, mapping=session_data)
redis_client.expire(session_key, 86400)  # 24 hour TTL

# Conversation history using Redis List
history_key = f"history:{session_id}"
redis_client.lpush(history_key, json.dumps(message))
redis_client.ltrim(history_key, 0, 99)  # Keep last 100 messages
redis_client.expire(history_key, 86400)

# Active sessions using Redis Set
active_sessions = "active_sessions"
redis_client.sadd(active_sessions, session_id)
```

### Memory Management
```python
# Memory usage monitoring
def check_memory_usage():
    info = redis_client.info(section="memory")
    used_memory = info["used_memory_human"]
    peak_memory = info["used_memory_peak_human"]
    return used_memory, peak_memory

# Memory cleanup for expired sessions
def cleanup_expired_sessions():
    for session in redis_client.smembers("active_sessions"):
        if not redis_client.exists(f"session:{session}"):
            redis_client.srem("active_sessions", session)
```

### Session Handling
```python
class SessionManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "session:"

    def create_session(self, session_id, data):
        key = f"{self.prefix}{session_id}"
        pipeline = self.redis.pipeline()
        pipeline.hset(key, mapping=data)
        pipeline.expire(key, 86400)
        pipeline.sadd("active_sessions", session_id)
        pipeline.execute()

    def get_session(self, session_id):
        key = f"{self.prefix}{session_id}"
        if not self.redis.exists(key):
            return None
        self.redis.expire(key, 86400)  # Refresh TTL
        return self.redis.hgetall(key)

    def update_session(self, session_id, updates):
        key = f"{self.prefix}{session_id}"
        if self.redis.exists(key):
            self.redis.hset(key, mapping=updates)
            self.redis.expire(key, 86400)
```

## Memory Types

### 1. Factual Memory
Stores concrete, factual information about users or topics:
```sql
-- SQLite storage
INSERT INTO memory_facts (fact_type, content, confidence, metadata)
VALUES (
    'user_fact',
    'Occupation: software engineer; Preferences: coffee',
    1.0,
    json('{"categories": ["occupation", "preferences"]}')
);

-- ChromaDB Document
{
    "text": "Occupation: software engineer; Preferences: coffee",
    "metadata": {
        "type": "fact",
        "categories": ["occupation", "preferences"],
        "sqlite_id": 1  -- Reference to SQLite record
    }
}
```

### 2. Contextual Memory
Maintains conversation context and related information:
```
User: "I prefer working on backend systems"
ChromaDB Document:
{
    "text": "Preference for backend development work",
    "metadata": {
        "type": "context",
        "related_to": "occupation",
        "confidence": 0.95
    }
}
```

### 3. Session Memory
Temporary information relevant to current conversation:
```python
# Redis implementation
session_data = {
    "session_id": "unique_id",
    "current_topic": "Python frameworks",
    "scope": "technical",
    "context": {
        "last_message_id": "msg_123",
        "conversation_state": "active",
        "user_preferences": {"technical_level": "expert"}
    },
    "metadata": {
        "client_info": "web_interface",
        "session_start": timestamp,
        "last_active": timestamp
    }
}

# Store in Redis with proper expiration
redis_client.hset(f"session:{session_id}", mapping=session_data)
redis_client.expire(f"session:{session_id}", 86400)  # 24 hour TTL

# Track active sessions
redis_client.sadd("active_sessions", session_id)
```

## Memory Flow with SQLite and ChromaDB

1. **Transaction Management**
   ```python
   # Ensure ACID compliance
   with sqlite3.connect('memory.db') as conn:
       conn.execute('BEGIN TRANSACTION')
       try:
           # Store in SQLite
           cursor = conn.execute(
               'INSERT INTO memory_facts (fact_type, content) VALUES (?, ?)',
               ('user_fact', processed_text)
           )
           sqlite_id = cursor.lastrowid

           # Store in ChromaDB with reference
           collection.add(
               documents=[text],
               embeddings=[embedding],
               metadatas=[{"sqlite_id": sqlite_id, **metadata}]
           )
           conn.commit()
       except Exception as e:
           conn.rollback()
           raise
   ```

2. **Retrieval Strategy**
   ```python
   def get_relevant_memories(query_text):
       # Search vector store
       results = collection.query(
           query_embeddings=[query_embedding],
           n_results=5
       )

       # Fetch full context from SQLite
       sqlite_ids = [m['sqlite_id'] for m in results.metadatas[0]]
       with sqlite3.connect('memory.db') as conn:
           memories = conn.execute('''
               SELECT * FROM memory_facts
               WHERE id IN (%s)
               ''' % ','.join('?' * len(sqlite_ids)),
               sqlite_ids
           ).fetchall()
       return memories
   ```

## Implementation Details

### SQLite Optimization
```python
# Connection pooling
def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(
            'memory.db',
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Apply optimal pragmas
        for pragma, value in pragmas.items():
            g.sqlite_db.execute(f'PRAGMA {pragma}={value}')
    return g.sqlite_db
```

### Memory Lifecycle

1. **Ingestion**
   - Text preprocessing
   - Metadata extraction
   - Embedding generation
   - ChromaDB storage
   - Redis caching (if session-relevant)

2. **Maintenance**
   - Regular embedding updates
   - Metadata refreshing
   - Collection optimization
   - Cache invalidation

3. **Retrieval**
   - Context-aware querying
   - Metadata filtering
   - Result ranking
   - Cache integration

## Best Practices

1. **SQLite Optimization**
   - Use Write-Ahead Logging (WAL)
   - Implement proper indexing
   - Use prepared statements
   - Manage transactions correctly
   - Regular VACUUM maintenance

2. **Data Integrity**
   - Enable foreign key constraints
   - Use appropriate column constraints
   - Implement proper error handling
   - Regular database maintenance

3. **Performance Considerations**
   - Optimize query patterns
   - Use appropriate indexes
   - Implement connection pooling
   - Regular database optimization

4. **Security and Privacy**
   - Use parameterized queries
   - Implement access controls
   - Regular backups
   - Secure file permissions

### Redis Best Practices

1. **Connection Management**
   - Use connection pooling
   - Implement proper timeout handling
   - Monitor connection health
   - Handle reconnection gracefully

2. **Data Structure Selection**
   - Use Hashes for session data
   - Lists for conversation history
   - Sets for active session tracking
   - Sorted Sets for time-based queries

3. **Memory Optimization**
   - Set appropriate TTLs
   - Monitor memory usage
   - Implement cleanup routines
   - Use pipelining for bulk operations

4. **Performance Tuning**
   - Enable persistence appropriately
   - Configure client-side caching
   - Use Redis pipelining
   - Implement proper error handling

5. **Security Considerations**
   - Enable protected mode
   - Use strong passwords
   - Implement access controls
   - Regular security audits

## System Integration & Compatibility

### Julep Integration
```python
# Initialize Julep client with memory components
from julep import Client
from julep.memory import MemoryManager

class JulepMemorySystem:
    def __init__(self, config):
        # Initialize storage components
        self.sqlite_conn = self._init_sqlite()
        self.chroma_client = self._init_chroma()
        self.redis_client = self._init_redis()

        # Initialize Julep client
        self.julep_client = Client(
            api_key=config.julep_api_key,
            base_url=config.openai_api_base
        )

        # Initialize memory manager
        self.memory_manager = MemoryManager(
            sqlite_conn=self.sqlite_conn,
            chroma_client=self.chroma_client,
            redis_client=self.redis_client
        )

    def create_agent(self, config):
        return self.julep_client.create_agent(
            config=config,
            memory_manager=self.memory_manager
        )

    async def process_message(self, agent, message):
        # Store message in SQLite
        msg_id = self._store_message(message)

        # Generate and store embeddings
        self._store_embeddings(message, msg_id)

        # Update session state
        self._update_session(message)

        # Get relevant context
        context = self._get_context(message)

        # Process with Julep agent
        response = await agent.process(
            message=message,
            context=context
        )

        return response

### Component Interactions
1. **Julep ↔ SQLite**
   - Persistent storage for conversations
   - Transaction management
   - Message history tracking

2. **Julep ↔ ChromaDB**
   - Semantic search for context
   - Vector storage for embeddings
   - Relevance scoring

3. **Julep ↔ Redis**
   - Session state management
   - Short-term memory cache
   - Real-time context updates

### Configuration Alignment
```yaml
# agent_config.yaml
memory:
  sqlite:
    database: "storage/memory.db"
    pragmas:
      journal_mode: "WAL"
      cache_size: -64000

  chroma:
    collection: "julep_memories"
    persist_directory: "storage/chromadb"
    embedding_model: "all-MiniLM-L6-v2"

  redis:
    host: "localhost"
    port: 6379
    ttl: 86400
```

### Compatibility Notes
1. **SQLite Compatibility**
   - WAL mode supported by Julep
   - JSON extension available
   - Foreign key constraints enabled
   - Prepared statements used

2. **ChromaDB Compatibility**
   - Collection persistence verified
   - Embedding model supported
   - Metadata schema aligned
   - Query patterns compatible

3. **Redis Compatibility**
   - Connection pooling supported
   - Data structures verified
   - TTL management aligned
   - Pipeline operations enabled

4. **Performance Considerations**
   - Concurrent access handled
   - Memory usage optimized
   - Connection pooling implemented
   - Error handling coordinated
