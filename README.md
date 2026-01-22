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

## Multi-User & Context Switching

The server is designed to be **stateless**. This means the Hailo memory is cleared between every request to support multiple concurrent users. 

**Application Logic:**
Your application must maintain the conversation history (context) for each user and send the **full history** with every new request. The server will re-ingest (prefill) this context before generating the new response.

### Example: Chat Session for User A
**Turn 1:**
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen",
  "messages": [
    {"role": "user", "content": "My name is Alice."}
  ]
}'
```

**Turn 2 (Crucial: Send History Again):**
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen",
  "messages": [
    {"role": "user", "content": "My name is Alice."},
    {"role": "assistant", "content": "Hello Alice! How can I help?"},
    {"role": "user", "content": "What is my name?"}
  ]
}'
```

The server will isolate this request from any other concurrect request.

**Smart Caching Optimization (New):**
While you must send the full history, the server implements **Prefix Caching**.
1.  **First Turn**: The server processes the text (Prefill).
2.  **Follow-up Turns**: If the new request extends a previous conversation, the server **skips re-processing** the old history and instantly loads the cached state.
3.  **Performance**:
    *   **Cache Hit**: ~0.0s prefill latency (Instant start).
    *   **Cache Miss**: ~2.0s prefill (for 2k chars).
    *   This provides a smooth, "stateful-like" experience for users while keeping your app logic simple and stateless.


## Stateful Mode (Advanced)

For applications that wish to offload history management to the server (Ollama-style), use the `/api/generate` endpoint with the `context` parameter.

**Turn 1:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5", 
  "prompt": "My name is Bob"
}'
# Response:
# {
#   "model": "qwen2.5",
#   "created_at": "2026-01-22T22:00:00.000Z",
#   "response": "Hello! Nice to meet you, Bob.",
#   "done": true,
#   "context": [1737123456789]
# }
```

**Turn 2 (Send Context ID only):**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5", 
  "prompt": "What is my name?",
  "context": [12345678]
}'
# Response confirms memory ("Bob") and returns NEW context ID.
```

The server caches the session state internally. This is more efficient for bandwidth but requires your client to track the latest `context` ID.
