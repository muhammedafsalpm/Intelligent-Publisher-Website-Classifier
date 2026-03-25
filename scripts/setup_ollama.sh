#!/bin/bash
# scripts/setup_ollama.sh
# Setup script for Ollama

echo "Setting up Ollama..."

# Pull models
ollama pull llama3.2
ollama pull nomic-embed-text

echo "Ollama setup complete!"
