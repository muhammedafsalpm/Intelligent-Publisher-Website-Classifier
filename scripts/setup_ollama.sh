#!/bin/bash
# scripts/setup_ollama.sh
# Setup script for Ollama

echo "Setting up Ollama models..."

# Pull classification model
ollama pull llama3.2

# Pull embedding model (Fixes 404 for /api/embeddings)
ollama pull nomic-embed-text

echo "Ollama setup complete!"
