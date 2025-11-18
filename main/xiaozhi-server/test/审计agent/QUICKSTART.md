# 快速开始指南 🚀

本指南帮助您快速上手使用审计Agent工具分类评测系统。

## 📋 前置条件

### 1. 安装依赖

```bash
pip install fastmcp openai
```

### 2. 检查文件结构

确保以下文件存在：
```
审计agent/
├── 03_exp/
│   ├── audit_mcp.py           # MCP工具定义
│   ├── classify.py             # 原版分类脚本
│   └── readme.md
├── query_categorization_metrics.py  # 评测脚本
├── visualization.html          # 可视化界面
├── 审计QA——人工版-工作表1.csv   # 测试数据
├── README_metrics.md           # 详细文档
├── CODE_CONSISTENCY.md         # 代码一致性说明
└── QUICKSTART.md               # 本文件
```

### 3. 准备测试数据

测试数据CSV文件应包含以下列：
- `Q`: 用户问题
- `标签`: 正确的分类（"制度类" 或 "实例类"）

示例：
```csv
编号,文档,Q,A,标签,路径
1,数据中心人员设备进出管理规定,请提供人员设备进出管理的相关制度,,制度类,
2,,浦江25年的培训计划是什么,,实例类,
```

## 🎯 快速测试（3步）

### 步骤1：运行基础测试

```bash
python query_categorization_metrics.py
```

这将使用默认参数运行一轮测试。

### 步骤2：查看控制台报告

测试完成后，控制台会显示详细的评测报告，包括：
- 核心性能指标（准确率、F1分数等）
- LLM工具调用专属指标
- 各类别详细指标
- 混淆矩阵
- 错误案例分析

### 步骤3：查看可视化报告

1. 在浏览器中打开 `visualization.html`
2. 点击"加载示例数据"按钮
3. 查看交互式图表和指标卡片

## 📊 进阶使用

### 多轮稳定性测试

```bash
python query_categorization_metrics.py --rounds 3
```

运行3轮测试以评估模型的稳定性和一致性。

### 调整批处理大小

```bash
python query_categorization_metrics.py --batch-size 5
```

根据API限制和网络条件调整并行批处理大小。

### 测试不同温度参数

```bash
# 较低温度（更确定性）
python query_categorization_metrics.py --temperature 0.1

# 较高温度（更随机性）
python query_categorization_metrics.py --temperature 0.7
```

### 指定输出文件

```bash
python query_categorization_metrics.py \
    --output-json results_temp_0.3.json
```

## 🎨 可视化使用

### 方法1：直接打开（推荐）

Windows:
```cmd
start visualization.html
```

Mac:
```bash
open visualization.html
```

Linux:
```bash
xdg-open visualization.html
```

### 方法2：使用本地服务器

```bash
# 启动HTTP服务器
python -m http.server 8000

# 在浏览器访问
# http://localhost:8000/visualization.html
```

### 加载数据

1. 点击"📁 选择JSON文件"按钮
2. 选择生成的 `test_results.json` 文件
3. 或点击"📊 加载示例数据"自动加载

## 🔧 常见问题

### Q1: 遇到连接错误怎么办？

**问题**：所有请求都显示 "Connection error"

**解决方法**：
```bash
# 检查API配置
python query_categorization_metrics.py \
    --api-key "your-valid-key" \
    --base-url "https://correct-url.com/v1"

# 或设置环境变量
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://your-url.com/v1"
```

### Q2: CSV文件加载失败？

**问题**："未能从CSV文件中加载有效的测试数据"

**解决方法**：
1. 确保CSV文件编码为UTF-8
2. 确保包含"Q"和"标签"列
3. 检查标签值是否为"制度类"或"实例类"

### Q3: 如何验证代码一致性？

请查看 `CODE_CONSISTENCY.md` 文档，其中详细对比了测试脚本与原版代码的一致性。

### Q4: 可视化界面无法加载数据？

**解决方法**：
1. 确保JSON文件与HTML在同一目录
2. 如果使用"加载示例数据"，确保 `test_results.json` 存在
3. 使用浏览器开发者工具查看错误信息

## 📈 完整测试流程示例

### 场景：评估模型在不同温度下的表现

```bash
# 1. 温度 0.1（最确定）
python query_categorization_metrics.py \
    --temperature 0.1 \
    --rounds 3 \
    --output-json results_temp_0.1.json

# 2. 温度 0.3（推荐）
python query_categorization_metrics.py \
    --temperature 0.3 \
    --rounds 3 \
    --output-json results_temp_0.3.json

# 3. 温度 0.5（平衡）
python query_categorization_metrics.py \
    --temperature 0.5 \
    --rounds 3 \
    --output-json results_temp_0.5.json

# 4. 对比结果
# 在可视化界面中分别加载这三个JSON文件，对比性能指标
```

## 🎓 评测指标说明

### 核心指标

| 指标 | 说明 | 理想值 |
|------|------|--------|
| Accuracy | 整体准确率 | > 90% |
| Macro F1 | 各类别F1的平均值 | > 85% |
| Weighted F1 | 按样本数加权的F1 | > 85% |

### LLM工具调用专属指标

| 指标 | 说明 | 理想值 |
|------|------|--------|
| Tool Call Success Rate | 工具调用成功率 | > 90% |
| No Tool Call Rate | 无工具调用率 | < 5% |
| Tool Hallucination Rate | 工具幻觉率 | 0% |
| Single Tool Call Accuracy | 单工具调用准确率 | > 95% |

## 📚 更多资源

- **详细文档**: `README_metrics.md`
- **代码一致性说明**: `CODE_CONSISTENCY.md`
- **原版脚本**: `03_exp/classify.py`
- **MCP工具定义**: `03_exp/audit_mcp.py`

## 💡 最佳实践

1. **基线测试**: 首先运行单轮测试建立基线
2. **稳定性验证**: 使用3-5轮测试验证稳定性
3. **参数调优**: 尝试不同温度参数找到最佳配置
4. **定期评测**: 在更新工具描述或系统提示词后重新评测
5. **保留记录**: 保存JSON结果文件以便对比不同版本的性能

## 🎉 开始测试

准备好了吗？运行您的第一个测试：

```bash
python query_categorization_metrics.py --rounds 3
```

测试完成后，在浏览器中打开 `visualization.html` 查看精美的可视化报告！

---

如有问题，请查看详细文档或在项目中提出Issue。

