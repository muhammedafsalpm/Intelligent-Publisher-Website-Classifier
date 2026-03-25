# Publisher Website Classifier with Multi-LLM Support

## LLM Provider Support

This system supports two LLM providers:

### 1. OpenAI (Cloud-based)
- Fast, accurate, production-ready
- Requires API key
- Models: gpt-4o-mini, gpt-4o, etc.

### 2. Ollama (Local, Open Source)
- Run locally with no API costs
- Supports Llama 3, Mistral, etc.
- Great for development and privacy-sensitive use cases

## Configuration

Edit `.env` file to choose provider:

```env
# Choose provider: "openai" or "ollama"
LLM_PROVIDER=openai

# OpenAI config (if provider=openai)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

# Ollama config (if provider=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Running with Ollama

1. Start Ollama:
```bash
docker-compose --profile with-ollama up -d ollama
```

2. Pull a model:
```bash
docker exec -it publisher-classifier_ollama_1 ollama pull llama3.2
```

3. Start the API:
```bash
docker-compose up -d api
```

## Provider Comparison

| Feature | OpenAI | Ollama |
|---------|--------|--------|
| Setup | API key only | Local installation |
| Cost | ~$0.002/request | Free |
| Speed | Fast (2-3s) | Depends on hardware |
| Privacy | Cloud-based | Fully local |
| Accuracy | Very high | Good |
| Embeddings | Built-in | Built-in |

## Switching Providers

Simply change `LLM_PROVIDER` in `.env` and restart the service:

```bash
docker-compose restart api
```

The system automatically uses the appropriate client and embeddings.