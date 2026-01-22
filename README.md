# Hailo LLM Interface

This project provides an Ollama-compatible API key for running LLMs on Hailo10h hardware on Raspberry Pi 5.

## Quick Start

1. **Install Dependencies** (Already done if you see the `venv` folder)
   ```bash
   python3 -m venv venv --system-site-packages
   ./venv/bin/pip install -r requirements.txt
   ```

2. **Run the Server**
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

3. **Open Chat UI**
   Open your browser to `http://<raspberry-pi-ip>:11434/`

## Model Setup

To use the real Hailo inference, you must upload your model files to the `models/` directory.
Required files:
- `qwen2.5.hef` (The compiled Hailo Executable Format file)
- Tokenizer files (`tokenizer.json`, `vocab.json` etc.) - standard HuggingFace format.

Once files are uploaded, edit `start_server.sh` and uncomment:
```bash
export USE_HAILO_RUNNER=1
```

## API Usage

Generate text:
```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen2.5", "prompt": "Why is the sky blue?"}'
```

Chat:
```bash
curl http://localhost:11434/api/chat -d '{"model": "qwen2.5", "messages": [{"role": "user", "content": "Hello"}]}'
```
