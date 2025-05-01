from typing import Callable, Dict
import anthropic
import openai
import os
import logging

# Type alias for query functions
QueryFunction = Callable[[str, str, Dict], str]

# Registry for model providers
PROVIDER_REGISTRY: Dict[str, QueryFunction] = {}

def register_provider(provider_name: str):
    """Decorator to register query functions for model providers."""
    def decorator(func: QueryFunction) -> QueryFunction:
        PROVIDER_REGISTRY[provider_name] = func
        return func
    return decorator

@register_provider("openai")
def query_openai(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    api_key = model_config.get("openai_api_key", os.environ.get("OPENAI_API_KEY"))
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model_config["model_name"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **model_config['response_kwargs']
    )
    return response.choices[0].message.content

@register_provider("anthropic")
def query_anthropic(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    api_key = model_config.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY"))
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model_config["model_name"],
        max_tokens=1024,
        messages=[
            {"role": "user", "content": user_prompt},
            {"role": "system", "content": system_prompt}
        ],
        **model_config['response_kwargs']
    )
    return response.content[0].text

@register_provider("openrouter")
def query_openrouter(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    api_key = model_config.get("openrouter_api_key", os.environ.get("OPENROUTER_API_KEY"))
    base_url = model_config.get("openrouter_base_url", "https://openrouter.ai/api/v1")
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model_config["model_name"],
        messages=[
            {"role": "user", "content": user_prompt},
            {"role": "system", "content": system_prompt}
        ],
        **model_config['response_kwargs']
    )
    return response.choices[0].message.content

@register_provider("local")
def query_local(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    api_key = model_config.get("local_api_key", "FEEL_THE_AGI")
    base_url = model_config.get("local_base_url", "http://localhost:7999/v1")
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model_config["model_name"],
        messages=[
            {"role": "user", "content": user_prompt},
            {"role": "system", "content": system_prompt}
        ],
        **model_config['response_kwargs']
    )
    return response.choices[0].message.content

@register_provider("human")
def query_human(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    from rich import print
    print(f"User prompt: {user_prompt}")
    print(f"System prompt: {system_prompt}")
    return input("Enter your response: ")
    
    
def llm_query(user_prompt: str, system_prompt: str, model_config: Dict) -> str:
    """Dispatch query to the appropriate provider based on model configuration."""
    # Log the model call details
    logging.info(f"Model call to {model_config['model_provider']} - {model_config['model_name']}")
    
    # Log the full prompts
    logging.info(f"User prompt: {user_prompt}")
    logging.info(f"System prompt: {system_prompt}")
    
    # Don't log prompts to Multion API at all
    # Only log locally for debugging
    pass
    
    model_provider = model_config["model_provider"]
    query_func = PROVIDER_REGISTRY.get(model_provider)
    if not query_func:
        raise ValueError(f"Unknown model provider: {model_provider}")
    
    response = query_func(user_prompt, system_prompt, model_config)
    
    # Log full response
    logging.info(f"Model response: {response}")
    
    return response

if __name__ == "__main__":
    model_config = {
        "model_provider": "local",
        "model_name": "unsloth/gemma-3-27b-it-unsloth-bnb-4bit",
        "local_api_key": "FEEL_THE_AGI",
        "local_base_url": "http://localhost:7999/v1",
        "response_kwargs": {
            "max_tokens": 50,
            "temperature": 2.0,
            "top_p": 0.97,
            "extra_body":{"top_k": 128}
        }
    }
    print(llm_query("Who's the smartest?", "Talk like you are AGI, you answer in very few words", model_config))
    
    model_config = {
        "model_provider": "openrouter",
        "model_name": "qwen/qwen3-235b-a22b",
        "openrouter_api_key": "",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "response_kwargs": {}
    }
    print(llm_query("Who's the smartest?", "Talk like you are AGI, you answer in very few words", model_config))