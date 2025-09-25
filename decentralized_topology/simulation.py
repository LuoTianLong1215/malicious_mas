# simulation.py
"""
去中心化拓扑
多智能体仿真主流程
在去中心化拓扑中，所有 agent 都是平等的，可以相互交流和影响。
"""
from . import roles, prev_num, discussion_num
from .prompts import DETECT_TEMPLATE, get_prompt
from utils.llm import llm_chat
from utils.metrics import get_predict_answer, parse_detect_result
from collections import Counter


def run_single_simulation(dataset_info, sample, condition, malicious_role, llm, model):
    """
    多智能体仿真主流程：让所有agent根据其角色和历史对话生成回复，最后由检测agent判断谁是malicious。
    在去中心化拓扑中，所有agent都是平等的，每个agent可以看到之前所有其他agent的讨论内容。
    
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
    prev_discussions = []
    agent_records = []      # 记录每个agent的prompt、think和answer
    records_str = ""        # 每个agent的结果记录，用于判断恶意agent
    all_predict_answers = []  # 记录所有agent的预测答案，用于计算众数

    # 构建问答参数
    format_kwargs = {
        "question": sample.get('question', ''),
        "correct_answer": sample.get('answer', ''),
        "prev_discussions": "No previous discussions yet."      # 初始状态没有之前的讨论
    }

    # 构建选项参数
    if dataset_info['type'] == 'multiple_choice' and 'options' in sample:
        format_kwargs['choices'] = "/".join([chr(i + 65) for i in range(len(sample['options']))])
        format_kwargs['options'] = "\n".join(sample['options'])

    # 运行每个agent
    for role in [roles[i % len(roles)] for i in range(discussion_num)]:
        # 构建提示词
        prompt = get_prompt(dataset_info, role, condition, malicious_role).format(**format_kwargs)
        # LLM推理
        think, answer = llm_chat(prompt, llm, model)
        # 解析预测结果
        predict_answer = get_predict_answer(answer, dataset_info)
        # 记录agent结果
        agent_records.append({"role": role, "prompt": prompt, "think": think, "answer": answer, "predict_answer": predict_answer})
        records_str += f"\n{role}: {answer}"
        
        # 记录预测答案
        if predict_answer is not None:
            all_predict_answers.append(predict_answer)
        
        # 更新prev_content，使其包含之前所有agent的讨论内容
        prev_discussions.append(answer)
        format_kwargs['prev_discussions'] = "\n".join(prev_discussions[-prev_num:])
        format_kwargs[role + "_answer"] = answer

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
        "predict_role": predict_role,
    })
    
    # 计算所有agent答案的众数作为最终预测结果
    if all_predict_answers:
        # 使用Counter计算每个答案的出现次数
        counter = Counter(all_predict_answers)
        # 获取出现次数最多的答案作为众数
        most_common = counter.most_common(1)[0][0]
        predict_answer = most_common
    else:
        # 如果没有有效的预测答案，保持原来的行为
        predict_answer = None
    
    return agent_records, predict_answer, predict_role