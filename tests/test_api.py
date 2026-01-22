from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_endpoint():
    response = client.post("/api/generate", json={
        "model": "qwen2.5",
        "prompt": "Hello",
        "stream": False
    })
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "qwen2.5" or data["model"] == "mock-qwen2.5"
    assert data["done"] is True
    assert "response" in data
    assert len(data["response"]) > 0

def test_chat_endpoint():
    response = client.post("/api/chat", json={
        "model": "qwen2.5",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": False
    })
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is True
    assert "message" in data
    assert data["message"]["role"] == "assistant"
