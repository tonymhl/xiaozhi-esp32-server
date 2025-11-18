# 更新说明 🎉

## 最新改进 (2025-11-18)

### 1. 前端可视化修复 ✅

#### 问题修复
- ✅ 修复了Chart.js加载问题（"Chart is not defined"）
- ✅ 修复了错误案例表格不显示的问题
- ✅ 移除了错误案例数量限制，现在显示全部错误案例
- ✅ 优化了"加载示例数据"按钮的提示信息

#### 使用建议
由于浏览器安全限制，直接打开HTML文件无法使用fetch加载本地JSON。推荐以下方式：

**方法1：使用本地服务器（推荐）**
```bash
# 启动HTTP服务器
python -m http.server 8000

# 在浏览器访问
# http://localhost:8000/visualization.html
```

**方法2：直接打开HTML并手动上传**
```bash
# Windows
start visualization.html

# 然后点击"选择JSON文件"按钮，选择test_results.json
```

### 2. 文本报告自动保存 📄

现在测试完成后会自动生成两个文件：
- `test_results.json` - 完整的JSON数据（用于可视化）
- `test_results.txt` - 控制台报告的文本版本（便于查看和分享）

```bash
python query_categorization_metrics.py --rounds 3

# 生成文件：
# - test_results.json
# - test_results.txt ← 新增！
```

### 3. 多模型支持 🚀

现在支持多个LLM API提供商：

#### DeepSeek-V3（默认）
```bash
python query_categorization_metrics.py --provider deepseek
```

#### 智谱AI GLM-4-Flash
```bash
python query_categorization_metrics.py --provider zhipu
```

#### 自定义API
```bash
python query_categorization_metrics.py \
    --provider custom \
    --api-key "your-api-key" \
    --base-url "https://your-api.com/v1" \
    --model "your-model-name"
```

### 4. 模型对比测试 ⚡

新增对比测试脚本，可以同时测试多个模型并生成对比报告：

```bash
python compare_models.py
```

这将：
1. 依次测试 DeepSeek-V3 和 GLM-4-Flash
2. 每个模型进行3轮测试
3. 生成详细的对比报告
4. 保存对比结果到 `model_comparison.json`

#### 对比指标包括：
- 准确率 (Accuracy)
- Macro F1-Score
- Weighted F1-Score
- 工具调用成功率
- 无工具调用率
- 工具幻觉率
- 平均响应时间
- **综合评分**（加权）

### 5. 错误案例完整显示 📋

前端和控制台报告现在都显示**全部**错误案例，不再限制为10个：

**前端显示：**
- 标题显示错误总数：`错误案例分析（全部 X 个）`
- 表格包含序号、问题、真实标签、预测工具、预测标签
- 支持表格滚动查看所有错误

**控制台报告：**
- 显示全部错误案例的详细信息
- 包含问题、真实标签、预测工具、预测标签

## 快速开始

### 单模型测试

```bash
# DeepSeek-V3 (默认)
python query_categorization_metrics.py --rounds 3

# 智谱AI GLM-4-Flash
python query_categorization_metrics.py --provider zhipu --rounds 3
```

### 多模型对比

```bash
# 自动测试DeepSeek和智谱AI，并生成对比报告
python compare_models.py
```

### 查看可视化报告

```bash
# 启动本地服务器
python -m http.server 8000

# 浏览器访问 http://localhost:8000/visualization.html
# 点击"选择JSON文件"，选择对应的test_results.json
```

## 文件说明

### 生成的文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `test_results.json` | 完整测试数据 | 用于前端可视化 |
| `test_results.txt` | 文本报告 | 便于查看和分享 |
| `test_results_deepseek.json` | DeepSeek测试结果 | 模型对比 |
| `test_results_zhipu.json` | 智谱AI测试结果 | 模型对比 |
| `model_comparison.json` | 模型对比数据 | 对比分析 |

### 核心脚本

| 文件名 | 说明 |
|--------|------|
| `query_categorization_metrics.py` | 主评测脚本 |
| `compare_models.py` | 模型对比脚本 |
| `visualization.html` | 可视化界面 |

## 示例输出

### 文本报告示例

```
================================================================================
测试报告 - 审计Agent工具分类准确率评估
================================================================================

测试时间: 2025-11-18 18:42:08
模型: deepseek-ai/DeepSeek-V3
温度: 0.3
测试轮数: 3
每轮测试样本数: 25

--------------------------------------------------------------------------------
各轮测试结果汇总
--------------------------------------------------------------------------------

第 1 轮:
  准确率: 96.00% (24/25)
  无预测: 0 个
  平均响应时间: 0.715秒

...
```

### 模型对比示例

```
================================================================================
模型对比报告
================================================================================

核心指标对比
--------------------------------------------------------------------------------
指标                           deepseek        zhipu          
--------------------------------------------------------------------------------
准确率 (Accuracy)                 96.00%          92.00%
Macro F1-Score                   88.89%          85.50%
Weighted F1-Score                95.64%          93.20%
工具调用成功率                    96.00%          92.00%
无工具调用率                       0.00%           4.00%
工具幻觉率                         0.00%           0.00%
平均响应时间 (秒)                 0.641s          0.823s

综合评分 (加权)
--------------------------------------------------------------------------------
  deepseek: 94.32分
  模型: deepseek-ai/DeepSeek-V3

     zhipu: 90.15分
  模型: glm-4-flash
```

## 常见问题

### Q1: 前端图表不显示？

**A:** 确保使用本地服务器访问，而不是直接打开HTML文件：
```bash
python -m http.server 8000
# 访问 http://localhost:8000/visualization.html
```

### Q2: JSON文件解析失败？

**A:** 检查JSON文件是否完整，可以用文本编辑器打开查看。如果文件损坏，重新运行测试生成新的JSON文件。

### Q3: 如何测试自己的模型？

**A:** 使用 `--provider custom` 参数：
```bash
python query_categorization_metrics.py \
    --provider custom \
    --api-key "your-key" \
    --base-url "https://your-api.com/v1" \
    --model "your-model"
```

### Q4: 如何只对比某两个模型？

**A:** 修改 `compare_models.py` 中的 `providers` 列表：
```python
providers = ["deepseek", "zhipu"]  # 修改这里
```

## 性能对比参考

基于当前测试数据（25个样本）：

| 模型 | 准确率 | F1分数 | 工具成功率 | 响应时间 |
|------|--------|--------|-----------|---------|
| DeepSeek-V3 | 96% | 95.64% | 96% | 0.64s |
| GLM-4-Flash | 待测试 | 待测试 | 待测试 | 待测试 |

## 下一步

1. **扩充测试集**：在CSV中添加更多QA对以获得更准确的评估
2. **运行对比测试**：使用 `compare_models.py` 对比多个模型
3. **分析错误案例**：查看全部错误案例，优化工具描述
4. **调整参数**：尝试不同的temperature值

## 反馈和建议

如有问题或建议，请在项目中提出Issue。

