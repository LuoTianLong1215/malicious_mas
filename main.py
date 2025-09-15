# main.py
"""
主入口，负责参数解析、数据加载、调用 simulation、输出结果等。
支持多种数据集：MMLU、MMLU-Pro、GSM8K、MATH、HumanEval
"""

import argparse
import os

import hierarchical_topology
from utils.utils import set_seed, get_result_dir
from utils.dataset_loader import create_dataset_loader

def main():
    # 第一步：创建基础解析器，只包含拓扑参数
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('--topology', default='hierarchical', choices=['hierarchical', 'centralized', 'decentralized'], help='拓扑策略')
    
    # 解析拓扑参数
    args, remaining_argv = base_parser.parse_known_args()
    
    # 第二步：创建完整解析器
    parser = argparse.ArgumentParser(description='Multi-Agent Malicious Detection System', parents=[base_parser])
    parser.add_argument('--dataset', nargs='+', default=['mmlu', 'mmlu_pro', 'gsm8k', 'math'], choices=['mmlu', 'mmlu_pro', 'gsm8k', 'math', 'humaneval'], help='数据集 mmlu, mmlu_pre: 选择; gsm8k, math: 数学; humaneval: 代码')
    parser.add_argument('--llm', default='ollama', choices=['api', 'ollama'], help='模型调用方式 api: 调用api; ollama: 调用ollama模型')
    parser.add_argument('--model', type=str, default='qwen3:8b', help='模型名称')
    parser.add_argument('--sample_size', type=int, default=50, help='样本数量')
    parser.add_argument('--random_seed', type=int, default=0, help='随机种子')
    
    # 根据拓扑类型设置malicious_role参数选项
    if args.topology == 'hierarchical':
        parser.add_argument('--malicious_role', default='Solver', choices=hierarchical_topology.roles, help='恶意角色 Analyst: 分析; Solver: 解决; Validator: 验证')
    elif args.topology == 'centralized':
        parser.add_argument('--malicious_role', default='centralized_1', choices=['centralized_1', 'centralized_2', 'centralized_3'], help='恶意角色 centralized_1: 中心1; centralized_2: 中心2; centralized_3: 中心3')
    elif args.topology == 'decentralized':
        parser.add_argument('--malicious_role', default='decentralized_1', choices=['decentralized_1', 'decentralized_2', 'decentralized_3'], help='恶意角色 decentralized_1:  decentralized_2: decentralized_3:')
    
    # 解析所有参数
    args = parser.parse_args(remaining_argv)
    
    # 依次处理多个数据集
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
        results_dir = get_result_dir(dataset_info['name'], args.topology, args.malicious_role, args.model)
        os.makedirs(results_dir, exist_ok=True)
        
        print(f"Dataset Name: {dataset_name}")
        print(f"Dataset Type: {dataset_info['type']}")
        print(f"Model: {args.model}")
        print(f"Sample Size: {args.sample_size}")
        print(f"Output Directory: {results_dir}")
        print(f"Topology: {args.topology}")
        print(f"Malicious Role: {args.malicious_role}")
        print("=" * 100)
        
        if args.topology == 'hierarchical':
            # 运行实验
            hierarchical_topology.run_simulation(dataset_info, samples, results_dir, args.malicious_role, args.llm, args.model)

if __name__ == '__main__':
    # nohup python -u main.py > output.log 2>&1 &
    # echo $! > output.pid
    main()
