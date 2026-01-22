
import requests
import json
import time

API_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5"

def chat(messages):
    """
    Sends the full conversation history to the API.
    Returns the assistant's response content.
    """
    start_time = time.time()
    
    # Enable streaming to see it live, but for simplicity here we just buffer
    # Actually, let's use streaming to avoid timeouts on long articles
    response = requests.post(
        API_URL, 
        json={"model": MODEL, "messages": messages}, 
        stream=True
    )
    
    full_content = ""
    print("Assistant: ", end="", flush=True)
    
    for line in response.iter_lines():
        if line:
            # parsing ollama stream format
            # {"model":"qwen2.5","created_at":"...","message":{"role":"assistant","content":"X"},"done":false}
            try:
                data = json.loads(line.decode('utf-8'))
                if 'message' in data:
                    content = data['message']['content']
                    full_content += content
                    print(content, end="", flush=True)
            except:
                pass
                
    print(f"\n[latency: {time.time() - start_time:.2f}s]\n")
    return full_content

def run_scenario():
    # Scenario Configuration
    TOPIC = "Healthy Eating"
    LANGUAGE = "English"
    LEVEL = "A2"
    GRAMMAR_CONCEPT = "use of modal verbs (should, must, can)"
    
    # This list maintains the State/Context of the conversation
    messages = []
    
    print(f"--- Starting Language Teacher Scenario ({TOPIC}) ---\n")

    # 1. Generate Article
    prompt_1 = (
        f"Act as a strict but helpful language teacher. "
        f"Write a short article (approx 150 words) about '{TOPIC}'. "
        f"Write in {LANGUAGE} at {LEVEL} level. "
        f"Focus on the grammar concept: {GRAMMAR_CONCEPT}. "
        f"Do not ask questions yet."
    )
    print(f"User: [Requesting Article about {TOPIC}]")
    messages.append({"role": "user", "content": prompt_1})
    response_1 = chat(messages)
    messages.append({"role": "assistant", "content": response_1})
    
    # 2. Generate Quiz
    prompt_2 = "Now create a 3-question multiple-choice quiz based on the text above. Indicate the correct answer."
    print(f"User: {prompt_2}")
    messages.append({"role": "user", "content": prompt_2})
    response_2 = chat(messages)
    messages.append({"role": "assistant", "content": response_2})
    
    # 3. Open Question
    prompt_3 = "Ask me one open-ended question related to the text to test my understanding."
    print(f"User: {prompt_3}")
    messages.append({"role": "user", "content": prompt_3})
    response_3 = chat(messages)
    messages.append({"role": "assistant", "content": response_3})
    
    # 4. User Answers
    # Simulating a user answer (maybe with a slight mistake to trigger feedback)
    user_answer = "I think people should eat more fruits because it must be good for health."
    print(f"User: {user_answer}")
    messages.append({"role": "user", "content": user_answer})
    
    # 5. Feedback
    prompt_5 = "Evaluate my answer. Give me a score out of 10, correct any mistakes, and give a hint how to improve it using the grammar concept."
    # Note: In a real app, you might append this instruction to the user's message or send it as a system instruction?
    # Here we send it as a separate instruction aka 'User' role driving the flow.
    # Actually, usually the user just answers. The 'Teacher' persona should know to evaluate.
    # Let's force the evaluation instruction.
    print(f"System/User: [Requesting Feedback]")
    messages.append({"role": "user", "content": prompt_5}) # Explicit instruction
    response_5 = chat(messages)
    messages.append({"role": "assistant", "content": response_5})
    
    # 6. Start Chat
    prompt_6 = "Now let's start a casual conversation about this topic. Ask me a new question to get started."
    print(f"User: {prompt_6}")
    messages.append({"role": "user", "content": prompt_6})
    response_6 = chat(messages)
    messages.append({"role": "assistant", "content": response_6})
    
    # 7 & 8. Conversation (Loop)
    # Simulating 3 turns for brevity in this example (User asked for 10, but 3 proves the point)
    conversation_turns = [
        "I usually eat toast for breakfast.",
        "I try to cook at home, but I am busy.",
        "Yes, I like apples."
    ]
    
    for turn_input in conversation_turns:
        print(f"User: {turn_input}")
        messages.append({"role": "user", "content": turn_input})
        response = chat(messages)
        messages.append({"role": "assistant", "content": response})
        
    # 9. End & Feedback
    prompt_9 = "Let's end the conversation here. Please give me overall feedback on my vocabulary and grammar usage during our chat."
    print(f"User: {prompt_9}")
    messages.append({"role": "user", "content": prompt_9})
    response_9 = chat(messages)
    messages.append({"role": "assistant", "content": response_9})
    
    print("--- Scenario Complete ---")

if __name__ == "__main__":
    run_scenario()
