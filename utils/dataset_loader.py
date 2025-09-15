# dataset_loader.py
"""
通用数据集加载器，支持MMLU、MMLU-Pro、GSM8K、MATH和HumanEval数据集。
"""
import os

# 设置Hugging Face镜像地址
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import os
from typing import List, Dict, Any
from datasets import load_dataset
import random

class DatasetLoader:
    """
    通用数据集加载器类，支持多种数据集格式的统一加载。
    """
    
    def __init__(self, dataset_name: str, sample_size: int = 50, random_seed: int = 42):
        """
        初始化数据集加载器。
        
        Args:
            dataset_name: 数据集名称 ('mmlu', 'mmlu_pro', 'gsm8k', 'math', 'humaneval')
            sample_size: 采样数量
            random_seed: 随机种子
        """
        self.dataset_name = dataset_name.lower()
        # 保存到项目根路径下的data文件夹
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = os.path.join(project_root, 'data', dataset_name)
        self.sample_size = sample_size
        self.random_seed = random_seed
        random.seed(random_seed)
    
    def _load_and_sample_dataset(self, dataset_config: Dict[str, Any], processor_func) -> List[Dict[str, Any]]:
        """
        通用的数据集加载和采样方法。
        
        Args:
            dataset_config: 数据集配置，包含name, subset, split等
            processor_func: 数据处理函数，将原始数据转换为标准格式
        
        Returns:
            处理后的样本列表
        """
        try:
            # 加载数据集
            if 'subset' in dataset_config:
                dataset = load_dataset(dataset_config['name'], dataset_config['subset'], cache_dir=self.cache_dir)
            else:
                dataset = load_dataset(dataset_config['name'], cache_dir=self.cache_dir)
            
            data = dataset[dataset_config['split']]
            
            # 处理数据
            all_samples = []
            for item in data:
                processed_item = processor_func(item)
                if processed_item:
                    all_samples.append(processed_item)
            
            # 随机采样
            random.shuffle(all_samples)
            return all_samples[:self.sample_size]
            
        except Exception as e:
            print(f"无法加载数据集 {dataset_config['name']}: {e}")
            return []
        
    def _process_mmlu_item(self, item) -> Dict[str, Any]:
        """处理MMLU数据项"""
        return {
            'question': item['question'],
            'options': [f"{chr(idx + 65)}. {choice}" for idx, choice in enumerate(item['choices'])],
            'answer': chr(item['answer'] + 65),
        }
    
    def _process_mmlu_pro_item(self, item) -> Dict[str, Any]:
        """处理MMLU-Pro数据项"""
        return {
            'question': item['question'],
            'options': [f"{chr(idx + 65)}. {option}" for idx, option in enumerate(item['options'])],
            'answer': item['answer'],
        }
    
    def _process_gsm8k_item(self, item) -> Dict[str, Any]:
        """处理GSM8K数据项"""
        # 提取最终答案
        answer_text = item['answer']
        if '####' in answer_text:
            answer = answer_text.split('####')[-1].strip()
        else:
            answer = answer_text.strip()
        
        return {
            'question': item['question'],
            'answer': answer,
        }
    
    def _process_math_item(self, item) -> Dict[str, Any]:
        """处理MATH数据项"""
        # 尝试提取boxed答案
        solution = item['solution']
        if '\\boxed{' in solution:
            answer = solution.split('\\boxed{')[-1].split('}')[0]
        elif '\\boxed' in solution:
            answer = solution.split('\\boxed')[-1].strip()
        else:
            answer = solution.strip()
        
        return {
            'question': item['problem'],
            'answer': answer,
        }
    
    def _process_humaneval_item(self, item) -> Dict[str, Any]:
        """处理HumanEval数据项"""
        return {
            'question': item['prompt'],
            'test': item['test'],
            'answer': item['canonical_solution'],
            'entry_point': item['entry_point'],
        }
    
    def load_mmlu(self) -> List[Dict[str, Any]]:
        """
        加载MMLU数据集（从Hugging Face）。
        格式：question, options, answer
        """
        dataset_config = {
            'name': 'cais/mmlu',
            'subset': 'all',
            'split': 'test'
        }
        return self._load_and_sample_dataset(dataset_config, self._process_mmlu_item)
    
    def load_mmlu_pro(self) -> List[Dict[str, Any]]:
        """
        加载MMLU-Pro数据集。
        格式：question, options, answer
        """
        dataset_config = {
            'name': 'TIGER-Lab/MMLU-Pro',
            'split': 'test'
        }
        return self._load_and_sample_dataset(dataset_config, self._process_mmlu_pro_item)
    
    def load_gsm8k(self) -> List[Dict[str, Any]]:
        """
        加载GSM8K数据集。
        格式：question, answer
        """
        dataset_config = {
            'name': 'openai/gsm8k',
            'subset': 'main',
            'split': 'test'
        }
        return self._load_and_sample_dataset(dataset_config, self._process_gsm8k_item)
    
    def load_math(self) -> List[Dict[str, Any]]:
        """
        加载MATH数据集。
        格式：question, answer
        """
        dataset_config = {
            'name': 'qwedsacf/competition_math',
            'split': 'train'
        }
        return self._load_and_sample_dataset(dataset_config, self._process_math_item)
    
    def load_humaneval(self) -> List[Dict[str, Any]]:
        """
        加载HumanEval数据集。
        格式：question, test, answer
        """
        dataset_config = {
            'name': 'openai/openai_humaneval',
            'split': 'test'
        }
        return self._load_and_sample_dataset(dataset_config, self._process_humaneval_item)
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """
        根据数据集名称加载相应的数据集。
        """
        if self.dataset_name == 'mmlu':
            return self.load_mmlu()
        elif self.dataset_name == 'mmlu_pro':
            return self.load_mmlu_pro()
        elif self.dataset_name == 'gsm8k':
            return self.load_gsm8k()
        elif self.dataset_name == 'math':
            return self.load_math()
        elif self.dataset_name == 'humaneval':
            return self.load_humaneval()
        else:
            raise ValueError(f"不支持的数据集: {self.dataset_name}")
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """
        获取数据集信息。
        """
        info = {
            'mmlu': {
                'name': 'MMLU',
                'type': 'multiple_choice',
                'description': '大规模多任务语言理解数据集',
                'options_count': 4
            },
            'mmlu_pro': {
                'name': 'MMLU-Pro',
                'type': 'multiple_choice',
                'description': 'MMLU增强版，更具挑战性的推理问题',
                'options_count': 10
            },
            'gsm8k': {
                'name': 'GSM8K',
                'type': 'math_reasoning',
                'description': '小学数学问题数据集',
                'options_count': 0
            },
            'math': {
                'name': 'MATH',
                'type': 'math_reasoning',
                'description': '数学竞赛问题数据集',
                'options_count': 0
            },
            'humaneval': {
                'name': 'HumanEval',
                'type': 'code_generation',
                'description': '编程问题数据集',
                'options_count': 0
            }
        }
        return info.get(self.dataset_name, {})

def create_dataset_loader(dataset_name: str, **kwargs) -> DatasetLoader:
    """
    创建数据集加载器的工厂函数。
    """
    return DatasetLoader(dataset_name, **kwargs)
