# utils.py
"""
通用工具函数，如文件读写、日志、随机种子设置等。
"""
import random
import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font
import re
import traceback

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

def get_result_dir(subject, topology, malicious_role, model, base_dir):
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
    return os.path.join(base_dir, safe_model, topology, malicious_role, dir_name)

def save_excel(excel_path, results_dir, conditions):
    """
    读取模型文件夹下的拓扑策略、角色、数据集，相同数据集选择日期较新的，
    然后读取stats_and_summary.txt文件，获取三个conditions的Correct, Detection, Framing, Unable四个指标并打印到控制台。
    
    参数：
        excel_path (str): Excel文件路径
        results_dir (str): 结果目录路径
        conditions (list): 攻击条件列表
    
    返回值：
        无
    """
    
    try:
        # 定义字体颜色
        green_font = Font(color='00B050')
        red_font = Font(color='FF0000')
        black_font = Font(color='000000')
        
        # 加载Excel工作簿
        book = openpyxl.load_workbook(excel_path)

        # 遍历第一层子文件夹（模型名称）
        model_dirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
        
        for model_name in model_dirs:
            # 检查是否已经存在该模型名称的工作表，如果存在则跳过
            if model_name in book.sheetnames:
                sheet = book[model_name]
            else:
                # 复制template工作表并重命名为模型名称
                template_sheet = book['template']
                sheet= book.copy_worksheet(template_sheet)
                sheet.title = model_name

            model_path = os.path.join(results_dir, model_name)
            
            # 遍历第二层子文件夹（拓扑类型）
            topology_dirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
            
            for topology in topology_dirs:
                topology_path = os.path.join(model_path, topology)
                
                # 遍历第三层子文件夹（角色）
                role_dirs = [d for d in os.listdir(topology_path) if os.path.isdir(os.path.join(topology_path, d))]
                
                for role in role_dirs:
                    role_path = os.path.join(topology_path, role)
                    
                    # 遍历第四层子文件夹（数据集名称_时间）
                    dataset_dirs = [d for d in os.listdir(role_path) if os.path.isdir(os.path.join(role_path, d))]
                    
                    # 按数据集名称分组，只对相同名称的数据集比较时间戳
                    dataset_groups = {}
                    
                    for dataset_dir in dataset_dirs:
                        try:
                            # 提取数据集名称（假设格式为：datasetname_时间戳）
                            # 分割并移除最后一个时间戳部分
                            parts = dataset_dir.split('_')
                            # 尝试解析最后一部分为时间戳来确认
                            timestamp_part = parts[-1]
                            timestamp = datetime.strptime(timestamp_part, '%Y%m%d%H%M%S')
                            
                            # 重建数据集名称（去掉时间戳部分）
                            dataset_name = '_'.join(parts[:-1])
                            
                            # 将数据集添加到对应的组
                            if dataset_name not in dataset_groups:
                                dataset_groups[dataset_name] = []
                            dataset_groups[dataset_name].append((dataset_dir, timestamp))
                        except (ValueError, IndexError):
                            # 如果无法解析时间戳，跳过该文件夹
                            continue
                    
                    # 对于每个数据集名称组，选择时间戳最新的数据集
                    for dataset_name, datasets in dataset_groups.items():
                        # 按时间戳降序排序，选择最新的数据集
                        datasets.sort(key=lambda x: x[1], reverse=True)
                        latest_dataset = datasets[0][0]
                        
                        # 构建stats_and_summary.txt文件路径
                        stats_file_path = os.path.join(role_path, latest_dataset, 'stats_and_summary.txt')
                        
                        # 读取并解析stats_and_summary.txt文件
                        try:
                            with open(stats_file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # 使用正则表达式获取Final Summary:后的所有内容
                            match = re.search(r'Final Summary:(.*)', content, re.DOTALL)
                            if match:
                                summary_content = match.group(1)
                                for idx, condition in enumerate(conditions):
                                    # 构建正则表达式模式，匹配指定条件下的四个指标
                                    pattern = re.compile(
                                        rf'\[{re.escape(condition)}\] Correct: (\d+\.\d+), Detection: (\d+\.\d+), Framing: (\d+\.\d+), Unable: (\d+\.\d+)(?:\n|$)'
                                    )
                                    match = pattern.search(summary_content)
                                    if match:
                                        correct = float(match.group(1))
                                        detection = float(match.group(2))
                                        framing = float(match.group(3))
                                        unable = float(match.group(4))

                                        # 写入Excel
                                        for row in range(2, sheet.max_row + 1):
                                            # 检查topology、dataset、role、condition是否匹配
                                            # 处理合并单元格的情况
                                            row_topology = None
                                            row_dataset = None
                                            row_role = None
                                            row_condition = None
                                              
                                            # 检查当前行是否在某个合并区域内
                                            for merged_cell in sheet.merged_cells.ranges:
                                                if row >= merged_cell.min_row and row <= merged_cell.max_row:
                                                    # 获取合并区域左上角单元格的值
                                                    if merged_cell.min_col == 1:  # A列
                                                        row_topology = sheet.cell(row=merged_cell.min_row, column=1).value
                                                    if merged_cell.min_col == 2:  # B列
                                                        row_dataset = sheet.cell(row=merged_cell.min_row, column=2).value
                                                    if merged_cell.min_col == 3:  # C列
                                                        row_role = sheet.cell(row=merged_cell.min_row, column=3).value
                                                    if merged_cell.min_col == 4:  # D列
                                                        row_condition = sheet.cell(row=merged_cell.min_row, column=4).value
                                            
                                            # 如果不在合并区域内，直接获取单元格值
                                            if row_topology is None:
                                                row_topology = sheet[f'A{row}'].value
                                            if row_dataset is None:
                                                row_dataset = sheet[f'B{row}'].value
                                            if row_role is None:
                                                row_role = sheet[f'C{row}'].value
                                            if row_condition is None:
                                                row_condition = sheet[f'D{row}'].value
                                            
                                            if (row_topology == topology and 
                                                row_dataset == dataset_name and 
                                                row_role == role and 
                                                row_condition == condition):
                                                # 找到匹配的行，写入四个指标值
                                                sheet[f'E{row}'].value = correct    # Correct的第一列
                                                sheet[f'H{row}'].value = detection  # Detection的第一列
                                                sheet[f'K{row}'].value = framing    # Framing的第一列
                                                sheet[f'N{row}'].value = unable     # Unable的第一列
                                                 
                                                # 设置颜色 - 修改颜色设置逻辑，避免None值
                                                for i in range(idx):
                                                    try:
                                                        compare_correct = float(sheet[f'E{row-idx+i}'].value)
                                                        compare_detection = float(sheet[f'H{row-idx+i}'].value)
                                                        compare_framing = float(sheet[f'K{row-idx+i}'].value)
                                                        compare_unable = float(sheet[f'N{row-idx+i}'].value)
                                                         
                                                        sheet[f'{chr(ord("E")+i+1)}{row}'].font = green_font if correct < compare_correct else red_font if correct > compare_correct else black_font
                                                        sheet[f'{chr(ord("H")+i+1)}{row}'].font = green_font if detection < compare_detection else red_font if detection > compare_detection else black_font
                                                        sheet[f'{chr(ord("K")+i+1)}{row}'].font = green_font if framing > compare_framing else red_font if framing < compare_framing else black_font
                                                        sheet[f'{chr(ord("N")+i+1)}{row}'].font = green_font if unable > compare_unable else red_font if unable < compare_unable else black_font
                                                    except (ValueError, TypeError):
                                                        continue
                                                break
                            
                        except Exception:
                            print(traceback.format_exc())

        # 保存工作簿
        book.save(excel_path)
        
    except Exception:
        print(traceback.format_exc())