# 审计Agent工具分类准确率测试脚本

## 概述

`query_categorization_metrics.py` 是一个完整的测试脚本，用于评估大模型（DeepSeek-V3）在审计Agent场景下选择正确MCP工具的性能表现。

## 功能特性

### 核心功能
- ✅ **自动化测试**: 从CSV文件加载测试数据，自动批量测试
- ✅ **并行执行**: 支持批量并行调用API，提高测试效率
- ✅ **多轮测试**: 支持多轮测试以评估模型的稳定性和一致性
- ✅ **详细指标**: 计算准确率、精确率、召回率、F1分数等多种性能指标
- ✅ **混淆矩阵**: 生成详细的混淆矩阵分析
- ✅ **错误分析**: 自动识别并展示错误预测案例
- ✅ **结果持久化**: 将测试结果保存为JSON格式以便后续分析

### 性能指标

脚本会计算以下指标：

#### 整体指标
- **Accuracy (准确率)**: 模型预测正确的样本比例
- **Macro Average**: 各类别指标的简单平均
  - Precision (精确率)
  - Recall (召回率)
  - F1-Score
- **Weighted Average**: 按样本数加权的平均值
  - Precision (精确率)
  - Recall (召回率)
  - F1-Score

#### 每个类别的指标
- **Precision (精确率)**: TP / (TP + FP)
- **Recall (召回率)**: TP / (TP + FN)
- **F1-Score**: 2 * Precision * Recall / (Precision + Recall)
- **Support (样本数)**: 该类别的测试样本总数
- **混淆矩阵元素**: TP, FP, FN, TN

#### LLM工具调用专属指标 ⭐ 新增
- **Tool Call Success Rate (工具调用成功率)**: 模型成功调用工具且选择正确的比例
- **No Tool Call Rate (无工具调用率)**: 模型没有调用任何工具的比例
- **Multiple Tool Calls Rate (多工具调用率)**: 模型一次调用多个工具的比例
- **Tool Hallucination Rate (工具幻觉率)**: 模型调用不存在工具的比例
- **Valid Tool Call Rate (有效工具调用率)**: 模型至少调用一个有效工具的比例
- **Single Tool Call Accuracy (单工具调用准确率)**: 只调用一个工具时的准确率
- **Tool Call Distribution (工具调用分布)**: 各工具被调用的次数统计
- **Average Tools Per Query (平均工具调用数)**: 每个查询平均调用的工具数

#### 响应时间统计
- 平均响应时间
- 最小/最大响应时间
- P50 (中位数)
- P95 响应时间
- P99 响应时间

#### 跨轮次稳定性分析
- 准确率标准差
- 准确率范围（最小值、最大值）

## 工具映射

脚本会将CSV中的"标签"列映射到对应的MCP工具：

| CSV标签 | MCP工具名称 | 说明 |
|---------|------------|------|
| 制度类 | `regulation_search` | 搜索规章制度相关文档 |
| 实例类 | `case_retrieval` | 搜索实例类文档或非制度类文档 |

## 使用方法

### 基本用法

最简单的使用方式（使用默认参数）：

```bash
python query_categorization_metrics.py
```

### 指定测试轮数和并行批次大小

```bash
python query_categorization_metrics.py --rounds 3 --batch-size 5
```

### 完整参数示例

```bash
python query_categorization_metrics.py \
    --csv-path "审计QA——人工版-工作表1.csv" \
    --model "deepseek-ai/DeepSeek-V3" \
    --temperature 0.3 \
    --rounds 3 \
    --batch-size 5 \
    --output-json "test_results.json"
```

### 命令行参数说明

#### 数据和MCP配置
- `--csv-path`: 测试数据CSV文件路径（默认: `审计QA——人工版-工作表1.csv`）
- `--mcp-url`: MCP服务URL或脚本路径（默认: `03_exp/audit_mcp.py`）

#### 模型配置
- `--api-key`: OpenAI API密钥（默认从环境变量读取）
- `--base-url`: OpenAI API基础URL（默认: `https://deepseek.gds-services.com/v1`）
- `--model`: 使用的模型名称（默认: `deepseek-ai/DeepSeek-V3`）
- `--temperature`: 模型温度参数（默认: `0.3`）
- `--max-tokens`: 最大生成token数（默认: `1024`）
- `--timeout`: API请求超时时间（秒）（默认: `60`）

