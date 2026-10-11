

import ollama

response = ollama.chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly: Motor overheating can be caused by excessive load, blocked ventilation, and damaged bearings."
        }
    ],
    think=False,
    options={
        "num_predict": 500,
        "temperature": 0.7
    }
)

print("ANSWER:", repr(response.message.content))
print("THINKING:", repr(response.message.thinking))
print("FINISH REASON:", response.done_reason)