# Query Rewrite Agent

该项目包含一个用于审计查询改写的智能 Agent，以及配套的评估框架和可视化看板。

## 目录结构

*   `query_rewriter.py`: 核心 Agent 实现，包含 Prompt Engineering 和 LLM 调用逻辑。
*   `evaluator.py`: 批量评估脚本，使用并发跑批来评估 Agent 的准确率。
*   `llm_client.py`: 封装 DeepSeek API 调用，支持 `aiohttp` 异步调用和 `curl` fallback。
*   `server.py`: 一个简单的 aiohttp Web 服务器，用于展示评估结果看板。
*   `index.html`: 看板的前端页面。
*   `test_case.json`: 测试用例集。
*   `evaluation_results.json`: 评估运行后生成的详细结果文件。

## 快速开始

### 1. 安装依赖

确保已安装 `aiohttp` 和 `requests`：

```bash
pip install aiohttp requests
```

### 2. 运行评估

运行评估脚本以生成最新的测试结果：

```bash
python evaluator.py
```

该脚本会：
1.  加载 `test_case.json`。
2.  并发调用 `QueryRewriteAgent` 进行改写。
3.  使用 LLM Judge 对改写结果进行语义一致性判定。
4.  生成 `evaluation_results.json`。

### 3. 启动看板

启动 Web 服务以查看结果：

```bash
python server.py
```

打开浏览器访问 `http://localhost:8080` (端口可在 `server.py` 中修改)。

在看板中，您可以：
*   查看总体准确率。
*   查看每个 Case 的 Input, Expected, Actual Output。
*   **人工复核 (Human Review)**: 点击 ✔ 或 ✘ 按钮修正模型的判定结果。修正后，准确率会实时更新。

## 优化策略说明

*   **Few-Shot Prompting**: 针对复杂的边缘案例（如不一致的 Ground Truth），在 Prompt 中加入了具体的 Few-Shot 示例。
*   **Strict JSON**: 强制模型仅输出 JSON 格式，避免解析错误。
*   **并发优化**: 使用 `asyncio` + `aiohttp` 大幅缩短跑批时间。

## 注意事项

*   由于 `test_case.json` 中的部分 Expected 结果存在一定的主观性或不一致性（例如是否包含特定隐含设备），模型评估准确率通常在 80% 左右。
*   建议结合人工看板进行最终确认。

