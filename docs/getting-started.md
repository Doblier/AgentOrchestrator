# Getting Started with AgentOrchestrator

This guide will help you set up AgentOrchestrator and create your first AI agent in minutes.

## Prerequisites

- Python 3.12 or higher
- [UV](https://github.com/astral-sh/uv) package manager (recommended)
- API key for at least one LLM provider (Google AI, OpenAI, Anthropic, etc.)
- Redis (optional, for authentication, caching, and rate limiting)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AgentOrchestrator.git
cd AgentOrchestrator
```

### 2. Set Up Python Environment

Using UV (recommended):

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Using pip:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Open `.env` in your editor and add your LLM API keys and other settings.

### 4. Start the Server

```bash
python main.py
```

You should see output similar to:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Creating Your First Agent

AgentOrchestrator makes it easy to create new agents. Follow these steps to create a simple agent that generates greetings:

### 1. Create Agent Directory

```bash
mkdir -p src/routes/hello_agent
```

### 2. Create Agent Module

Create a file `src/routes/hello_agent/ao_agent.py` with the following content:

```python
"""
Hello Agent - Greeting Generator

This agent generates personalized greetings based on a name input.
"""

from typing import Dict, Any
from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize LLM
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

@task
def generate_greeting(name: str) -> str:
    """Generate a personalized greeting."""
    prompt = f"Generate a friendly and creative greeting for someone named {name}. Keep it concise."
    response = model.invoke(prompt)
    return response.content

@entrypoint()
def run_workflow(name: str) -> Dict[str, Any]:
    """Main workflow that generates a greeting for the given name."""
    greeting = generate_greeting(name).result()
    return {
        "greeting": greeting,
        "name": name,
        "timestamp": "2023-02-28T12:00:00Z"  # In a real app, use actual timestamp
    }
```

### 3. Test Your Agent

Restart the server (if it's running) and make a request to your new agent:

```bash
curl "http://localhost:8000/api/v1/agent/hello_agent?input=Sarah"
```

You should get a JSON response similar to:

```json
{
  "success": true,
  "data": {
    "greeting": "Hey Sarah! Sunshine follows you wherever you go. Have an amazing day!",
    "name": "Sarah",
    "timestamp": "2023-02-28T12:00:00Z"
  },
  "error": null
}
```

## Creating an Agent with Structured Input

For more complex agents that need multiple input parameters, you can use JSON input:

### 1. Create a Travel Agent

Create the directory and file:

```bash
mkdir -p src/routes/travel_agent
```

Create `src/routes/travel_agent/ao_agent.py`:

```python
"""
Travel Agent - Trip Recommendation Generator

This agent generates travel recommendations based on destination, budget, and duration.
"""

from typing import Dict, Any, TypedDict
from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize LLM
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

class TravelInput(TypedDict):
    """Input schema for travel recommendations."""
    destination: str
    budget: int
    duration: int

@task
def generate_recommendations(input_data: TravelInput) -> str:
    """Generate travel recommendations based on input parameters."""
    destination = input_data["destination"]
    budget = input_data["budget"]
    duration = input_data["duration"]
    
    prompt = f"""
    Generate travel recommendations for a {duration}-day trip to {destination} with a budget of ${budget}.
    Include:
    - 2-3 must-see attractions
    - 1-2 restaurant recommendations
    - 1 accommodation suggestion
    Keep it concise but informative.
    """
    
    response = model.invoke(prompt)
    return response.content

@entrypoint()
def run_workflow(input_data: TravelInput) -> Dict[str, Any]:
    """Main workflow that generates travel recommendations."""
    recommendations = generate_recommendations(input_data).result()
    
    return {
        "destination": input_data["destination"],
        "budget": input_data["budget"],
        "duration": input_data["duration"],
        "recommendations": recommendations
    }
```

### 2. Test Your Travel Agent

Make a request with JSON input:

```bash
curl "http://localhost:8000/api/v1/agent/travel_agent?input={\"destination\":\"Paris\",\"budget\":1500,\"duration\":5}"
```

You can also use a simpler string input, which will be adapted automatically:

```bash
curl "http://localhost:8000/api/v1/agent/travel_agent?input=Paris"
```

## Next Steps

- [Creating Agents](creating-agents.md) - Learn more about creating complex agents
- [Deployment Options](deployment.md) - Deploy your agents to production
- [API Reference](api-reference.md) - Full API documentation
- [Examples](../examples/README.md) - More example agents 