# LLM_MODEL = "deepseek-r1:70b"
MAX_ROUNDS = 3

LLM_CONFIG = {
    # "default_model": "deepseek-r1:70b",
    # "default_model": "deepseek-r1:671b",
    "default_model": "qwq:latest",
    "temperature": {
        "research": 0.3,
        "coding": 0.2,
        "critique": 0.4,
        "execution": 0.1,
    },
}