#### 测试配置
- `--rounds`: 测试轮数，用于评估稳定性（默认: `1`）
- `--batch-size`: 并行批处理大小（默认: `5`）
- `--aggregate-rounds`: 合并所有轮次的结果进行分析（默认: 只使用最后一轮）

#### 输出配置
- `--output-json`: 输出JSON结果文件路径（默认: `test_results.json`）
- `--no-save`: 不保存JSON结果文件

## 测试数据格式

CSV文件需要包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| Q | 用户输入的问题 | "请提供人员设备进出管理的相关制度" |
| 标签 | 正确的工具分类 | "制度类" 或 "实例类" |

其他列（如：编号、文档、A、路径等）会被忽略。

示例CSV格式：
```csv
编号,文档,Q,A,标签,路径
1,数据中心人员设备进出管理规定,请提供人员设备进出管理的相关制度,,制度类,
2,数据中心人员设备进出管理规定,人员设备进出管理的最新修改日期和版本,,制度类,
3,,浦江25年的培训计划是什么,,实例类,
```

## 可视化界面 🎨 新增

我们提供了一个现代化的Web可视化界面 (`visualization.html`) 来展示评测结果：

### 功能特性
- 📊 **交互式图表**: 使用Chart.js展示各种性能指标
- 🎯 **核心指标卡片**: 以卡片形式展示关键指标
- 📈 **多维度分析**: 包括混淆矩阵、工具分布、响应时间等
- 🔄 **轮次切换**: 支持查看多轮测试的不同结果
- 📱 **响应式设计**: 适配不同屏幕尺寸

### 使用方法

1. **方法一：直接打开HTML文件**
```bash
# 在浏览器中打开
start visualization.html  # Windows
open visualization.html   # Mac
xdg-open visualization.html  # Linux
```

2. **方法二：使用本地服务器**
```bash
# Python 3
python -m http.server 8000

# 然后在浏览器访问
# http://localhost:8000/visualization.html
```

3. **加载数据**
- 点击"选择JSON文件"按钮，选择生成的 `test_results.json`
- 或点击"加载示例数据"按钮自动加载同目录下的 `test_results.json`

### 可视化内容

界面包含以下可视化组件：

1. **元信息卡片**
   - 测试时间、模型、温度、轮数、样本数

2. **核心指标卡片**
   - 准确率、Macro F1、Weighted F1、平均响应时间

3. **LLM工具调用专属指标卡片**
   - 工具调用成功率、无工具调用率、多工具调用率
   - 工具幻觉率、单工具调用准确率、平均工具调用数

4. **可视化图表**
   - 📊 整体性能指标对比（柱状图）
   - 🎯 混淆矩阵（柱状图）
   - 🍩 工具调用分布（饼图）
   - ⏱️ 响应时间统计（柱状图）
   - 🎭 各类别性能对比（雷达图）
   - 📈 工具调用行为统计（柱状图）

5. **错误案例表格**
   - 显示前10个错误案例的详细信息

## 输出示例

### 控制台输出

脚本会在控制台输出详细的测试报告，包括：

