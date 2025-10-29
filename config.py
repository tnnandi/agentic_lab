MAX_ROUNDS = 1

LLM_CONFIG = {
    # "source": "ollama", 
    # "default_model": "llama3.1:8b",
    # "default_model": "qwen3:8b",
    # "default_model": "gpt-oss:20b",
    # "default_model": "deepseek-r1:70b",
    "source": "alcf_sophia",
    "default_model": "openai/gpt-oss-120b",
    # "source": "alcf_metis",
    # "default_model": "DeepSeek-R1",
    "temperature": {
        "research": 0.3,
        "coding": 0.2,
        "critic": 0.4,
        "execution": 0.1,
        "review": 0.1,
    },
}