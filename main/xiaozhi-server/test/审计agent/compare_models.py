"""
模型对比测试脚本

该脚本可以同时测试多个模型（如DeepSeek-V3和glm-4-flash），并生成对比报告。
"""

import asyncio
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_test(provider: str, rounds: int = 3):
    """运行单个模型的测试"""
    script_dir = Path(__file__).parent
    metrics_script = script_dir / "query_categorization_metrics.py"
    
    output_json = script_dir / f"test_results_{provider}.json"
    
    print(f"\n{'=' * 80}")
    print(f"开始测试 {provider.upper()} 模型")
    print(f"{'=' * 80}\n")
    
    cmd = [
        sys.executable,
        str(metrics_script),
        "--provider", provider,
        "--rounds", str(rounds),
        "--output-json", str(output_json)
    ]
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"错误: {provider} 模型测试失败")
        return None
    
    return str(output_json)


def load_results(json_path: str):
    """加载测试结果"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_results(results_dict: dict):
    """对比多个模型的测试结果"""
    print("\n" + "=" * 80)
    print("模型对比报告")
    print("=" * 80)
    print(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 提取关键指标
    comparison_data = []
    
    for provider, data in results_dict.items():
        # 获取最后一轮的数据
        last_round = data['rounds'][-1]
        overall_metrics = last_round['overall_metrics']
        tool_metrics = last_round['tool_call_metrics']
        
        comparison_data.append({
            'provider': provider,
            'model': data['meta']['model'],
            'accuracy': overall_metrics['accuracy'],
            'macro_f1': overall_metrics['macro_f1'],
            'weighted_f1': overall_metrics['weighted_f1'],
            'tool_call_success_rate': tool_metrics['tool_call_success_rate'],
            'no_tool_call_rate': tool_metrics['no_tool_call_rate'],
            'tool_hallucination_rate': tool_metrics['tool_hallucination_rate'],
            'avg_response_time': overall_metrics['avg_response_time'],
        })
    
    # 打印对比表格
    print("\n" + "-" * 80)
    print("核心指标对比")
    print("-" * 80)
    
    # 表头
    header = f"{'指标':<30} " + " ".join([f"{d['provider']:<15}" for d in comparison_data])
    print(header)
    print("-" * len(header))
    
    # 数据行
    metrics = [
        ('准确率 (Accuracy)', 'accuracy', '%'),
        ('Macro F1-Score', 'macro_f1', '%'),
        ('Weighted F1-Score', 'weighted_f1', '%'),
        ('工具调用成功率', 'tool_call_success_rate', '%'),
        ('无工具调用率', 'no_tool_call_rate', '%'),
        ('工具幻觉率', 'tool_hallucination_rate', '%'),
        ('平均响应时间 (秒)', 'avg_response_time', 's'),
    ]
    
    for label, key, unit in metrics:
        row = f"{label:<30} "
        for d in comparison_data:
            value = d[key]
            if unit == '%':
                row += f"{value*100:>14.2f}% "
            elif unit == 's':
                row += f"{value:>14.3f}s "
            else:
                row += f"{value:>15} "
        print(row)
    
    # 找出最佳模型
    print("\n" + "-" * 80)
    print("最佳模型推荐")
    print("-" * 80)
    
    best_accuracy = max(comparison_data, key=lambda x: x['accuracy'])
    best_f1 = max(comparison_data, key=lambda x: x['weighted_f1'])
    best_tool_success = max(comparison_data, key=lambda x: x['tool_call_success_rate'])
    fastest = min(comparison_data, key=lambda x: x['avg_response_time'])
    
    print(f"\n最高准确率: {best_accuracy['provider']} ({best_accuracy['accuracy']*100:.2f}%)")
    print(f"最高F1分数: {best_f1['provider']} ({best_f1['weighted_f1']*100:.2f}%)")
    print(f"最高工具调用成功率: {best_tool_success['provider']} ({best_tool_success['tool_call_success_rate']*100:.2f}%)")
    print(f"最快响应速度: {fastest['provider']} ({fastest['avg_response_time']:.3f}秒)")
    
    # 综合评分
    print("\n" + "-" * 80)
    print("综合评分 (加权)")
    print("-" * 80)
    print("评分规则: 准确率(40%) + F1分数(30%) + 工具调用成功率(20%) + 响应速度(10%)")
    
    for d in comparison_data:
        # 响应时间需要归一化（越小越好）
        min_time = min(cd['avg_response_time'] for cd in comparison_data)
        max_time = max(cd['avg_response_time'] for cd in comparison_data)
        time_score = 1.0 - (d['avg_response_time'] - min_time) / (max_time - min_time + 0.001)
        
        score = (
            d['accuracy'] * 0.4 +
            d['weighted_f1'] * 0.3 +
            d['tool_call_success_rate'] * 0.2 +
            time_score * 0.1
        )
        print(f"\n{d['provider']:>10}: {score*100:.2f}分")
        print(f"  模型: {d['model']}")
    
    print("\n" + "=" * 80)


def main():
    """主函数"""
    print("=" * 80)
    print("多模型对比测试")
    print("=" * 80)
    print("\n将依次测试以下模型：")
    print("  1. DeepSeek-V3 (deepseek)")
    print("  2. GLM-4-Flash (zhipu)")
    print("\n每个模型将进行3轮测试")
    
    input("\n按Enter键开始测试...")
    
    # 测试所有模型
    providers = ["deepseek", "zhipu"]
    results_dict = {}
    
    for provider in providers:
        result_path = run_test(provider, rounds=3)
        if result_path:
            results_dict[provider] = load_results(result_path)
        else:
            print(f"警告: {provider} 模型测试失败，将跳过")
    
    if len(results_dict) < 2:
        print("\n错误: 至少需要2个模型的测试结果才能进行对比")
        return
    
    # 生成对比报告
    compare_results(results_dict)
    
    # 保存对比报告
    script_dir = Path(__file__).parent
    comparison_json = script_dir / "model_comparison.json"
    
    comparison_data = {
        'timestamp': datetime.now().isoformat(),
        'models': list(results_dict.keys()),
        'results': results_dict
    }
    
    with open(comparison_json, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n对比报告已保存到: {comparison_json}")
    print("\n测试完成！")


if __name__ == "__main__":
    main()

