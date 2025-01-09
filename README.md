# Julep AI w/ Llama

A Python application that integrates Julep AI with a custom Llama model endpoint, providing a flexible and powerful AI agent system with persistent memory and efficient caching.

## Features

- 🤖 Custom Llama model integration via OpenAI-compatible API
- 💾 Persistent storage with SQLite
- 🧠 Vector embeddings with ChromaDB
- ⚡ Fast caching with Redis
- 🔒 Secure environment configuration
- 📝 Comprehensive logging system

## Prerequisites

- Python 3.12+
- Redis server
- Git
- A Julep API key from [dev.julep.ai](https://dev.julep.ai)

## Installation & Setup

Please refer to [setup.md](setup.md) for detailed installation and configuration instructions.

## Project Structure

```
Julep-AI-Llama/
├── config/
│   ├── agent_config.example.yaml  # Template for agent configuration
│   ├── agent_config.yaml         # Your custom agent config (git-ignored)
│   └── memory_config.yaml       # Memory settings
├── storage/
│   ├── chromadb/           # Vector embeddings storage
│   ├── logs/               # Application logs
│   └── julep.db            # SQLite database
├── .env                    # Environment variables
├── .env.example           # Environment template
├── main.py               # Main application
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Development

### Code Style

This project follows:
- PEP 8 style guide
- Type hints throughout
- Google-style docstrings
- Black code formatting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Julep AI](https://dev.julep.ai) for the agent framework
- The Llama model community
- All contributors to this project
