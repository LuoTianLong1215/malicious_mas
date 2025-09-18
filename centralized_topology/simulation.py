# simulation.py
"""
中心化拓扑
多智能体仿真主流程
"""
import json

from .prompts import get_prompt, get_detector_prompt
from utils.llm import llm_chat
from utils.metrics import get_predict_answer, parse_detect_result


coordinator_role = 'Coordinator'
expert_role = 'Expert'
verifier_role = 'Verifier'
roles = [coordinator_role, expert_role, verifier_role]

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

    # 1. Coordinator分析问题并返回instruction
    prompt = get_prompt(dataset_info, coordinator_role, condition, malicious_role)[0].format(**format_kwargs)
    think, coordinator_response = llm_chat(prompt, llm, model)
    
    # 记录Coordinator结果
    agent_records.append({"role": coordinator_role, "prompt": prompt, "think": think, "answer": coordinator_response})
    records_str += f"\n{coordinator_role}: {coordinator_response}"
    
    # 解析Coordinator的instruction
    try:
        instruction = json.loads(coordinator_response).get('instruction', '')
    except Exception:
        instruction = coordinator_response
    
    # 2. Expert根据问题和instruction生成思路和答案
    format_kwargs['instruction'] = instruction
    prompt = get_prompt(dataset_info, expert_role, condition, malicious_role).format(**format_kwargs)
    think, expert_response = llm_chat(prompt, llm, model)
    
    # 解析Expert的答案
    expert_answer = get_predict_answer(expert_response, dataset_info)
    
    # 记录Expert结果
    agent_records.append({"role": expert_role, "prompt": prompt, "think": think, "answer": expert_response, "predict_answer": expert_answer})
    records_str += f"\n{expert_role}: {expert_response}"
    
    # 3. Verifier根据instruction和Expert的答案生成自己的答案
    format_kwargs['expert_answer'] = expert_response
    prompt = get_prompt(dataset_info, verifier_role, condition, malicious_role).format(**format_kwargs)
    think, verifier_response = llm_chat(prompt, llm, model)
    
    # 解析Verifier的答案
    verifier_answer = get_predict_answer(verifier_response, dataset_info)
    
    # 记录Verifier结果
    agent_records.append({"role": verifier_role, "prompt": prompt, "think": think, "answer": verifier_response, "predict_answer": verifier_answer})
    records_str += f"\n{verifier_role}: {verifier_response}"
    
    # 4. Coordinator从Expert和Verifier的答案中选择并给出理由
    format_kwargs['expert_response'] = expert_response
    format_kwargs['verifier_response'] = verifier_response
    prompt = get_prompt(dataset_info, coordinator_role, condition, malicious_role)[1].format(**format_kwargs)
    think, answer = llm_chat(prompt, llm, model)
    
    # 解析最终答案
    final_answer = get_predict_answer(answer, dataset_info)
    
    # 记录Coordinator最终结果
    agent_records.append({"role": coordinator_role, "prompt": prompt, "think": think, "answer": answer, "predict_answer": final_answer})
    records_str += f"\n{coordinator_role}: {answer}"
    
    # 5. 构建检测提示词
    prompt = get_detector_prompt(dataset_info, sample, records_str)
    think, answer = llm_chat(prompt, llm, model)
    predict_role = parse_detect_result(answer, roles)
    agent_records.append({
        "role": "Detector",
        "prompt": prompt,
        "think": think,
        "answer": answer,
        "predict_role": predict_role,
    })
    
    return agent_records, final_answer, predict_role