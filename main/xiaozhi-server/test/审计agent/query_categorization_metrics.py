"""
审计Agent工具分类准确率测试脚本

该脚本用于评估模型在选择正确工具（regulation_search vs case_retrieval）时的性能表现。
支持多轮测试、并行执行、详细的metrics统计和结果可视化。
"""

import argparse
import asyncio
import csv
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter
import statistics

from fastmcp import Client
from openai import AsyncOpenAI


# 标签到工具名称的映射
LABEL_TO_TOOL = {
    "制度类": "regulation_search",
    "实例类": "case_retrieval",
}

# 工具名称到标签的反向映射
TOOL_TO_LABEL = {v: k for k, v in LABEL_TO_TOOL.items()}


class TestResult:
    """单次测试结果"""
    def __init__(self, question: str, true_label: str, predicted_tools: List[str], 
                 response_time: float = 0.0, raw_response: Optional[Any] = None):
        self.question = question
        self.true_label = true_label
        self.predicted_tools = predicted_tools
        self.response_time = response_time
        self.raw_response = raw_response
        
        # 计算预测标签
        self.predicted_label = self._get_predicted_label()
        self.is_correct = self.predicted_label == self.true_label
        
    def _get_predicted_label(self) -> Optional[str]:
        """根据预测的工具列表确定预测标签"""
        if not self.predicted_tools:
            return None
        # 如果多个工具被调用，取第一个
        first_tool = self.predicted_tools[0]
        return TOOL_TO_LABEL.get(first_tool)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "true_label": self.true_label,
            "predicted_tools": self.predicted_tools,
            "predicted_label": self.predicted_label,
            "is_correct": self.is_correct,
            "response_time": self.response_time,
        }


