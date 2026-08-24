#!/bin/bash

echo -e "\n\033[1;34m🚀 Installing SIMORGH CORE v3.0\033[0m"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31m❌ Please run this script with sudo.\033[0m"
    exit 1
fi

echo -e "\n📦 Updating system..."
apt-get update -qq > /dev/null
apt-get upgrade -y -qq > /dev/null

echo -e "\n📦 Installing dependencies..."
apt-get install -y -qq git python3.11 python3.11-dev python3.11-venv sqlite3 build-essential wget > /dev/null

echo -e "\n🐍 Installing Python packages..."
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install -r /home/mahdi/simorgh/requirements.txt > /dev/null 2>&1

if [ ! -f "/home/mahdi/simorgh/models/qwen2.5-1.5b.gguf" ]; then
    echo -e "\n🤖 Downloading LLM model..."
    python3 - <<EOF
from huggingface_hub import hf_hub_download
import os
os.makedirs("/home/mahdi/simorgh/models", exist_ok=True)
try:
    hf_hub_download(
        repo_id="Qwen/Qwen2.5-1.5B-GGUF",
        filename="qwen2.5-1.5b-q4_k_m.gguf",
        local_dir="/home/mahdi/simorgh/models",
        local_filename="qwen2.5-1.5b.gguf"
    )
    print("✓ Model downloaded successfully")
except Exception as e:
    print(f"⚠ Model download failed: {e}")
    print("Please download manually from:")
    print("https://huggingface.co/Qwen/Qwen2.5-1.5B-GGUF")
EOF
fi

chown -R mahdi:mahdi /home/mahdi/simorgh
chmod +x /home/mahdi/simorgh/main.py

echo -e "\n✅ SIMORGH CORE v3.0 installed successfully!"
echo -e "\nTo start SIMORGH:"
echo -e "  cd /home/mahdi/simorgh"
echo -e "  python3.11 main.py"
echo -e "\nAccess at: http://localhost:8000"
