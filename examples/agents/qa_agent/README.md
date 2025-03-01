# Question Answering Agent

This example demonstrates a simple but powerful question answering agent that uses Google's Gemini model to respond to natural language questions.

## Features

- Answers general knowledge questions
- Returns confidence metadata
- Handles factual, opinion-based, and creative questions

## Prerequisites

- AgentOrchestrator installed and configured
- Google AI API key in your `.env` file

## Setup

1. Copy the agent to your routes directory:
   ```bash
   cp -r examples/agents/qa_agent/ src/routes/
   ```

2. Ensure your `.env` file has a valid Google AI API key:
   ```
   GOOGLE_API_KEY=your-google-ai-key
   ```

3. Restart your AgentOrchestrator server:
   ```bash
   python main.py
   ```

## Usage

### Basic Question

```bash
curl "http://localhost:8000/api/v1/agent/qa_agent?input=What%20is%20the%20capital%20of%20Japan%3F"
```

Response:
```json
{
  "success": true,
  "data": {
    "question": "What is the capital of Japan?",
    "answer": "The capital of Japan is Tokyo.",
    "metadata": {
      "model": "gemini-2.0-flash-exp",
      "temperature": 0.2,
      "tokens_used": 16
    }
  },
  "error": null
}
```

### Complex Questions

The agent can handle more complex questions as well:

```bash
curl "http://localhost:8000/api/v1/agent/qa_agent?input=Explain%20the%20theory%20of%20relativity%20in%20simple%20terms"
```

```bash
curl "http://localhost:8000/api/v1/agent/qa_agent?input=What%20are%20the%20main%20differences%20between%20Python%20and%20JavaScript%3F"
```

## Customization

You can modify the agent's behavior by:

1. Changing the model in `ao_agent.py`:
   ```python
   model = ChatGoogleGenerativeAI(
       model="gemini-2.0-pro",  # Change to a different model
       temperature=0.5,  # Adjust for more creative responses
   )
   ```

2. Enhancing the prompt template for specific use cases

## Implementation Details

The implementation follows these steps:

1. Take the user's question as input
2. Format the question within a prompt that instructs the model to provide accurate information
3. Send the prompt to Google's Gemini model
4. Process and format the response
5. Return a structured response with metadata

## Error Handling

The agent includes basic error handling but could be enhanced with:

- Input validation
- Toxic content detection
- Response verification against known facts 