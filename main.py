# main.py
"""
主入口，负责配置加载、数据加载、调用 simulation、输出结果等。
支持多种数据集：MMLU、MMLU-Pro、GSM8K、MATH、HumanEval
运行方式：python main.py --config config_example.yaml
"""

import argparse
import os

import hierarchical_topology
import centralized_topology
import decentralized_topology
from simulation import run_simulation
from utils.utils import save_excel, set_seed, get_result_dir
from utils.dataset_loader import create_dataset_loader
from utils.config_loader import load_config

# 结果文件夹
base_dir = os.path.join(os.path.dirname(__file__), 'multiagent_eval_results')
# 结果Excel
result_excel = os.path.join(base_dir, 'multiagent_eval_results.xlsx')

# 拓扑模块映射
TOPOLOGY_MODULES = {
    'hierarchical': hierarchical_topology,
    'centralized': centralized_topology,
    'decentralized': decentralized_topology,
}


def main():
    parser = argparse.ArgumentParser(description='Multi-Agent Malicious Detection System')
    parser.add_argument('--config', type=str, required=True, help='YAML 配置文件路径')
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    for experiment in config['experiments']:
        topology_name = experiment['topology']
        conditions = experiment['conditions']
        topology_module = TOPOLOGY_MODULES[topology_name]

        for malicious_role in experiment['malicious_roles']:
            for dataset_name in experiment['datasets']:
                print("=" * 100)

                # 设置随机种子
                set_seed(config['random_seed'])

                # 创建数据集加载器
                dataset_loader = create_dataset_loader(
                    dataset_name=dataset_name,
                    sample_size=config['sample_size'],
                    random_seed=config['random_seed']
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
                results_dir = get_result_dir(dataset_info['name'], topology_name, malicious_role, config['model'], base_dir)
                os.makedirs(results_dir, exist_ok=True)

                print(f"Dataset Name: {dataset_name}")
                print(f"Dataset Type: {dataset_info['type']}")
                print(f"Model: {config['model']}")
                print(f"Sample Size: {config['sample_size']}")
                print(f"Output Directory: {results_dir}")
                print(f"Topology: {topology_name}")
                print(f"Malicious Role: {malicious_role}")
                print(f"Conditions: {conditions}")
                print("=" * 100)

                run_simulation(
                    topology_module.run_single_simulation,
                    conditions,
                    dataset_info, samples, results_dir,
                    malicious_role, config['llm'], config['model']
                )


if __name__ == '__main__':
    main()
