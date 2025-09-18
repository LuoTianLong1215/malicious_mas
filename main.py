# main.py
"""
主入口，负责参数解析、数据加载、调用 simulation、输出结果等。
支持多种数据集：MMLU、MMLU-Pro、GSM8K、MATH、HumanEval
"""

import argparse
import os
import time
import traceback

import hierarchical_topology
import centralized_topology
import decentralized_topology
from utils.utils import set_seed, get_result_dir
from utils.dataset_loader import create_dataset_loader
from utils.metrics import compare_answers
from utils.result_writer import write_agent_records, write_stats

conditions = ['No Malicious', 'Simple Malicious', 'Framing Malicious']

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

def run_simulation(run_single_simulation, dataset_info, samples, output_dir, malicious_role, llm, model):
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

def main():
    # 第一步：创建基础解析器，只包含拓扑参数
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('--topology', choices=['hierarchical', 'centralized', 'decentralized'], help='拓扑策略')
    
    # 解析拓扑参数
    args, remaining_argv = base_parser.parse_known_args()

    topology = args.topology
    if topology == 'hierarchical':
        run_single_simulation = hierarchical_topology.run_single_simulation
    elif topology == 'centralized':
        run_single_simulation = centralized_topology.run_single_simulation
    elif topology == 'decentralized':
        run_single_simulation = decentralized_topology.run_single_simulation
    else:
        raise ValueError(f"未知的拓扑类型: {topology}")
    
    # 第二步：创建完整解析器
    parser = argparse.ArgumentParser(description='Multi-Agent Malicious Detection System', parents=[base_parser])
    parser.add_argument('--dataset', nargs='+', default=['mmlu', 'mmlu_pro', 'gsm8k', 'math'], choices=['mmlu', 'mmlu_pro', 'gsm8k', 'math', 'humaneval'], help='数据集 mmlu, mmlu_pre: 选择; gsm8k, math: 数学; humaneval: 代码')
    parser.add_argument('--llm', default='ollama', choices=['api', 'ollama'], help='模型调用方式 api: 调用api; ollama: 调用ollama模型')
    parser.add_argument('--model', type=str, default='qwen3:8b', help='模型名称')
    parser.add_argument('--sample_size', type=int, default=50, help='样本数量')
    parser.add_argument('--random_seed', type=int, default=0, help='随机种子')
    
    # 根据拓扑类型设置malicious_role参数选项
    if topology == 'hierarchical':
        parser.add_argument('--malicious_roles', nargs='+', default=hierarchical_topology.roles, choices=hierarchical_topology.roles, help=hierarchical_topology.help)
    elif topology == 'centralized':
        parser.add_argument('--malicious_roles', nargs='+', default=centralized_topology.roles, choices=centralized_topology.roles, help=centralized_topology.help)
    elif topology == 'decentralized':
        parser.add_argument('--malicious_roles', nargs='+', default=decentralized_topology.roles, choices=decentralized_topology.roles, help=decentralized_topology.help)
    else:
        raise ValueError(f"未知的拓扑类型: {topology}")
    
    # 解析所有参数
    args = parser.parse_args(remaining_argv)
    
    for malicious_role in args.malicious_roles:
        for dataset_name in args.dataset:
            print("=" * 100)

            # 设置随机种子
            set_seed(args.random_seed)

            # 创建数据集加载器
            dataset_loader = create_dataset_loader(
                dataset_name=dataset_name,
                sample_size=args.sample_size,
                random_seed=args.random_seed
            )
            
            # 加载数据集
            print(f"Load {dataset_name} Dataset...")
            samples = dataset_loader.load_dataset()
            
            if not samples:
                print(f"Load {dataset_name} Dataset Failed")
                continue
            
            print(f"Load {len(samples)} Samples from {dataset_name} Dataset")
            
            # 获取数据集信息
            dataset_info = dataset_loader.get_dataset_info()
            
            # 设置输出目录
            results_dir = get_result_dir(dataset_info['name'], topology, malicious_role, args.model)
            os.makedirs(results_dir, exist_ok=True)
            
            print(f"Dataset Name: {dataset_name}")
            print(f"Dataset Type: {dataset_info['type']}")
            print(f"Model: {args.model}")
            print(f"Sample Size: {args.sample_size}")
            print(f"Output Directory: {results_dir}")
            print(f"Topology: {topology}")
            print(f"Malicious Role: {malicious_role}")
            print("=" * 100)
            
            
            run_simulation(run_single_simulation, dataset_info, samples, results_dir, malicious_role, args.llm, args.model)

if __name__ == '__main__':
    # nohup python -u main.py > output.log 2>&1 &
    # echo $! > output.pid
    main()
