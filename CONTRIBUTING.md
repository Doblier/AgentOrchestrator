# Contributing to AgentOrchestrator

Thank you for your interest in contributing to AgentOrchestrator! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We expect all contributors to adhere to it.

## How Can I Contribute?

### Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear and concise description of the bug
2. **Reproduction Steps**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, and dependency versions

Please create issues using the Bug Report template.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

1. **Use Case**: Clear description of the problem you're trying to solve
2. **Proposed Solution**: Your idea for implementing the enhancement
3. **Alternatives Considered**: Any alternative solutions you've considered

### Contributing Code

#### Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/AgentOrchestrator.git`
3. Set up your development environment:
   ```bash
   cd AgentOrchestrator
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

#### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Run tests:
   ```bash
   pytest
   ```
4. Ensure code quality:
   ```bash
   ruff check .
   ```
5. Update documentation if needed

#### Pull Request Process

1. Update the README.md or documentation with details of changes if applicable
2. Include tests for new features or bug fixes
3. Ensure your code passes all tests and lint checks
4. Submit a pull request to the `main` branch

## Development Guidelines

### Code Style

We follow PEP 8 with a few exceptions:

- Line length: 88 characters (using Black defaults)
- Use consistent docstrings (Google style)

### Testing

- Write unit tests for new features or bug fixes
- Keep test coverage above 80%
- Use pytest for running tests

### Documentation

- Update documentation for new features or changes to existing functionality
- Follow the established documentation style
- Create examples for new features

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `test`: Adding or updating tests
- `chore`: Changes to the build process or auxiliary tools

Example: `feat: add support for OpenAI function calling`

## Project Structure

```
AgentOrchestrator/
├── agentorchestrator/       # Core framework code
│   ├── api/                 # API and route handling
│   ├── middleware/          # Middleware components
│   ├── state/               # State management
│   └── tools/               # Agent tools
├── docs/                    # Documentation
├── examples/                # Example agents and integrations
├── kubernetes/              # Kubernetes deployment configs
├── src/                     # User agent code (not modified by framework)
│   └── routes/              # Agent routes
└── tests/                   # Test suite
```

## Adding New Agents

When contributing new example agents:

1. Create a new directory in `examples/agents/your-agent-name/`
2. Include proper documentation and examples of how to use it
3. Follow the established agent pattern (using ao_agent.py)
4. Avoid adding dependencies unless absolutely necessary

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

## Questions?

If you have any questions, feel free to open an issue or reach out to the maintainers.

Thank you for contributing to AgentOrchestrator!