class MetricsCalculator:
    """性能指标计算器 - 包含LLM工具调用专属指标"""
    
    def __init__(self, results: List[TestResult]):
        self.results = results
        self.labels = list(LABEL_TO_TOOL.keys())
        self.all_tools = list(LABEL_TO_TOOL.values())
        
    def calculate_confusion_matrix(self) -> Dict[str, Dict[str, int]]:
        """计算混淆矩阵"""
        matrix = {label: {pred: 0 for pred in self.labels + [None]} for label in self.labels}
        
        for result in self.results:
            if result.true_label in self.labels:
                matrix[result.true_label][result.predicted_label] = \
                    matrix[result.true_label].get(result.predicted_label, 0) + 1
        
        return matrix
    
    def calculate_metrics_per_class(self) -> Dict[str, Dict[str, float]]:
        """计算每个类别的precision, recall, f1"""
        metrics = {}
        
        for label in self.labels:
            tp = sum(1 for r in self.results if r.true_label == label and r.predicted_label == label)
            fp = sum(1 for r in self.results if r.true_label != label and r.predicted_label == label)
            fn = sum(1 for r in self.results if r.true_label == label and r.predicted_label != label)
            tn = sum(1 for r in self.results if r.true_label != label and r.predicted_label != label)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            support = sum(1 for r in self.results if r.true_label == label)
            
            metrics[label] = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "support": support,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        
        return metrics
    
    def calculate_tool_call_metrics(self) -> Dict[str, Any]:
        """计算LLM工具调用专属指标"""
        total = len(self.results)
        
        # 1. 工具调用成功率 (Tool Call Success Rate)
        #    定义：模型成功调用了工具且选择正确的比例
        successful_calls = sum(1 for r in self.results if r.predicted_tools and r.is_correct)
        tool_call_success_rate = successful_calls / total if total > 0 else 0.0
        
        # 2. 无工具调用率 (No Tool Call Rate)
        #    定义：模型没有调用任何工具的比例
        no_tool_calls = sum(1 for r in self.results if not r.predicted_tools)
        no_tool_call_rate = no_tool_calls / total if total > 0 else 0.0
        
        # 3. 多工具调用率 (Multiple Tool Calls Rate)
        #    定义：模型一次调用了多个工具的比例
        multiple_calls = sum(1 for r in self.results if len(r.predicted_tools) > 1)
        multiple_tool_call_rate = multiple_calls / total if total > 0 else 0.0
        
        # 4. 工具幻觉率 (Tool Hallucination Rate)
        #    定义：模型调用了不存在的工具的比例
        hallucinated_calls = sum(1 for r in self.results 
                                if r.predicted_tools and 
                                any(tool not in self.all_tools for tool in r.predicted_tools))
        tool_hallucination_rate = hallucinated_calls / total if total > 0 else 0.0
        
        # 5. 有效工具调用率 (Valid Tool Call Rate)
        #    定义：模型至少调用了一个有效工具的比例
        valid_calls = sum(1 for r in self.results 
                         if r.predicted_tools and 
                         any(tool in self.all_tools for tool in r.predicted_tools))
        valid_tool_call_rate = valid_calls / total if total > 0 else 0.0
        
        # 6. 单工具调用准确率 (Single Tool Call Accuracy)
        #    定义：在只调用一个工具的情况下的准确率
        single_calls = [r for r in self.results if len(r.predicted_tools) == 1]
        single_call_correct = sum(1 for r in single_calls if r.is_correct)
        single_tool_call_accuracy = single_call_correct / len(single_calls) if single_calls else 0.0
        
        # 7. 工具调用分布
        tool_call_distribution = Counter()
        for result in self.results:
            for tool in result.predicted_tools:
                tool_call_distribution[tool] += 1
        
        # 8. 平均工具调用数
        avg_tools_per_query = statistics.mean([len(r.predicted_tools) for r in self.results])
        
        # 9. 响应时间分位数
        response_times = [r.response_time for r in self.results if r.response_time > 0]
        response_time_p50 = statistics.median(response_times) if response_times else 0.0
        response_time_p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else (max(response_times) if response_times else 0.0)
        response_time_p99 = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else (max(response_times) if response_times else 0.0)
        
        return {
            "tool_call_success_rate": tool_call_success_rate,
            "no_tool_call_rate": no_tool_call_rate,
            "multiple_tool_call_rate": multiple_tool_call_rate,
            "tool_hallucination_rate": tool_hallucination_rate,
            "valid_tool_call_rate": valid_tool_call_rate,
            "single_tool_call_accuracy": single_tool_call_accuracy,
            "tool_call_distribution": dict(tool_call_distribution),
            "avg_tools_per_query": avg_tools_per_query,
            "response_time_p50": response_time_p50,
            "response_time_p95": response_time_p95,
            "response_time_p99": response_time_p99,
            "total_samples": total,
            "successful_calls": successful_calls,
            "no_tool_calls": no_tool_calls,
            "multiple_calls": multiple_calls,
            "hallucinated_calls": hallucinated_calls,
            "valid_calls": valid_calls,
            "single_calls_total": len(single_calls),
            "single_calls_correct": single_call_correct,
        }
    
    def calculate_overall_metrics(self) -> Dict[str, Any]:
        """计算整体指标"""
        correct = sum(1 for r in self.results if r.is_correct)
        total = len(self.results)
        accuracy = correct / total if total > 0 else 0.0
        
        # 计算macro和weighted平均
        class_metrics = self.calculate_metrics_per_class()
        
        macro_precision = statistics.mean([m["precision"] for m in class_metrics.values()])
        macro_recall = statistics.mean([m["recall"] for m in class_metrics.values()])
        macro_f1 = statistics.mean([m["f1_score"] for m in class_metrics.values()])
        
        # 加权平均
        total_support = sum(m["support"] for m in class_metrics.values())
        weighted_precision = sum(m["precision"] * m["support"] for m in class_metrics.values()) / total_support if total_support > 0 else 0.0
        weighted_recall = sum(m["recall"] * m["support"] for m in class_metrics.values()) / total_support if total_support > 0 else 0.0
        weighted_f1 = sum(m["f1_score"] * m["support"] for m in class_metrics.values()) / total_support if total_support > 0 else 0.0
        
        # 统计无预测的情况
        no_prediction = sum(1 for r in self.results if r.predicted_label is None)
        
        # 响应时间统计
        response_times = [r.response_time for r in self.results if r.response_time > 0]
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        min_response_time = min(response_times) if response_times else 0.0
        max_response_time = max(response_times) if response_times else 0.0
        
        return {
            "accuracy": accuracy,
            "correct_count": correct,
            "total_count": total,
            "no_prediction_count": no_prediction,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
            "weighted_precision": weighted_precision,
            "weighted_recall": weighted_recall,
            "weighted_f1": weighted_f1,
            "avg_response_time": avg_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
        }


