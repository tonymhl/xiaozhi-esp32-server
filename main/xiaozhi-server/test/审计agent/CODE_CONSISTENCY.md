# 代码一致性说明

## 概述

本文档说明 `query_categorization_metrics.py` 如何确保完全使用原版 `03_exp/classify.py` 的代码逻辑，以保证评测的公平性和客观性。

## 核心函数对比

### 1. MCP工具加载函数

#### 原版 (`03_exp/classify.py`)
```python
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
```

#### 测试脚本 (`query_categorization_metrics.py`)
```python
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
```

**结论**: ✅ **完全一致**，逐字逐句相同。

---

### 2. 系统提示词

#### 原版 (`03_exp/classify.py` 第44-48行)
```python
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
system_prompt = (
    "你是一个专业的审计与知识检索助手。"
    f"\n现在的时间是上海时间: {now}"
    "\n当有合适的工具可用时，应优先选择工具以获取更准确的信息。"
)
```

#### 测试脚本 (`query_categorization_metrics.py` 第266-271行)
```python
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
system_prompt = (
    "你是一个专业的审计与知识检索助手。"
    f"\n现在的时间是上海时间: {now}"
    "\n当有合适的工具可用时，应优先选择工具以获取更准确的信息。"
)
```

**结论**: ✅ **完全一致**，系统提示词逐字相同。

---

### 3. 消息构建

#### 原版 (`03_exp/classify.py` 第51-54行)
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": question},
]
```

#### 测试脚本 (`query_categorization_metrics.py` 第273-276行)
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": question},
]
```

**结论**: ✅ **完全一致**，消息结构相同。

---

### 4. API调用参数

#### 原版 (`03_exp/classify.py` 第56-63行)
```python
response = await aclient.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temperature,
    tools=tools,
    tool_choice="auto",
    max_completion_tokens=max_tokens,
)
```

#### 测试脚本 (`query_categorization_metrics.py` 第280-287行)
```python
response = await aclient.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temperature,
    tools=tools,
    tool_choice="auto",
    max_completion_tokens=max_tokens,
)
```

**结论**: ✅ **完全一致**，API调用参数完全相同。

---

### 5. 工具名称提取逻辑

#### 原版 (`03_exp/classify.py` 第65-71行)
```python
message = response.choices[0].message
called_tool_names: list[str] = []
if getattr(message, "tool_calls", None):
    for call in message.tool_calls:
        if getattr(call, "function", None) and getattr(call.function, "name", None):
            called_tool_names.append(call.function.name)

return called_tool_names
```

#### 测试脚本 (`query_categorization_metrics.py` 第291-297行)
```python
message = response.choices[0].message
called_tool_names: List[str] = []
if getattr(message, "tool_calls", None):
    for call in message.tool_calls:
        if getattr(call, "function", None) and getattr(call.function, "name", None):
            called_tool_names.append(call.function.name)

return called_tool_names, response_time, response
```

**结论**: ✅ **逻辑完全一致**，唯一差异是返回值增加了 `response_time` 和 `response`，这不影响工具选择的逻辑。

---

### 6. MCP服务URL

#### 原版 (`03_exp/classify.py` 第76行)
```python
mcp_path = str((Path(__file__).parent / "audit_mcp.py").absolute())
```

#### 测试脚本 (`query_categorization_metrics.py` 第559行)
```python
mcp_path = str((script_dir / "03_exp" / "audit_mcp.py").absolute())
```

**结论**: ✅ **指向同一个文件**，都指向 `03_exp/audit_mcp.py`。

---

## 新增功能说明

测试脚本在保持核心逻辑不变的基础上，仅增加了以下**辅助功能**，这些功能不会影响模型的工具选择行为：

### 1. 响应时间统计
- 在API调用前后记录时间戳
- 计算响应时间用于性能分析
- **不影响模型行为**

### 2. 错误处理
```python
try:
    response = await aclient.chat.completions.create(...)
    # ... 原版逻辑 ...
except Exception as e:
    print(f"Error processing question '{question}': {e}")
    return [], response_time, None
```
- 增加了异常捕获，避免单个请求失败导致整个测试中断
- 失败时返回空工具列表，视为"无预测"
- **不影响模型行为**

### 3. 批量处理和并行
- 支持批量读取CSV数据
- 支持并行调用API提高效率
- **不影响模型行为**，每个查询仍然独立处理

### 4. 结果封装
- 将返回值封装为 `TestResult` 对象
- 便于后续统计和分析
- **不影响模型行为**

## 关键参数默认值对比

| 参数 | 原版默认值 | 测试脚本默认值 | 一致性 |
|------|-----------|---------------|--------|
| model | `deepseek-ai/DeepSeek-V3` | `deepseek-ai/DeepSeek-V3` | ✅ 一致 |
| temperature | `0.3` | `0.3` | ✅ 一致 |
| max_tokens | `1024` | `1024` | ✅ 一致 |
| base_url | `https://deepseek.gds-services.com/v1` | `https://deepseek.gds-services.com/v1` | ✅ 一致 |
| api_key | `av7b4VoBryCMu3hZ9` | `av7b4VoBryCMu3hZ9` | ✅ 一致 |
| timeout | `60` | `60` | ✅ 一致 |

## 总结

### ✅ 保证的一致性

1. **MCP工具加载逻辑**: 完全相同
2. **系统提示词**: 逐字相同
3. **消息构建**: 完全相同
4. **API调用参数**: 完全相同
5. **工具名称提取**: 逻辑完全相同
6. **默认参数值**: 完全相同

### ➕ 新增的辅助功能

1. 响应时间统计（不影响模型）
2. 错误处理（不影响模型）
3. 批量处理（不影响模型）
4. 结果封装（不影响模型）
5. 详细的性能指标计算
6. 可视化界面

### 🎯 结论

测试脚本 **100%保留了原版 `03_exp/classify.py` 的核心逻辑**，所有可能影响模型工具选择的代码都保持一致。新增的功能仅用于：

- 提高测试效率（并行处理）
- 增强健壮性（错误处理）
- 丰富分析维度（性能指标）
- 改善用户体验（可视化）

因此，测试结果能够**客观、公正地反映原版03_exp的agent工具调用表现**。

## 验证方法

如果您想要验证一致性，可以：

1. 对比两个文件的关键函数代码
2. 使用相同的输入运行两个脚本，验证输出的工具名称是否一致
3. 检查代码diff，确认所有差异都是辅助功能

```bash
# 使用classify.py测试单个问题
python 03_exp/classify.py --question "检索培训管理规定"

# 使用metrics脚本测试同一个问题
python query_categorization_metrics.py --csv-path test_single.csv

# 对比输出的工具名称应该完全一致
```

