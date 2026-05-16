#!/bin/sh
set -e

MODEL_DIR="/models"
MODEL_FILE="$MODEL_DIR/gemma-3-4b-it-Q4_K_M.gguf"
MMPROJ_FILE="$MODEL_DIR/mmproj-model-f16.gguf"
HF_BASE="https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main"

mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_FILE" ]; then
  echo "[pull_model] Downloading Gemma 3 4B Q4_K_M (~2.5GB)..."
  curl -L --progress-bar -o "$MODEL_FILE" "$HF_BASE/gemma-3-4b-it-Q4_K_M.gguf"
fi

if [ ! -f "$MMPROJ_FILE" ]; then
  echo "[pull_model] Downloading mmproj (~300MB)..."
  curl -L --progress-bar -o "$MMPROJ_FILE" "$HF_BASE/mmproj-model-f16.gguf"
fi

echo "[pull_model] Models ready. Starting llama.cpp server..."
exec /llama-server \
  -m "$MODEL_FILE" \
  --mmproj "$MMPROJ_FILE" \
  --host 0.0.0.0 \
  --port 8080 \
  -c 4096 \
  -np 1
