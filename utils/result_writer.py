# result_writer.py
"""
结果输出相关函数。
"""
import json

def write_agent_records(records, out_path):
    """
    将所有样本下三种条件下的agent对话记录写入JSON文件，便于后续分析。
    
    参数：
        records (List[Dict]): 每个元素为一个样本下的三种条件agent对话记录
        out_path (str): 输出文件路径
    
    返回值：
        无
    """
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)

def write_stats(stats_list, summary, out_path):
    """
    将每个样本的统计信息和最终汇总写入文本文件。
    
    参数：
        stats_list (List[Dict]): 每个元素为一个样本的统计信息（耗时和各率）
        summary (Dict): 最终三种条件的平均统计结果
        out_path (str): 输出文件路径
    
    返回值：
        无
    """
    with open(out_path, 'w', encoding='utf-8') as f:
        for i, stat in enumerate(stats_list):
            f.write(f"[Sample {i+1}]\n")
            f.write(f"  Time: {stat['time']:.2f} seconds\n")
            for cond, rates in stat['rates'].items():
                f.write(f"  [{cond}] Correct: {rates['correct']:.3f}, Detection: {rates['detection']:.3f}, Framing: {rates['framing']:.3f}, Unable: {rates['unable']:.3f}\n")
            f.write("\n")
        f.write("\nFinal Summary:\n")
        for cond, rates in summary.items():
            f.write(f"[{cond}] Correct: {rates['correct']:.3f}, Detection: {rates['detection']:.3f}, Framing: {rates['framing']:.3f}, Unable: {rates['unable']:.3f}\n")
