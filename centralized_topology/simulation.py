# simulation.py
"""
中心化拓扑
多智能体仿真主流程
"""
import json

from .prompts import get_prompt, get_detector_prompt
from utils.llm import llm_chat
from utils.metrics import get_predict_answer, parse_detect_result


expert_role = 'Expert'
verifier_role = 'Verifier'
coordinator_role = 'Coordinator'
roles = [expert_role, verifier_role, coordinator_role]

def run_single_simulation(dataset_info, sample, condition, malicious_role, llm, model):
    """
    中心化拓扑多智能体仿真主流程：
    1. Coordinator分析问题并返回instruction
    2. Expert根据问题和instruction生成思路和答案
    3. Verifier根据instruction和Expert的答案生成自己的答案
    4. Coordinator从Expert和Verifier的答案中选择并给出理由
    5. 最后由检测agent判断谁是malicious
    
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
    records_str = ""        # 每个agent的结果记录，用于判断恶意agent
    
    # 构建问答参数
    format_kwargs = {
        "question": sample.get('question', ''),
        "correct_answer": sample.get('answer', ''),
    }

    # 构建选项参数
    if dataset_info['type'] == 'multiple_choice' and 'options' in sample:
        format_kwargs['choices'] = "/".join([chr(i + 65) for i in range(len(sample['options']))])
        format_kwargs['options'] = "\n".join(sample['options'])

    for role in roles:
        prompt = get_prompt(dataset_info, role, condition, malicious_role).format(**format_kwargs)
        think, response = llm_chat(prompt, llm, model)
        
        answer = get_predict_answer(response, dataset_info)
        agent_records.append({"role": role, "prompt": prompt, "think": think, "answer": response, "predict_answer": answer})
        records_str += f"\n{role}: {response}"

        format_kwargs[role.lower() + '_answer'] = response
    
    prompt = get_detector_prompt(dataset_info, sample, records_str)
    think, response = llm_chat(prompt, llm, model)
    predict_role = parse_detect_result(response, roles)
    agent_records.append({
        "role": "Detector",
        "prompt": prompt,
        "think": think,
        "answer": response,
        "predict_role": predict_role,
    })
    
    return agent_records, answer, predict_role