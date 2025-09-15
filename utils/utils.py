# utils.py
"""
通用工具函数，如文件读写、日志、随机种子设置等。
"""
import random
import os
from datetime import datetime

def set_seed(seed):
    """
    设置全局随机种子，保证实验可复现。
    
    参数：
        seed (int): 随机种子数值
    
    返回值：
        无
    """
    random.seed(seed)

def get_time_str():
    """
    获取当前时间字符串，格式为YYYYMMDD-HHMMSS。
    用于生成唯一的结果目录名或文件名。
    
    参数：
        无
    
    返回值：
        str: 当前时间字符串，格式为'YYYYMMDDHHMMSS'
    """
    return datetime.now().strftime('%Y%m%d%H%M%S')

def get_result_dir(subject, topology, malicious_role, model, base_dir='multiagent_eval_results'):
    """
    根据科目、拓扑结构、恶意角色、模型和当前时间生成唯一的结果输出目录。
    
    参数：
        subject (str): 科目名
        topology (str): 拓扑结构名称
        malicious_role (str): 恶意角色名称
        model (str): 模型名称
        base_dir (str): 结果主目录，默认为'multiagent_eval_results'
    
    返回值：
        str: 唯一的结果输出目录路径
    """
    time_str = get_time_str()
    # 替换非法字符，保证目录名安全
    safe_subject = subject.replace(' ', '_').replace('/', '_')
    safe_model = model.replace(':', '-').replace('/', '_')
    dir_name = f"{safe_subject}_{time_str}"
    return os.path.join(base_dir, topology, malicious_role, safe_model, dir_name)
