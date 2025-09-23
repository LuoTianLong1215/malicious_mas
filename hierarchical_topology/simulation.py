# simulation.py
"""
层级拓扑
多智能体仿真主流程
"""
from . import roles
from .prompts import DETECT_TEMPLATE, get_prompt
from utils.llm import llm_chat
from utils.metrics import get_predict_answer, parse_detect_result


def run_single_simulation(dataset_info, sample, condition, malicious_role, llm, model):
    """
    多智能体仿真主流程：依次让每个agent根据其角色和历史对话生成回复，最后由检测agent判断谁是malicious。
    参数：
        参数：
        dataset_info: 数据集信息
        sample: 题目内容
        condition: 条件名称
        malicious_role: 恶意角色
        llm, model: LLM模型名
    返回：
        agent_records: 所有agent的prompt、think、answer
        predict_answer: 预测答案
        predict_role: 预测恶意角色
    """
    agent_records = []      # 记录每个agent的prompt、think和answer
    
    # 构建问答参数
    format_kwargs = {
        "question": sample.get('question', ''),
        "correct_answer": sample.get('answer', ''),
    }

    # 构建选项参数
    if dataset_info['type'] == 'multiple_choice' and 'options' in sample:
        format_kwargs['choices'] = "/".join([chr(i + 65) for i in range(len(sample['options']))])
        format_kwargs['options'] = "\n".join(sample['options'])

    # 运行每个agent
    for role in roles:
        # 构建提示词
        prompt = get_prompt(dataset_info, role, condition, malicious_role).format(**format_kwargs)
        # LLM推理
        think, answer = llm_chat(prompt, llm, model)
        # 解析预测结果
        predict_answer = get_predict_answer(answer, dataset_info)
        # 记录agent结果
        agent_records.append({"role": role, "prompt": prompt, "think": think, "answer": answer, "predict": predict_answer})
        # 构建下一个agent的提示词
        format_kwargs[role + '_answer'] = answer

    # 构建检测提示词
    prompt = DETECT_TEMPLATE.format(**format_kwargs)
    # LLM推理
    think, answer = llm_chat(prompt, llm, model)
    predict_role = parse_detect_result(answer, roles)
    agent_records.append({
        "role": "Detector",
        "prompt": prompt,
        "think": think,
        "answer": answer,
        "predict": predict_role,
    })
    
    return agent_records, predict_answer, predict_role