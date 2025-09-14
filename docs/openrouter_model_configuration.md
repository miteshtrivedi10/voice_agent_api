# OpenRouter Model Configuration

## Overview
The application now supports configuring the OpenRouter model via an environment variable, allowing you to easily switch between different models without modifying the code.

## Environment Variable
- **OPENROUTER_MODEL**: Specifies the OpenRouter model to use for LLM calls
- **Default Value**: `openrouter/sonoma-dusk-alpha`
- **Examples**: 
  - `openrouter/llama-3-70b`
  - `openrouter/mistral-7b`
  - `openrouter/gpt-4`

## Usage

### Setting the Environment Variable

#### Linux/macOS:
```bash
export OPENROUTER_MODEL="openrouter/llama-3-70b"
```

#### Windows:
```cmd
set OPENROUTER_MODEL=openrouter/llama-3-70b
```

#### In .env file:
```env
OPENROUTER_MODEL=openrouter/llama-3-70b
```

### Running the Application
After setting the environment variable, simply run the application as usual:

```bash
python main.py
```

The application will automatically use the configured model for all OpenRouter API calls.

## Affected Components
The following components will use the configured model:
- Content analysis and classification
- Questionnaire generation
- Semantic summarization
- Image multimodal analysis

## Model Compatibility
Ensure that the model you specify is compatible with OpenRouter and supports the required functionality for educational content processing.