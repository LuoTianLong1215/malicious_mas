# utils/config_loader.py
"""
YAML 配置文件加载与校验
"""

import yaml

# 所有合法的攻击条件
VALID_CONDITIONS = [
    'No Malicious',
    'Simple Malicious',
    'Framing Malicious',
    'PsySafe Malicious',
    'IntentionHiding Malicious',
]

# 所有合法的拓扑类型及其对应的角色
VALID_TOPOLOGIES = {
    'hierarchical': ['Analyst', 'Solver', 'Validator'],
    'centralized': ['Worker1', 'Worker2', 'Central'],
    'decentralized': ['Agent1', 'Agent2', 'Agent3'],
}

# 所有合法的数据集
VALID_DATASETS = ['mmlu', 'mmlu_pro', 'gsm8k', 'math', 'humaneval']


def load_config(config_path: str) -> dict:
    """
    加载 YAML 配置文件并校验。
    参数：
        config_path: YAML 配置文件路径
    返回：
        校验通过的配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config


def validate_config(config: dict):
    """
    校验配置文件的完整性和合法性。
    """
    # 校验全局字段
    for field in ['llm', 'model', 'sample_size', 'random_seed']:
        if field not in config:
            raise ValueError(f"缺少必需的全局配置字段: {field}")

    if config['llm'] not in ['api', 'ollama']:
        raise ValueError(f"llm 必须为 'api' 或 'ollama'，当前值: {config['llm']}")

    if not isinstance(config['sample_size'], int) or config['sample_size'] <= 0:
        raise ValueError(f"sample_size 必须为正整数，当前值: {config['sample_size']}")

    if not isinstance(config['random_seed'], int):
        raise ValueError(f"random_seed 必须为整数，当前值: {config['random_seed']}")

    # 校验 experiments
    if 'experiments' not in config or not config['experiments']:
        raise ValueError("必须至少配置一个 experiment")

    for i, exp in enumerate(config['experiments']):
        # 校验 topology
        if 'topology' not in exp:
            raise ValueError(f"experiment[{i}] 缺少 topology 字段")
        if exp['topology'] not in VALID_TOPOLOGIES:
            raise ValueError(f"experiment[{i}] 的 topology '{exp['topology']}' 不合法，可选值: {list(VALID_TOPOLOGIES.keys())}")

        # 校验 conditions
        if 'conditions' not in exp or not exp['conditions']:
            raise ValueError(f"experiment[{i}] 必须至少配置一个 condition")
        for cond in exp['conditions']:
            if cond not in VALID_CONDITIONS:
                raise ValueError(f"experiment[{i}] 的 condition '{cond}' 不合法，可选值: {VALID_CONDITIONS}")

        # 校验 malicious_roles
        if 'malicious_roles' not in exp or not exp['malicious_roles']:
            raise ValueError(f"experiment[{i}] 必须至少配置一个 malicious_role")
        valid_roles = VALID_TOPOLOGIES[exp['topology']]
        for role in exp['malicious_roles']:
            if role not in valid_roles:
                raise ValueError(f"experiment[{i}] 的 malicious_role '{role}' 不合法，topology '{exp['topology']}' 可选角色: {valid_roles}")

        # 校验 datasets
        if 'datasets' not in exp or not exp['datasets']:
            raise ValueError(f"experiment[{i}] 必须至少配置一个 dataset")
        for ds in exp['datasets']:
            if ds not in VALID_DATASETS:
                raise ValueError(f"experiment[{i}] 的 dataset '{ds}' 不合法，可选值: {VALID_DATASETS}")
