# Text Summarization Agent

This example demonstrates a text summarization agent that can create concise summaries from longer content with customizable parameters.

## Features

- Summarizes text to a specified number of sentences
- Supports multiple summary styles (concise, bullet points, detailed)
- Provides metadata about the original and summarized content
- Handles both simple strings and structured JSON inputs

## Prerequisites

- AgentOrchestrator installed and configured
- Google AI API key in your `.env` file

## Setup

1. Copy the agent to your routes directory:
   ```bash
   cp -r examples/agents/summarizer_agent/ src/routes/
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

### Basic Text Summarization

You can submit text directly for summarization with default parameters (3 sentences, concise style):

```bash
curl "http://localhost:8000/api/v1/agent/summarizer_agent?input=The%20Industrial%20Revolution%20was%20a%20period%20of%20major%20industrialization%20and%20innovation%20during%20the%20late%201700s%20and%20early%201800s.%20The%20Industrial%20Revolution%20began%20in%20Great%20Britain%20and%20quickly%20spread%20throughout%20the%20world.%20The%20American%20Industrial%20Revolution%20commonly%20referred%20to%20as%20the%20Second%20Industrial%20Revolution%2C%20started%20in%20the%20late%201800s.%20The%20development%20of%20steam-powered%20machines%20and%20technologies%20was%20one%20of%20the%20biggest%20triggers%20for%20the%20Industrial%20Revolution.%20Industrial%20textile%20production%20required%20many%20workers%2C%20leading%20to%20rapid%20urbanization."
```

### Customized Summarization

For more control, use JSON input to specify parameters:

```bash
curl "http://localhost:8000/api/v1/agent/summarizer_agent?input={\"text\":\"The%20Industrial%20Revolution%20was%20a%20period%20of%20major%20industrialization%20and%20innovation%20during%20the%20late%201700s%20and%20early%201800s.%20The%20Industrial%20Revolution%20began%20in%20Great%20Britain%20and%20quickly%20spread%20throughout%20the%20world.%20The%20American%20Industrial%20Revolution%20commonly%20referred%20to%20as%20the%20Second%20Industrial%20Revolution%2C%20started%20in%20the%20late%201800s.%20The%20development%20of%20steam-powered%20machines%20and%20technologies%20was%20one%20of%20the%20biggest%20triggers%20for%20the%20Industrial%20Revolution.%20Industrial%20textile%20production%20required%20many%20workers%2C%20leading%20to%20rapid%20urbanization.\",\"max_sentences\":2,\"style\":\"bullet\"}"
```

### Summary Styles

The agent supports three summary styles:

1. **Concise** (default): Clear, focused summary in sentence format
   ```
   ?input={"text":"Your long text here","style":"concise"}
   ```

2. **Bullet**: Key points presented as a bullet list
   ```
   ?input={"text":"Your long text here","style":"bullet"}
   ```

3. **Detailed**: Comprehensive summary with more details
   ```
   ?input={"text":"Your long text here","style":"detailed"}
   ```

## Response Structure

The agent returns a JSON response with:

```json
{
  "success": true,
  "data": {
    "original_text": "The first 100 characters of the original text...",
    "summary": "The generated summary text.",
    "metadata": {
      "model": "gemini-2.0-flash-exp",
      "temperature": 0.2,
      "max_sentences": 3,
      "style": "concise",
      "original_length": 456,
      "summary_length": 128
    }
  },
  "error": null
}
```

## Implementation Details

The implementation follows these steps:

1. Accept either a string or structured input
2. Extract and validate parameters (max_sentences, style)
3. Generate a prompt based on the desired style
4. Send the prompt to the Gemini model
5. Return the summary with metadata

## Error Handling

The agent includes parameter validation to ensure:
- `max_sentences` is a positive integer (defaults to 3 if invalid)
- `style` is one of the supported options (defaults to "concise" if invalid) 