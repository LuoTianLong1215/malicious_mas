import ollama
import re

from openai import OpenAI

def llm_chat(prompt: str, llm: str, model: str):
    """
    调用模型
    """
    if llm == "api" and model.startswith("Qwen/Qwen3-"):
        return _api_qwen3(prompt, model)
    elif llm == "api" and model.startswith("gpt-4o-mini"):
        return _api_gpt(prompt, model) 
    elif llm == "ollama" and model.startswith("qwen3:"):
        return _ollama_qwen3(prompt, model)
    else:
        raise ValueError(f"不支持的模型: {llm} - {model}")

def _api_gpt(prompt: str, model: str):
    _client = OpenAI(
        base_url="https://api.gpt.ge/v1/",
        api_key="sk-dw7tdJcWgoaEvnx73aDb8a49750943039193663207Aa211a",
        default_headers={"x-foo": "true"},
    )

    response = _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.choices[0].message.content
    return None, answer

def _api_qwen3(prompt: str, model: str):
    """
    通过API调用模型
    """
    _client = OpenAI(
        base_url='https://api-inference.modelscope.cn/v1',
        api_key='ms-2d4ddfb6-55fb-4191-ac12-1f79064b9f66', # ModelScope Token
    )

    # set extra_body for thinking control
    extra_body = {
        # enable thinking, set to False to disable
        "enable_thinking": True,
        # use thinking_budget to contorl num of tokens used for thinking
        # "thinking_budget": 4096
    }
    
    response = _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        extra_body=extra_body
    )

    think = ""
    answer = ""
    for chunk in response:
        thinking_chunk = chunk.choices[0].delta.reasoning_content
        answer_chunk = chunk.choices[0].delta.content
        if thinking_chunk != '':
            think += thinking_chunk
        elif answer_chunk != '':
            answer += answer_chunk

    return think, answer

def _ollama_qwen3(prompt: str, model: str):
    """
    通过本地Ollama调用模型
    """
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response['message']['content'] if 'message' in response else response['messages'][-1]['content']

    think = None
    answer = content
    match = re.match(r'<think>(.*?)</think>(.*)', content, re.DOTALL)
    if match:
        think = match.group(1).strip()
        answer = match.group(2).strip()

    return think, answer
    