async def build_openai_tools_from_mcp(mcp_url: str) -> List[Dict[str, Any]]:
    """从 MCP 客户端动态获取工具，并转换为 OpenAI Tools 结构"""
    async with Client(mcp_url) as mcp:
        await mcp.ping()
        tools = await mcp.list_tools()

    openai_tools: List[Dict[str, Any]] = []
    for tool in tools:
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
        )
    return openai_tools


async def run_single_query(
    aclient: AsyncOpenAI,
    model: str,
    question: str,
    temperature: float,
    max_tokens: int,
    tools: List[Dict[str, Any]],
) -> Tuple[List[str], float, Any]:
    """执行单个查询，返回工具名称列表、响应时间和原始响应"""
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = (
        "你是一个专业的审计与知识检索助手。"
        f"\n现在的时间是上海时间: {now}"
        "\n\n你必须从以下两个工具中选择一个（必须二选一）："
        "\n\n【工具选择规则 - 核心判断逻辑】"
        "\n\n**第一步：判断查询的核心意图**"
        "\n\n1️⃣ **如果查询的是「规则、要求、标准、定义」等规范性内容** → regulation_search"
        "\n   关键词：\"如何\"、\"怎么\"、\"什么要求\"、\"什么标准\"、\"什么流程\"、"
        "\n           \"有哪些类型\"、\"有哪些等级\"、\"覆盖范围\"、\"管理周期\"、\"职责\"、\"定义\""
        "\n   示例："
        "\n   ✓ \"门禁管理要求是什么\" - 询问管理要求"
        "\n   ✓ \"有哪些应急预案\" - 询问预案类型/覆盖范围（不是要具体文档）"
        "\n   ✓ \"是否有应急物资库\" - 询问是否有这种管理机制"
        "\n   ✓ \"应急组织架构图是什么，各角色的职责是哪些\" - 询问职责分工"
        "\n   ✓ \"SH16巡检覆盖范围，巡检频次\" - 询问规定的范围和频次"
        "\n   ✓ \"下单的准备工作有哪些\" - 询问工作流程要求"
        "\n   ✓ \"请提供供应商相关管理规定文档\" - 明确要管理规定"
        "\n\n2️⃣ **如果查询的是「具体文档、记录、设备、数据」等实例内容** → case_retrieval"
        "\n   关键词：\"计划\"、\"记录\"、\"清单\"、\"报告\"、\"测试\"、\"证书\"、\"MOP\"、"
        "\n           \"路线\"、\"点位\"、\"权限列表\"、\"请提供XX记录/清单/表格\"、\"看一下\"、具体年份/设备+名词"
        "\n   示例："
        "\n   ✓ \"2025年培训计划\" - 要具体年份的计划文档"
        "\n   ✓ \"是否有培训记录\" - 要具体的记录"
        "\n   ✓ \"请提供MOP清单\" - 要具体的操作手册清单"
        "\n   ✓ \"浦江运维组织架构图\" - 要具体机构的架构图"
        "\n   ✓ \"SH16巡检路线\" - 要具体的路线（不是覆盖范围）"
        "\n   ✓ \"蓄电池放电测试的频率\" - 要维护计划中的具体参数"
        "\n   ✓ \"机房安全巡逻点位\" - 要具体的点位表"
        "\n   ✓ \"BNPP机柜门禁权限\" - 要具体的权限列表"
        "\n\n\n【详细判断规则】"
        "\n\n一、**regulation_search (制度类)** - 查询规范性内容"
        "\n   适用场景："
        "\n   • 询问「如何做」、「怎么管理」、「什么要求」、「什么标准」"
        "\n   • 询问「有哪些类型/等级/分类」（询问分类体系，不是要具体文档列表）"
        "\n   • 询问「是否有XX管理机制/规定」（询问是否存在这种规定）"
        "\n   • 询问「覆盖范围」、「职责」、\"审批流程\"等规定性内容"
        "\n   • 明确要求「管理规定」、「管理制度」文档"
        "\n   • 询问角色职责、审批矩阵、分级分类标准等"
        "\n\n二、**case_retrieval (实例类)** - 查询具体实例"
        "\n   适用场景（满足以下任一条件）："
        "\n   • 包含具体时间（年/月）+ 名词（如\"2025年XX计划\"、\"最近1周XX\"）"
        "\n   • 包含具体地点/设备 + 具体名词（如\"XX测试频率\"、\"SH16XX路线\"）"
        "\n   • 查询「XX记录」、「XX清单」、「XX报告」、\"XX证书\"、\"XX表格/工作表\""
        "\n   • 查询「MOP」、「操作手册」等具体操作文档"
        "\n   • 查询「XX计划」（维护计划、培训计划等）"
        "\n   • 使用「请提供」+ 非管理规定的名词"
        "\n   • 询问「是否有XX记录/清单」（要具体的记录，不是询问机制）"
        "\n   • 查询具体参数/配置/点位（如\"XX的频率\"、\"XX权限\"、\"XX点位\"）"
        "\n\n\n【关键区分点】"
        "\n\n🔍 **\"是否有...\"的判断：**"
        "\n   • \"是否有应急物资库\" → regulation_search（询问是否有这种管理机制）"
        "\n   • \"是否有培训记录\" → case_retrieval（询问是否存在具体的记录文档）"
        "\n\n🔍 **\"有哪些...\"的判断：**"
        "\n   • \"有哪些应急预案\" → regulation_search（询问预案类型/覆盖范围）"
        "\n   • \"有哪些维护记录\" → case_retrieval（要具体的记录列表）"
        "\n\n🔍 **参数/配置的判断：**"
        "\n   • \"蓄电池放电测试的频率\" → case_retrieval（查询具体维护参数）"
        "\n   • \"列头柜的安全管理阈值是什么\" → regulation_search（查询标准/规定）"
        "\n\n🔍 **权限/点位的判断：**"
        "\n   • \"BNPP机柜门禁权限\" → case_retrieval（查询具体权限列表）"
        "\n   • \"临时拜访人员的门禁权限是如何管理的\" → regulation_search（查询管理流程）"
        "\n   • \"机房安全巡逻点位\" → case_retrieval（查询具体点位表）"
        "\n\n🔍 **包含设备编号的判断：**"
        "\n   • \"SH16巡检覆盖范围\" → regulation_search（询问规定的范围）"
        "\n   • \"SH16巡检路线\" → case_retrieval（要具体的路线图/路线表）"
        "\n\n🔍 **架构图的判断：**"
        "\n   • \"应急组织架构图是什么，各角色的职责是哪些\" → regulation_search（重点在职责）"
        "\n   • \"浦江运维组织架构图\" → case_retrieval（要具体机构的架构图文档）"
        "\n\n\n【决策流程】"
        "\n1. 找出查询的核心意图关键词"
        "\n2. 判断是询问「规则/要求/标准」还是「具体文档/数据」"
        "\n3. 当不确定时，看是否包含：具体时间/地点/设备编号 + 具体名词（记录/清单/报告/计划/点位/权限）→ case_retrieval"
        "\n4. 否则 → regulation_search"
        "\n\n请仔细分析用户查询，必须选择且只能选择一个工具。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    start_time = asyncio.get_event_loop().time()
    try:
        response = await aclient.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=max_tokens,
        )
        end_time = asyncio.get_event_loop().time()
        response_time = end_time - start_time

        message = response.choices[0].message
        called_tool_names: List[str] = []
        if getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                if getattr(call, "function", None) and getattr(call.function, "name", None):
                    called_tool_names.append(call.function.name)

        return called_tool_names, response_time, response
    except Exception as e:
        end_time = asyncio.get_event_loop().time()
        response_time = end_time - start_time
        print(f"Error processing question '{question}': {e}")
        return [], response_time, None