```
================================================================================
测试报告 - 审计Agent工具分类准确率评估
================================================================================

测试时间: 2025-11-18 17:19:24
模型: deepseek-ai/DeepSeek-V3
温度: 0.3
测试轮数: 3
每轮测试样本数: 25

--------------------------------------------------------------------------------
各轮测试结果汇总
--------------------------------------------------------------------------------

第 1 轮:
  准确率: 92.00% (23/25)
  无预测: 0 个
  平均响应时间: 1.234秒

第 2 轮:
  准确率: 88.00% (22/25)
  无预测: 0 个
  平均响应时间: 1.187秒

第 3 轮:
  准确率: 96.00% (24/25)
  无预测: 0 个
  平均响应时间: 1.298秒

--------------------------------------------------------------------------------
跨轮次稳定性分析
--------------------------------------------------------------------------------
平均准确率: 92.00%
准确率标准差: 0.0327
准确率范围: [88.00%, 96.00%]

--------------------------------------------------------------------------------
整体性能指标
--------------------------------------------------------------------------------
准确率 (Accuracy): 96.00%
正确预测: 24/25
无预测样本: 0

Macro 平均:
  Precision: 95.50%
  Recall: 96.00%
  F1-Score: 95.75%

Weighted 平均:
  Precision: 96.20%
  Recall: 96.00%
  F1-Score: 96.10%

--------------------------------------------------------------------------------
各类别详细指标
--------------------------------------------------------------------------------

【制度类】 (对应工具: regulation_search)
  样本数 (Support): 22
  Precision: 95.65%
  Recall: 100.00%
  F1-Score: 97.78%
  混淆矩阵统计: TP=22, FP=1, FN=0, TN=2

【实例类】 (对应工具: case_retrieval)
  样本数 (Support): 3
  Precision: 100.00%
  Recall: 66.67%
  F1-Score: 80.00%
  混淆矩阵统计: TP=2, FP=0, FN=1, TN=22

--------------------------------------------------------------------------------
混淆矩阵
--------------------------------------------------------------------------------
真实\预测       制度类         实例类         无预测         
------------------------------------------------
制度类         22          0           0           
实例类         1           2           0           

--------------------------------------------------------------------------------
错误案例分析 (最多显示10个)
--------------------------------------------------------------------------------

错误 1:
  问题: 浦江25年的培训计划是什么
  真实标签: 实例类
  预测工具: ['regulation_search']
  预测标签: 制度类

================================================================================
```

### JSON输出文件

测试结果会保存为JSON格式（默认文件名：`test_results.json`），包含：

```json
{
  "meta": {
    "test_time": "2025-11-18T17:19:24.887009",
    "model": "deepseek-ai/DeepSeek-V3",
    "temperature": 0.3,
    "rounds": 3,
    "samples_per_round": 25
  },
  "rounds": [
    {
      "round": 1,
      "overall_metrics": {
        "accuracy": 0.96,
        "correct_count": 24,
        "total_count": 25,
        "no_prediction_count": 0,
        "macro_precision": 0.955,
        "macro_recall": 0.96,
        "macro_f1": 0.9575,
        "weighted_precision": 0.962,
        "weighted_recall": 0.96,
        "weighted_f1": 0.961,
        "avg_response_time": 1.234
      },
      "class_metrics": {
        "制度类": {
          "precision": 0.9565,
          "recall": 1.0,
          "f1_score": 0.9778,
          "support": 22,
          "tp": 22,
          "fp": 1,
          "fn": 0,
          "tn": 2
        },
        "实例类": {
          "precision": 1.0,
          "recall": 0.6667,
          "f1_score": 0.8,
          "support": 3,
          "tp": 2,
          "fp": 0,
          "fn": 1,
          "tn": 22
        }
      },
      "confusion_matrix": {
        "制度类": {"制度类": 22, "实例类": 0, "null": 0},
        "实例类": {"制度类": 1, "实例类": 2, "null": 0}
      },
      "results": [
        {
          "question": "请提供人员设备进出管理的相关制度",
          "true_label": "制度类",
          "predicted_tools": ["regulation_search"],
          "predicted_label": "制度类",
          "is_correct": true,
          "response_time": 1.234
        }
        // ... 更多结果
      ]
    }
    // ... 更多轮次
  ],
  "aggregated_stats": {
    "mean_accuracy": 0.92,
    "std_accuracy": 0.0327,
    "min_accuracy": 0.88,
    "max_accuracy": 0.96
  }
}
```

## 高级用法

### 多轮测试评估稳定性

运行3轮测试以评估模型的稳定性：

```bash
python query_categorization_metrics.py --rounds 3
```

脚本会：
1. 对每轮测试计算独立的指标
2. 计算跨轮次的平均准确率和标准差
3. 显示准确率的范围（最小值和最大值）

### 调整温度参数

测试不同温度参数对准确率的影响：

```bash
# 较低温度（更确定性）
python query_categorization_metrics.py --temperature 0.1 --rounds 3

# 较高温度（更随机性）
python query_categorization_metrics.py --temperature 0.7 --rounds 3
```

### 优化并行性能

根据API限制和网络条件调整批处理大小：

```bash
# 较小批次（更保守，适合不稳定网络）
python query_categorization_metrics.py --batch-size 3

# 较大批次（更激进，需要稳定网络和足够的API配额）
python query_categorization_metrics.py --batch-size 10
```

