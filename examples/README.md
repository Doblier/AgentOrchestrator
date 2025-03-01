# AgentOrchestrator Examples

This directory contains example agents and implementations to help you understand and build with AgentOrchestrator.

## Structure

- `agents/` - Example agent implementations
  - `qa_agent/` - Question answering agent with Google AI
  - `summarizer_agent/` - Text summarization agent
  - (more examples will be added)
- `patterns/` - Common patterns and best practices
- `integrations/` - Examples of integrating with other services
- `deployment/` - Sample deployment configurations

## Running Examples

Each example includes clear instructions in its README. Generally, you can:

1. Copy the example agent to your `src/routes/` directory:
   ```bash
   cp -r examples/agents/qa_agent/ src/routes/
   ```

2. Restart your AgentOrchestrator server:
   ```bash
   python main.py
   ```

3. Test the agent:
   ```bash
   curl "http://localhost:8000/api/v1/agent/qa_agent?input=What%20is%20the%20capital%20of%20France%3F"
   ```

## List of Examples

### QA Agent

A simple question-answering agent that uses Google AI to respond to natural language questions.

### Summarizer Agent

Summarizes text content, with options for controlling length and style of summary.

## Contributing Examples

We welcome contributions of new examples! Please follow these guidelines:

1. Create a directory with a descriptive name
2. Include a README.md with:
   - Overview of what the example demonstrates
   - Prerequisites
   - Setup instructions
   - Example usage
3. Follow the coding standards in the main CONTRIBUTING.md
4. Keep dependencies minimal
5. Include comments in your code 