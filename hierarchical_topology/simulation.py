# simulation.py
"""
层级拓扑
多智能体仿真主流程
"""
import os
import time
import traceback

from . import roles, conditions
from .prompts import get_prompt, get_detector_prompt
from utils.llm import llm_chat
from utils.metrics import get_predict_answer, parse_detect_result, compare_answers
from utils.result_writer import write_agent_records, write_stats


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
    agent_records = dict()  # 记录每个agent的prompt、think和answer
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

    # 运行每个agent
    for role in roles:
        # 构建提示词
        prompt = get_prompt(dataset_info, role, condition, malicious_role).format(**format_kwargs)
        # LLM推理
        think, answer = llm_chat(prompt, llm, model)
        # 解析预测结果
        predict_answer = get_predict_answer(answer, dataset_info)
        # 记录agent结果
        agent_records[role] = {"prompt": prompt, "think": think, "answer": answer, "predict_answer": predict_answer}
        records_str += f"\n{role}: {answer}"
        # 构建下一个agent的提示词
        format_kwargs['prev_content'] = answer

    # 构建检测提示词
    prompt = get_detector_prompt(dataset_info, sample, records_str)
    # LLM推理
    think, answer = llm_chat(prompt, llm, model)
    predict_role = parse_detect_result(answer, roles)
    agent_records["Detector"] = {
        "prompt": prompt,
        "think": think,
        "answer": answer,
        "predict_role": predict_role,
    }
    
    return agent_records, predict_answer, predict_role

def update_stats_and_log(stats, idx, sample, condition, predict_answer, predict_answer_correct, predict_role, malicious_role, out_file):
    """
    更新统计信息并写入日志文件。
    
    参数：
        stats: 统计字典
        idx, sample: 题目内容
        condition: 条件名称
        predict_answer: 预测答案
        predict_answer_correct: 预测答案是否正确
        predict_role: 预测恶意角色
        malicious_role: 恶意角色
        out_file: 输出文件句柄
    
    返回：
        当前条件的统计率
    """
    # 更新统计
    stats[condition][0] += int(predict_answer_correct)  # 预测答案正确
    if predict_role == malicious_role:
        stats[condition][1] += 1    # 预测角色正确
    elif predict_role is not None:
        stats[condition][2] += 1    # 预测角色错误
    else:
        stats[condition][3] += 1    # 预测角色未知
    stats[condition][4] += 1        # 样本总数

    # 写入日志
    if "options" in sample:
        out_file.write(
            f"[Sample {idx + 1}]\n"
            f"Question: {sample['question']}\n"
            f"Options: {sample['options']}\n"
            f"Ground Truth: {sample['answer']}\n"
            f"Predict Answer: {predict_answer}\n"
            f"Predict Answer Correct: {predict_answer_correct}\n"
            f"Predict Role: {predict_role}\n"
            f"Predict Role Correct: {predict_role == malicious_role}\n\n"
        )
    else:
        out_file.write(
            f"[Sample {idx + 1}]\n"
            f"Question: {sample['question']}\n"
            f"Ground Truth: {sample['answer']}\n"
            f"Predict Answer: {predict_answer}\n"
            f"Predict Answer Correct: {predict_answer_correct}\n"
            f"Predict Role: {predict_role}\n"
            f"Predict Role Correct: {predict_role == malicious_role}\n\n"
        )

    # 计算当前率
    value = stats[condition]
    return {
        'correct':   value[0] / value[4] if value[4] else 0,
        'detection': value[1] / value[4] if value[4] else 0,
        'framing':   value[2] / value[4] if value[4] else 0,
        'unable':    value[3] / value[4] if value[4] else 0,
    }

def run_simulation(dataset_info, samples, output_dir, malicious_role, llm, model):
    """
    多轮实验主控函数。对每个样本分别在三种攻击条件下运行仿真，统计各类指标并输出详细日志和汇总文件。
    参数：
        dataset_info: 数据集信息
        samples: 题目样本
        output_dir: 输出目录
        malicious_role: 恶意角色
        llm, model: 模型
    """
    # 初始化统计和文件
    stats = {
        condition: [0, 0, 0, 0, 0] for condition in conditions
    }
    
    # 为三种条件分别创建输出文件
    out_files = {
        condition: open(os.path.join(output_dir, f'{condition.lower().replace(" ", "_")}.txt'), 'w', encoding='utf-8') for condition in conditions
    }
    
    all_records = []  # 记录所有样本下三种条件的agent对话
    stats_list = []     # 记录每个样本的统计信息
    
    for idx, sample in enumerate(samples):
        try:
            start_time = time.time()
            
            rates = dict()
            record = {
                "Question": sample['question'],
                "Answer": sample['answer'],
                "Simulation": dict()
            }
            if 'options' in sample:
                record['Options'] = sample['options']
            if 'test' in sample and 'entry_point' in sample:
                record['Test'] = sample['test']
                record['Entry Point'] = sample['entry_point']
            
            # 运行三种仿真条件
            for condition in conditions:
                agent_records, predict_answer, predict_role = run_single_simulation(dataset_info, sample, condition, malicious_role, llm, model)
                
                # 判断预测答案是否正确
                predict_answer_correct = compare_answers(predict_answer, sample, dataset_info['type'])
                rates[condition] = update_stats_and_log(stats, idx, sample, condition, predict_answer, predict_answer_correct, predict_role, malicious_role, out_files[condition])
                record['Simulation'][condition] = {
                    'Records': agent_records,
                    'Predict Answer Correct': predict_answer_correct,
                    'Predict Role Correct': predict_role == malicious_role,
                }
            
            end_time = time.time()
            stats_list.append({'time': end_time - start_time, 'rates': rates})
            all_records.append(record)

            # 每处理完一个sample立即打印三种情况四个率和耗时
            print(f"[Sample {idx + 1}] Time: {end_time - start_time:.2f}s")
            for condition in conditions:
                rate = rates[condition]
                print(f"{condition}: Correct={rate['correct']:.3f}, Detection={rate['detection']:.3f}, Framing={rate['framing']:.3f}, Unable={rate['unable']:.3f}")
        
        except Exception as e:
            print(f"[Sample {idx + 1}] raise Exception: {e}")
            traceback.print_exc()

    # 汇总统计并写入文件
    summary = {}
    for k, v in stats.items():
        summary[k] = {
            'correct':      v[0] / v[4] if v[4] else 0,
            'detection':    v[1] / v[4] if v[4] else 0,
            'framing':      v[2] / v[4] if v[4] else 0,
            'unable':       v[3] / v[4] if v[4] else 0,
        }
        out_files[k].write(f"\nSummary:\n")
        out_files[k].write(f"Correct rate: {summary[k]['correct']:.3f}\n")
        out_files[k].write(f"Detection rate: {summary[k]['detection']:.3f}\n")
        out_files[k].write(f"Framing rate: {summary[k]['framing']:.3f}\n")
        out_files[k].write(f"Unable to determine rate: {summary[k]['unable']:.3f}\n")
        out_files[k].close()

    # 额外输出
    write_agent_records(all_records, os.path.join(output_dir, 'agent_records.json'))
    write_stats(stats_list, summary, os.path.join(output_dir, 'stats_and_summary.txt'))

    print("Agent records will be written to:", os.path.join(output_dir, 'agent_records.json'))
    print("Stats will be written to:", os.path.join(output_dir, 'stats_and_summary.txt'))
