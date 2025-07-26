MAX_ROUNDS = 1

LLM_CONFIG = {
    # "default_model": "llama3.1:8b",
    "default_model": "qwen3:8b",
    "temperature": {
        "research": 0.3,
        "coding": 0.2,
        "critique": 0.4,
        "execution": 0.1,
    },
}