import requests
import os
from config import LLM_CONFIG
from openai import OpenAI
from alcf_inference.inference_auth_token import get_access_token

total_tokens_used = 0
output_log = []
os.environ["NO_PROXY"] = "localhost"

def query_llm(prompt, model=LLM_CONFIG["default_model"], temperature=0.7, source=LLM_CONFIG["source"]):
    if source == "ollama":
        return query_llm_ollama(prompt, model, temperature)
    elif source == "alcf_sophia":
        return query_llm_alcf_sophia(prompt, model, temperature)
    elif source == "alcf_metis":
        return query_llm_alcf_metis(prompt, model, temperature)
    else:
        raise ValueError(f"Unsupported LLM source: {source}")
    
def query_llm_alcf_metis(prompt, model=LLM_CONFIG["default_model"], temperature=0.7):
    access_token = get_access_token()
    print("DEBUG: Using ALCF inference endpoint with access token.")
    # Metis cluster
    client = OpenAI(
        api_key=access_token,
        base_url="https://inference-api.alcf.anl.gov/resource_server/metis/api/v1"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()

def query_llm_alcf_sophia(prompt, model=LLM_CONFIG["default_model"], temperature=0.7):
    access_token = get_access_token()
    print("DEBUG: Using ALCF inference endpoint with access token.")
    # Sophia cluster
    client = OpenAI(
        api_key=access_token,
        base_url="https://inference-api.alcf.anl.gov/resource_server/sophia/vllm/v1"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
    
def query_llm_ollama(prompt, model=LLM_CONFIG["default_model"], temperature=0.7):
    global total_tokens_used
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "stream": False,
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        response_data = response.json()
        total_tokens_used += response_data.get("eval_count", 0)  # track tokens
        output_log.append(
            {
                "model": model,
                "prompt": prompt,
                "response": response_data.get("response", "").strip(),
                "tokens_used": response_data.get("eval_count", 0),
            }
        )
        return response.json().get("response", "").strip()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