### 使用不同的模型

```bash
# 使用其他兼容OpenAI API的模型
python query_categorization_metrics.py \
    --model "gpt-4" \
    --base-url "https://api.openai.com/v1" \
    --api-key "your-api-key"
```

## 故障排除

### 常见问题

#### 1. 连接错误 (Connection error)

**症状**: 所有请求都显示 "Connection error"

**可能原因**:
- API密钥无效或过期
- API基础URL配置错误
- 网络连接问题
- API服务不可用

**解决方法**:
```bash
# 检查API配置
python query_categorization_metrics.py \
    --api-key "your-valid-key" \
    --base-url "https://correct-url.com/v1"

# 增加超时时间
python query_categorization_metrics.py --timeout 120
```

#### 2. 无预测样本过多

**症状**: 大量样本显示 "无预测"

**可能原因**:
- 模型未能理解工具的用途
- 工具描述不够清晰
- 系统提示词不够明确

**解决方法**:
- 检查 `03_exp/audit_mcp.py` 中的工具描述
- 优化工具的 `description` 字段
- 调整系统提示词

#### 3. CSV加载失败

**症状**: "未能从CSV文件中加载有效的测试数据"

**可能原因**:
- CSV文件格式不正确
- 缺少必需的列（Q、标签）
- 编码问题

**解决方法**:
```bash
# 确认CSV文件存在且格式正确
# 检查文件编码是否为UTF-8
# 确保CSV包含"Q"和"标签"列
```

#### 4. MCP连接失败

**症状**: "连接MCP服务失败"

**可能原因**:
- MCP脚本路径不正确
- MCP依赖未安装

**解决方法**:
```bash
# 确认MCP脚本存在
python query_categorization_metrics.py \
    --mcp-url "path/to/audit_mcp.py"

# 确保fastmcp已安装
pip install fastmcp
```

## 性能优化建议

### 提高测试效率

1. **增加批处理大小**: 如果API限制允许，可以增大 `--batch-size`
2. **减少测试轮数**: 如果不需要稳定性评估，使用 `--rounds 1`
3. **调整超时时间**: 根据实际响应时间调整 `--timeout`

### 提高测试准确性

1. **多轮测试**: 使用 `--rounds 3` 或更多轮次
2. **调整温度**: 尝试不同的 `--temperature` 值（0.1-0.5）
3. **优化工具描述**: 在 `audit_mcp.py` 中改进工具的描述文本

## 依赖项

确保安装了以下Python包：

```bash
pip install fastmcp openai
```

完整的依赖列表：
- `fastmcp`: MCP客户端库
- `openai`: OpenAI API客户端
- `asyncio`: 异步I/O（Python标准库）
- `csv`: CSV文件处理（Python标准库）
- `json`: JSON处理（Python标准库）
- `statistics`: 统计计算（Python标准库）

## 扩展和定制

### 添加新的工具类别

如果需要添加新的工具类别，需要修改以下部分：

1. 在 `audit_mcp.py` 中添加新的工具定义
2. 在 `query_categorization_metrics.py` 中更新 `LABEL_TO_TOOL` 映射：

```python
LABEL_TO_TOOL = {
    "制度类": "regulation_search",
    "实例类": "case_retrieval",
    "新类别": "new_tool_name",  # 添加新映射
}
```

### 自定义指标计算

在 `MetricsCalculator` 类中可以添加自定义的指标计算方法：

```python
class MetricsCalculator:
    # ... 现有方法 ...
    
    def calculate_custom_metric(self):
        """计算自定义指标"""
        # 实现自定义逻辑
        pass
```

### 自定义报告格式

修改 `print_detailed_report()` 函数以自定义输出格式。

## 最佳实践

1. **定期运行测试**: 在更新工具描述或系统提示词后运行测试
2. **保留测试结果**: 保存JSON文件以便对比不同版本的性能
3. **分析错误案例**: 仔细分析错误案例以改进工具设计
4. **多轮验证**: 对关键配置进行多轮测试以确保稳定性
5. **版本控制**: 将测试脚本和结果纳入版本控制

## 许可证

本脚本遵循项目整体的许可证协议。

## 贡献

欢迎提交问题报告和改进建议！

