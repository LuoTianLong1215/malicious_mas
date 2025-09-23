# simulation.py
"""
多智能体仿真主流程
"""

import os
import time
import traceback

from utils.metrics import compare_answers
from utils.result_writer import write_agent_records, write_stats

def update_stats_and_log(stats, idx, sample, condition, predict_answer, predict_answer_correct, predict_role, malicious_role, out_file):
    """
    更新统计信息并写入日志文件。
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

def run_simulation(run_single_simulation, conditions, dataset_info, samples, output_dir, malicious_role, llm, model):
    """
    多轮实验主控函数。对每个样本分别在三种攻击条件下运行仿真，统计各类指标并输出详细日志和汇总文件。
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

                # 保存结果
                out_files[condition].write(f"====================== [Sample {idx + 1: 02d}] ======================\n")
                out_files[condition].write(f"Question: {record['Question']}\n")
                out_files[condition].write(f"Options: {record.get('Options', 'N/A')}\n")
                out_files[condition].write(f"Ground Truth: {record['Answer']}\n")
                out_files[condition].write(f"Predict Answer: {predict_answer}\n")
                out_files[condition].write(f"Predict Answer Correct: {predict_answer_correct}\n")
                out_files[condition].write(f"Predict Role: {predict_role}\n")
                out_files[condition].write(f"Predict Role Correct: {predict_role == malicious_role}\n\n")
                for agent_record in agent_records:
                    out_files[condition].write(f"[Agent]: {agent_record['role']}\n")
                    out_files[condition].write(f"[Prompt]: \n{agent_record['prompt']}\n")
                    out_files[condition].write(f"[Answer]: {agent_record['answer']}\n")
                    out_files[condition].write(f"[Predict]: {agent_record['predict']}\n\n")
            
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
        out_files[condition].write(f"====================== Summary =====================\n")
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