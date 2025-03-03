# AORBIT

![AORBIT Banner](https://via.placeholder.com/800x200?text=AORBIT)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/package%20manager-uv-green.svg)](https://github.com/astral-sh/uv)
[![CI](https://github.com/ameen-alam/AgentOrchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/ameen-alam/AgentOrchestrator/actions/workflows/ci.yml)

**AORBIT**: A powerful, production-grade framework for deploying AI agents with enterprise-grade security - perfect for financial applications and sensitive data processing.

## 🚀 Quick Start (5 minutes)

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-username/AORBIT.git
cd AORBIT

# Set up environment with UV
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Set up your .env file (copy from example)
cp .env.example .env

# Run the server
python main.py
```

Your server is now running at http://localhost:8000! 🎉

### Using Docker (even faster)

```bash
# Clone the repository
git clone https://github.com/your-username/AORBIT.git
cd AORBIT

# Windows PowerShell
.\scripts\run_environments.ps1 -Environment dev -Build

# Linux/macOS
./scripts/run_environments.sh dev --build
```

The development environment will be available at http://localhost:8000.

## 🤖 Create Your First Agent (2 minutes)

1. Create a new directory in `src/routes/my_first_agent/`
2. Create a file `ao_agent.py` with this template:

```python
from typing import Dict, Any
from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

@task
def generate_greeting(name: str) -> str:
    response = model.invoke(f"Generate a friendly greeting for {name}")
    return response.content

@entrypoint()
def run_workflow(name: str) -> Dict[str, Any]:
    greeting = generate_greeting(name).result()
    return {"greeting": greeting, "name": name}
```

3. Test your agent:
```
GET http://localhost:8000/api/v1/agent/my_first_agent?input=John
```

That's it! Your first AI agent is up and running.

## 🔒 Enterprise Security Framework

AORBIT includes a comprehensive enterprise-grade security framework designed for financial applications:

- **Role-Based Access Control (RBAC)**: Fine-grained permission management with hierarchical roles
- **Comprehensive Audit Logging**: Immutable audit trail for all system activities
- **Data Encryption**: Both at-rest and in-transit encryption for sensitive data
- **API Key Management**: Enhanced API keys with role assignments and IP restrictions

To enable the security framework, simply set the following in your `.env` file:

```
SECURITY_ENABLED=true
```

For detailed information, see the [Security Framework Documentation](docs/security_framework.md).

## 🐳 Running Different Environments

AORBIT supports multiple environments through Docker:

```bash
# Windows PowerShell
# Development environment (hot-reloading)
.\scripts\run_environments.ps1 -Environment dev

# Testing environment (runs tests)
.\scripts\run_environments.ps1 -Environment test

# UAT environment (pre-production)
.\scripts\run_environments.ps1 -Environment uat

# Production environment
.\scripts\run_environments.ps1 -Environment prod

# Linux/macOS
# Development environment (hot-reloading)
./scripts/run_environments.sh dev

# Testing environment (runs tests)
./scripts/run_environments.sh test

# UAT environment (pre-production)
./scripts/run_environments.sh uat

# Production environment
./scripts/run_environments.sh prod
```

Access environments at:
- Development: http://localhost:8000
- UAT: http://localhost:8001
- Production: http://localhost:8000

For more details, see the [Docker Environments Guide](docs/docker_environments.md).

## 🔥 Key Features

- **Deploy Anywhere**: Cloud, serverless functions, containers or locally
- **Stateless Architecture**: Horizontally scalable with no shared state
- **Flexible Agent System**: Support for any LLM via LangChain, LlamaIndex, etc.
- **Enterprise Ready**: Authentication, RBAC, audit logging, encryption, and metrics built-in
- **Financial Applications**: Designed for sensitive data processing and compliance requirements
- **Developer Friendly**: Automatic API generation, hot-reloading, and useful error messages

## 🛣️ Roadmap

- [x] Core framework
- [x] Dynamic agent discovery
- [x] API generation
- [x] Enterprise security features
- [ ] Agent marketplace
- [ ] Managed cloud offering

## 📚 Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Creating Agents](docs/creating-agents.md)
- [Security Framework](docs/security_framework.md)
- [Deployment Options](docs/deployment.md)
- [API Reference](docs/api-reference.md)
- [Docker Environments Guide](docs/docker_environments.md)
- [Environment Management](docs/environment_management.md)
- [Examples](examples/README.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain) for the LLM integration tools
- [FastAPI](https://fastapi.tiangolo.com/) for the lightning-fast API framework
- [UV](https://github.com/astral-sh/uv) for the modern Python package management