async def run_batch_test(
    aclient: AsyncOpenAI,
    model: str,
    test_cases: List[Tuple[str, str]],  # [(question, true_label), ...]
    temperature: float,
    max_tokens: int,
    tools: List[Dict[str, Any]],
    batch_size: int = 5,
) -> List[TestResult]:
    """批量并行测试"""
    results = []
    
    # 分批处理以避免过载
    for i in range(0, len(test_cases), batch_size):
        batch = test_cases[i:i + batch_size]
        tasks = []
        
        for question, true_label in batch:
            task = run_single_query(
                aclient, model, question, temperature, max_tokens, tools
            )
            tasks.append((question, true_label, task))
        
        # 并行执行当前批次
        for question, true_label, task in tasks:
            predicted_tools, response_time, raw_response = await task
            result = TestResult(
                question=question,
                true_label=true_label,
                predicted_tools=predicted_tools,
                response_time=response_time,
                raw_response=raw_response,
            )
            results.append(result)
        
        print(f"已完成 {min(i + batch_size, len(test_cases))}/{len(test_cases)} 个测试")
    
    return results


def load_test_data(csv_path: str) -> List[Tuple[str, str]]:
    """从CSV文件加载测试数据"""
    test_cases = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get('Q', '').strip()
            label = row.get('标签', '').strip()
            
            # 跳过空行或无效数据
            if question and label and label in LABEL_TO_TOOL:
                test_cases.append((question, label))
    
    return test_cases


