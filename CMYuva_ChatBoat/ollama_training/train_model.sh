#!/bin/bash
# ═══════════════════════════════════════════════════════════
# CM Yuva Ollama Model Training Script
# Run this AFTER installing Ollama and downloading llama3.2
# Usage: bash ollama_training/train_model.sh
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo " CM Yuva AI Model Training"
echo "================================================"

# Step 1: Generate training data from real dataset
echo ""
echo "[1/4] Generating training data from CM Yuva dataset..."
cd "$PROJECT_DIR"
python ollama_training/generate_dataset.py
echo "      Training data ready!"

# Step 2: Check Ollama is running
echo ""
echo "[2/4] Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "      ERROR: Ollama is not running!"
    echo "      Please start it with: ollama serve"
    exit 1
fi
echo "      Ollama is running."

# Step 3: Check base model
echo ""
echo "[3/4] Checking base model (llama3.2)..."
if ! ollama list | grep -q "llama3.2"; then
    echo "      Downloading llama3.2 (this may take a few minutes)..."
    ollama pull llama3.2
fi
echo "      Base model ready."

# Step 4: Create fine-tuned model using Modelfile
echo ""
echo "[4/4] Creating CM Yuva model..."
cd "$SCRIPT_DIR"
ollama create cmyuva -f Modelfile
echo ""
echo "================================================"
echo " SUCCESS! Model 'cmyuva' created."
echo "================================================"
echo ""
echo "Now start the chatbot:"
echo "  python backend/app.py"
echo ""
echo "The chatbot will automatically use the 'cmyuva' model."
