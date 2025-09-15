from multiprocess.connection import answer_challenge
import ollama
import re

from openai import OpenAI

def llm_chat(prompt: str, llm: str, model: str):
    """
    调用模型
    """
    if llm == "api":
        return llm_chat_api(prompt, model)
    elif llm == "ollama":
        return llm_chat_ollama(prompt, model)
    else:
        raise ValueError(f"不支持的模型: {llm} - {model}")

def llm_chat_api(prompt: str, model: str):
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

def llm_chat_ollama(prompt: str, model: str):
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