def print_detailed_report(all_round_results: List[List[TestResult]], args):
    """打印详细的测试报告"""
    # 收集所有输出内容
    report_lines = []
    
    def print_and_save(text=""):
        """同时打印到控制台和保存到列表"""
        print(text)
        report_lines.append(text)
    
    print_and_save("\n" + "=" * 80)
    print_and_save("测试报告 - 审计Agent工具分类准确率评估")
    print_and_save("=" * 80)
    print_and_save(f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_and_save(f"模型: {args.model}")
    print_and_save(f"温度: {args.temperature}")
    print_and_save(f"测试轮数: {args.rounds}")
    print_and_save(f"每轮测试样本数: {len(all_round_results[0])}")
    
    # 计算每轮的指标
    print_and_save("\n" + "-" * 80)
    print_and_save("各轮测试结果汇总")
    print_and_save("-" * 80)
    
    round_accuracies = []
    for round_idx, results in enumerate(all_round_results, 1):
        calculator = MetricsCalculator(results)
        overall = calculator.calculate_overall_metrics()
        round_accuracies.append(overall["accuracy"])
        
        print_and_save(f"\n第 {round_idx} 轮:")
        print_and_save(f"  准确率: {overall['accuracy']:.2%} ({overall['correct_count']}/{overall['total_count']})")
        print_and_save(f"  无预测: {overall['no_prediction_count']} 个")
        print_and_save(f"  平均响应时间: {overall['avg_response_time']:.3f}秒")
    
    # 跨轮次稳定性分析
    if args.rounds > 1:
        print_and_save("\n" + "-" * 80)
        print_and_save("跨轮次稳定性分析")
        print_and_save("-" * 80)
        print_and_save(f"平均准确率: {statistics.mean(round_accuracies):.2%}")
        print_and_save(f"准确率标准差: {statistics.stdev(round_accuracies) if len(round_accuracies) > 1 else 0:.4f}")
        print_and_save(f"准确率范围: [{min(round_accuracies):.2%}, {max(round_accuracies):.2%}]")
    
    # 使用最后一轮或所有轮次合并的结果进行详细分析
    if args.aggregate_rounds:
        # 合并所有轮次的结果
        all_results = [r for round_results in all_round_results for r in round_results]
        print_and_save("\n使用所有轮次的合并数据进行详细分析")
    else:
        # 使用最后一轮
        all_results = all_round_results[-1]
        print_and_save("\n使用最后一轮数据进行详细分析")
    
    calculator = MetricsCalculator(all_results)
    
    # 整体指标
    print_and_save("\n" + "-" * 80)
    print_and_save("整体性能指标")
    print_and_save("-" * 80)
    overall = calculator.calculate_overall_metrics()
    print_and_save(f"准确率 (Accuracy): {overall['accuracy']:.2%}")
    print_and_save(f"正确预测: {overall['correct_count']}/{overall['total_count']}")
    print_and_save(f"无预测样本: {overall['no_prediction_count']}")
    print_and_save(f"\nMacro 平均:")
    print_and_save(f"  Precision: {overall['macro_precision']:.2%}")
    print_and_save(f"  Recall: {overall['macro_recall']:.2%}")
    print_and_save(f"  F1-Score: {overall['macro_f1']:.2%}")
    print_and_save(f"\nWeighted 平均:")
    print_and_save(f"  Precision: {overall['weighted_precision']:.2%}")
    print_and_save(f"  Recall: {overall['weighted_recall']:.2%}")
    print_and_save(f"  F1-Score: {overall['weighted_f1']:.2%}")
    
    # LLM工具调用专属指标
    print_and_save("\n" + "-" * 80)
    print_and_save("LLM工具调用专属指标")
    print_and_save("-" * 80)
    tool_metrics = calculator.calculate_tool_call_metrics()
    print_and_save(f"\n工具调用行为分析:")
    print_and_save(f"  工具调用成功率: {tool_metrics['tool_call_success_rate']:.2%} ({tool_metrics['successful_calls']}/{tool_metrics['total_samples']})")
    print_and_save(f"  无工具调用率: {tool_metrics['no_tool_call_rate']:.2%} ({tool_metrics['no_tool_calls']}/{tool_metrics['total_samples']})")
    print_and_save(f"  多工具调用率: {tool_metrics['multiple_tool_call_rate']:.2%} ({tool_metrics['multiple_calls']}/{tool_metrics['total_samples']})")
    print_and_save(f"  工具幻觉率: {tool_metrics['tool_hallucination_rate']:.2%} ({tool_metrics['hallucinated_calls']}/{tool_metrics['total_samples']})")
    print_and_save(f"  有效工具调用率: {tool_metrics['valid_tool_call_rate']:.2%} ({tool_metrics['valid_calls']}/{tool_metrics['total_samples']})")
    
    print_and_save(f"\n工具调用质量分析:")
    print_and_save(f"  单工具调用准确率: {tool_metrics['single_tool_call_accuracy']:.2%} ({tool_metrics['single_calls_correct']}/{tool_metrics['single_calls_total']})")
    print_and_save(f"  平均工具调用数/查询: {tool_metrics['avg_tools_per_query']:.2f}")
    
    print_and_save(f"\n工具调用分布:")
    for tool, count in sorted(tool_metrics['tool_call_distribution'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / tool_metrics['total_samples'] * 100
        print_and_save(f"  {tool}: {count} 次 ({percentage:.1f}%)")
    
    print_and_save(f"\n响应时间分析:")
    print_and_save(f"  平均响应时间: {overall['avg_response_time']:.3f}秒")
    print_and_save(f"  最小响应时间: {overall['min_response_time']:.3f}秒")
    print_and_save(f"  最大响应时间: {overall['max_response_time']:.3f}秒")
    print_and_save(f"  P50 (中位数): {tool_metrics['response_time_p50']:.3f}秒")
    print_and_save(f"  P95: {tool_metrics['response_time_p95']:.3f}秒")
    print_and_save(f"  P99: {tool_metrics['response_time_p99']:.3f}秒")
    
    # 每个类别的详细指标
    print_and_save("\n" + "-" * 80)
    print_and_save("各类别详细指标")
    print_and_save("-" * 80)
    class_metrics = calculator.calculate_metrics_per_class()
    
    for label, metrics in class_metrics.items():
        print_and_save(f"\n【{label}】 (对应工具: {LABEL_TO_TOOL[label]})")
        print_and_save(f"  样本数 (Support): {metrics['support']}")
        print_and_save(f"  Precision: {metrics['precision']:.2%}")
        print_and_save(f"  Recall: {metrics['recall']:.2%}")
        print_and_save(f"  F1-Score: {metrics['f1_score']:.2%}")
        print_and_save(f"  混淆矩阵统计: TP={metrics['tp']}, FP={metrics['fp']}, FN={metrics['fn']}, TN={metrics['tn']}")
    
    # 混淆矩阵
    print_and_save("\n" + "-" * 80)
    print_and_save("混淆矩阵")
    print_and_save("-" * 80)
    confusion = calculator.calculate_confusion_matrix()
    
    # 打印表头
    pred_labels = list(LABEL_TO_TOOL.keys()) + ["无预测"]
    header = "真实\\预测".ljust(12) + "".join([label.ljust(12) for label in pred_labels])
    print_and_save(header)
    print_and_save("-" * len(header))
    
    for true_label in LABEL_TO_TOOL.keys():
        row = true_label.ljust(12)
        for pred_label in LABEL_TO_TOOL.keys():
            count = confusion[true_label].get(pred_label, 0)
            row += str(count).ljust(12)
        # 添加无预测列
        count = confusion[true_label].get(None, 0)
        row += str(count).ljust(12)
        print_and_save(row)
    
    # 错误案例分析
    print_and_save("\n" + "-" * 80)
    print_and_save(f"错误案例分析 (全部 {len([r for r in all_results if not r.is_correct])} 个)")
    print_and_save("-" * 80)
    
    errors = [r for r in all_results if not r.is_correct]
    if errors:
        for idx, error in enumerate(errors, 1):
            print_and_save(f"\n错误 {idx}:")
            print_and_save(f"  问题: {error.question}")
            print_and_save(f"  真实标签: {error.true_label}")
            print_and_save(f"  预测工具: {error.predicted_tools if error.predicted_tools else '(无)'}")
            print_and_save(f"  预测标签: {error.predicted_label if error.predicted_label else '(无)'}")
    else:
        print_and_save("\n🎉 没有错误案例！")
    
    print_and_save("\n" + "=" * 80)
    
    # 保存报告到txt文件
    return report_lines


def save_results_to_json(all_round_results: List[List[TestResult]], output_path: str, args):
    """保存详细结果到JSON文件"""
    output_data = {
        "meta": {
            "test_time": datetime.now().isoformat(),
            "model": args.model,
            "temperature": args.temperature,
            "rounds": args.rounds,
            "samples_per_round": len(all_round_results[0]),
        },
        "rounds": []
    }
    
    for round_idx, results in enumerate(all_round_results, 1):
        calculator = MetricsCalculator(results)
        round_data = {
            "round": round_idx,
            "overall_metrics": calculator.calculate_overall_metrics(),
            "tool_call_metrics": calculator.calculate_tool_call_metrics(),
            "class_metrics": calculator.calculate_metrics_per_class(),
            "confusion_matrix": calculator.calculate_confusion_matrix(),
            "results": [r.to_dict() for r in results],
        }
        output_data["rounds"].append(round_data)
    
    # 如果多轮，计算汇总统计
    if args.rounds > 1:
        accuracies = [r["overall_metrics"]["accuracy"] for r in output_data["rounds"]]
        output_data["aggregated_stats"] = {
            "mean_accuracy": statistics.mean(accuracies),
            "std_accuracy": statistics.stdev(accuracies) if len(accuracies) > 1 else 0,
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    script_dir = Path(__file__).parent
    mcp_path = str((script_dir / "03_exp" / "audit_mcp.py").absolute())
    csv_path = str((script_dir / "审计QA——人工版-工作表1.csv").absolute())
    
    parser = argparse.ArgumentParser(
        description="审计Agent工具分类准确率测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # 数据和MCP配置
    parser.add_argument("--csv-path", type=str, default=csv_path, 
                       help="测试数据CSV文件路径")
    parser.add_argument("--mcp-url", type=str, default=os.getenv("MCP_URL", mcp_path),
                       help="MCP服务URL或脚本路径")
    
    # 模型配置
    parser.add_argument("--provider", type=str, 
                       choices=["deepseek", "zhipu", "custom"],
                       default="deepseek",
                       help="API提供商：deepseek, zhipu, 或 custom（自定义）")
    parser.add_argument("--api-key", type=str, 
                       default=None,
                       help="API密钥（如果不指定，将使用provider的默认值）")
    parser.add_argument("--base-url", type=str, 
                       default=None,
                       help="API基础URL（如果不指定，将使用provider的默认值）")
    parser.add_argument("--model", type=str, 
                       default=None,
                       help="使用的模型名称（如果不指定，将使用provider的默认值）")
    parser.add_argument("--temperature", type=float, default=0.3,
                       help="模型温度参数")
    parser.add_argument("--max-tokens", type=int, default=1024,
                       help="最大生成token数")
    parser.add_argument("--timeout", type=int, default=60,
                       help="API请求超时时间（秒）")
    
    # 测试配置
    parser.add_argument("--rounds", type=int, default=1,
                       help="测试轮数，用于评估稳定性")
    parser.add_argument("--batch-size", type=int, default=25,
                       help="并行批处理大小")
    parser.add_argument("--aggregate-rounds", action="store_true",
                       help="合并所有轮次的结果进行分析（而不是只用最后一轮）")
    
    # 输出配置
    parser.add_argument("--output-json", type=str, 
                       default=str(script_dir / "test_results.json"),
                       help="输出JSON结果文件路径")
    parser.add_argument("--no-save", action="store_true",
                       help="不保存JSON结果文件")
    
    return parser.parse_args()


async def amain():
    """主异步函数"""
    args = parse_args()
    
    # 根据provider设置默认值
    provider_configs = {
        "deepseek": {
            "api_key": "av7b4VoBryCMu3hZ9",
            "base_url": "https://deepseek.gds-services.com/v1",
            "model": "deepseek-ai/DeepSeek-V3"
        },
        "zhipu": {
            "api_key": "29ada920c778a1c8341267040b0e31f0.WYoDydHDDDbmsqAx",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash"
        }
    }
    
    # 应用默认配置
    if args.provider in provider_configs:
        config = provider_configs[args.provider]
        if not args.api_key:
            args.api_key = config["api_key"]
        if not args.base_url:
            args.base_url = config["base_url"]
        if not args.model:
            args.model = config["model"]
    else:
        # custom模式，必须手动指定所有参数
        if not args.api_key or not args.base_url or not args.model:
            raise SystemExit("错误: 使用custom模式时，必须指定--api-key、--base-url和--model参数")
    
    print("=" * 80)
    print("审计Agent工具分类准确率测试")
    print("=" * 80)
    print(f"\nAPI提供商: {args.provider}")
    print(f"模型: {args.model}")
    print(f"\n加载测试数据: {args.csv_path}")
    
    # 加载测试数据
    test_cases = load_test_data(args.csv_path)
    
    if not test_cases:
        raise SystemExit("错误: 未能从CSV文件中加载有效的测试数据")
    
    print(f"成功加载 {len(test_cases)} 个测试样本")
    
    # 统计标签分布
    label_counts = Counter([label for _, label in test_cases])
    print(f"标签分布: {dict(label_counts)}")
    
    # 初始化OpenAI客户端
    client_kwargs = {
        "api_key": args.api_key or "",
        "base_url": args.base_url,
        "timeout": args.timeout,
    }
    aclient = AsyncOpenAI(**client_kwargs)
    
    # 从MCP获取工具列表
    print(f"\n连接MCP服务: {args.mcp_url}")
    tools = await build_openai_tools_from_mcp(args.mcp_url)
    print(f"成功加载 {len(tools)} 个工具: {[t['function']['name'] for t in tools]}")
    
    # 执行多轮测试
    all_round_results = []
    
    for round_idx in range(1, args.rounds + 1):
        print(f"\n{'=' * 80}")
        print(f"开始第 {round_idx}/{args.rounds} 轮测试")
        print(f"{'=' * 80}")
        
        results = await run_batch_test(
            aclient=aclient,
            model=args.model,
            test_cases=test_cases,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            tools=tools,
            batch_size=args.batch_size,
        )
        
        all_round_results.append(results)
        print(f"第 {round_idx} 轮测试完成")
    
    # 打印详细报告并获取报告内容
    report_lines = print_detailed_report(all_round_results, args)
    
    # 保存结果
    if not args.no_save:
        save_results_to_json(all_round_results, args.output_json, args)
        
        # 保存文本报告
        txt_output = args.output_json.replace('.json', '.txt')
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        print(f"文本报告已保存到: {txt_output}")
    
    print("\n测试完成!")


def main():
    """主函数入口"""
    asyncio.run(amain())


if __name__ == "__main__":
    main()
