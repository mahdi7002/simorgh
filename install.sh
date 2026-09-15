#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$(id -un)}"
TARGET_GROUP="$(id -gn "$TARGET_USER")"

printf '\n\033[1;34m🚀 Installing SIMORGH CORE v3.0\033[0m\n'

if [ "$(id -u)" -ne 0 ]; then
    printf '\033[1;31m❌ Please run this script with sudo.\033[0m\n'
    exit 1
fi

printf '\n📦 Updating system...\n'
apt-get update -qq > /dev/null
apt-get upgrade -y -qq > /dev/null

printf '\n📦 Installing dependencies...\n'
apt-get install -y -qq git python3.11 python3.11-dev python3.11-venv sqlite3 build-essential wget > /dev/null

printf '\n🐍 Installing Python packages...\n'
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1

MODEL_DIR="$SCRIPT_DIR/models"
MODEL_PATH="$MODEL_DIR/qwen2.5-1.5b.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    printf '\n🤖 Downloading LLM model...\n'
    python3 - <<PY
from huggingface_hub import hf_hub_download
from pathlib import Path

model_dir = Path(${MODEL_DIR@Q})
model_dir.mkdir(parents=True, exist_ok=True)
try:
    hf_hub_download(
        repo_id="Qwen/Qwen2.5-1.5B-GGUF",
        filename="qwen2.5-1.5b-q4_k_m.gguf",
        local_dir=str(model_dir),
        local_filename="qwen2.5-1.5b.gguf",
    )
    print("✓ Model downloaded successfully")
except Exception as exc:
    print(f"⚠ Model download failed: {exc}")
    print("Please download manually from:")
    print("https://huggingface.co/Qwen/Qwen2.5-1.5B-GGUF")
PY
fi

chown -R "$TARGET_USER:$TARGET_GROUP" "$SCRIPT_DIR"
chmod +x "$SCRIPT_DIR/main.py"

printf '\n✅ SIMORGH CORE v3.0 installed successfully!\n'
printf '\nTo start SIMORGH:\n'
printf '  cd %q\n' "$SCRIPT_DIR"
printf '  python3.11 main.py\n'
printf '\nAccess at: http://localhost:8000\n'
