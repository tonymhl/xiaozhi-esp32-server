# get_temperature_humidity 工具函数开发文档

## 1. 概述

### 1.1 功能描述
`get_temperature_humidity` 是一个新的工具函数，用于通过多轮对话交互的方式，从用户处获取温度和湿度两个参数，并确保用户最终确认这组参数后再返回。

### 1.2 使用场景
- 用户需要设置环境温湿度参数
- 用户需要查询或调整空调/加湿器等设备的目标温湿度
- 需要确认用户输入的温湿度参数以避免误操作

### 1.3 返回格式
```json
{
    "temperature": "22℃",
    "humidity": "60%",
    "confirm": true
}
```

## 2. 技术架构分析

### 2.1 系统现有的函数注册机制

#### 2.1.1 装饰器注册
所有插件函数通过 `@register_function` 装饰器注册到全局注册表 `all_function_registry`：

```python
from plugins_func.register import register_function, ToolType, ActionResponse, Action

@register_function('function_name', function_desc, ToolType.SYSTEM_CTL)
def function_name(conn, param1: str, param2: int):
    # 函数实现
    return ActionResponse(action=Action.RESPONSE, result="...", response="...")
```

#### 2.1.2 函数描述格式
函数描述遵循 OpenAI Function Calling 格式：

```python
function_desc = {
    "type": "function",
    "function": {
        "name": "function_name",
        "description": "函数的详细描述，用于LLM理解何时调用此函数",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数1的描述"
                },
                "param2": {
                    "type": "integer",
                    "description": "参数2的描述"
                }
            },
            "required": ["param1", "param2"]
        }
    }
}
```

### 2.2 ToolType 类型说明

系统定义了多种工具类型（位于 `plugins_func/register.py`）：

- `ToolType.NONE` (1): 调用完工具后，不做其他操作
- `ToolType.WAIT` (2): 调用工具，等待函数返回（不需要conn参数）
- `ToolType.CHANGE_SYS_PROMPT` (3): 修改系统提示词
- `ToolType.SYSTEM_CTL` (4): 系统控制，需要传递conn参数
- `ToolType.IOT_CTL` (5): IOT设备控制，需要传递conn参数
- `ToolType.MCP_CLIENT` (6): MCP客户端

**对于需要访问连接状态或多轮交互的函数，应使用 `ToolType.SYSTEM_CTL`**

### 2.3 ActionResponse 返回类型

函数必须返回 `ActionResponse` 对象：

```python
class Action(Enum):
    ERROR = (-1, "错误")
    NOTFOUND = (0, "没有找到函数")
    NONE = (1, "啥也不干")
    RESPONSE = (2, "直接回复")
    REQLLM = (3, "调用函数后再请求llm生成回复")
```

常用返回模式：
- `Action.RESPONSE`: 直接返回response给用户，不经过LLM处理
- `Action.REQLLM`: 将result传给LLM处理后再回复用户
- `Action.NONE`: 函数内部已处理（如播放音乐），不需要额外回复

### 2.4 状态存储机制

系统允许在 `conn` 对象上动态添加属性来存储会话状态，参考现有实现：

```python
# 示例1：存储上一次查询的新闻链接
if not hasattr(conn, "last_news_link"):
    conn.last_news_link = {}
conn.last_news_link = {
    "link": selected_news.get("link", "#"),
    "title": selected_news.get("title", "未知标题")
}

# 示例2：设置退出标志
conn.close_after_chat = True
```

### 2.5 自动加载机制

系统通过 `loadplugins.py` 中的 `auto_import_modules()` 函数自动导入 `plugins_func/functions/` 目录下的所有模块。只需将新文件放入该目录即可自动加载。

## 3. 设计方案

### 3.1 交互流程设计

本函数采用多轮对话模式，支持以下场景：

#### 场景1：用户一次性提供所有参数
```
用户: "设置温度22度，湿度60%"
系统: "您想设置温度为22℃，湿度为60%，请确认是否正确？"
用户: "确认"
系统: [返回确认的参数]
```

#### 场景2：用户分步提供参数
```
用户: "设置温度"
系统: "请告诉我您想设置的温度"
用户: "22度"
系统: "温度已设置为22℃，请告诉我湿度值"
用户: "60%"
系统: "您想设置温度为22℃，湿度为60%，请确认是否正确？"
用户: "确认"
系统: [返回确认的参数]
```

#### 场景3：用户修改参数
```
用户: "设置温度22度，湿度60%"
系统: "您想设置温度为22℃，湿度为60%，请确认是否正确？"
用户: "温度改成25度"
系统: "已修改，温度为25℃，湿度为60%，请确认是否正确？"
用户: "确认"
系统: [返回确认的参数]
```

#### 场景4：用户取消操作
```
用户: "设置温度22度"
系统: "温度已设置为22℃，请告诉我湿度值"
用户: "取消"
系统: "已取消温湿度设置"
```

### 3.2 状态管理

在 `conn` 对象上存储临时状态：

```python
conn.temp_humidity_setting = {
    "temperature": None,      # 温度值（字符串，如"22℃"）
    "humidity": None,         # 湿度值（字符串，如"60%"）
    "temperature_raw": None,  # 原始温度数值
    "humidity_raw": None,     # 原始湿度数值
    "stage": "init"          # 当前阶段：init/collecting/confirming
}
```

### 3.3 参数提取策略

需要从用户输入中提取温度和湿度值，支持多种表达方式：
- 温度：22度、22℃、22摄氏度、二十二度
- 湿度：60%、60、百分之六十

使用正则表达式和自然语言处理提取数值。

### 3.4 函数参数设计

```python
def get_temperature_humidity(
    conn,
    temperature: str = None,  # 温度参数，可选
    humidity: str = None,     # 湿度参数，可选
    confirm: bool = False,    # 是否确认，默认False
    cancel: bool = False      # 是否取消，默认False
):
```

LLM会根据用户输入，智能填充这些参数。

## 4. 实现细节

### 4.1 文件结构

```
main/xiaozhi-server/plugins_func/functions/
└── get_temperature_humidity.py
```

### 4.2 核心函数实现

```python
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
import re

TAG = __name__
logger = setup_logging()

GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_temperature_humidity",
        "description": "用于设置或获取温度和湿度参数。支持用户分步输入或一次性输入。",
        "parameters": {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "string",
                    "description": "温度值，可以是数字加单位（如22度、22℃）"
                },
                "humidity": {
                    "type": "string",
                    "description": "湿度值，可以是数字或百分比（如60%、60）"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "用户是否确认这组参数，默认为false"
                },
                "cancel": {
                    "type": "boolean",
                    "description": "用户是否取消设置，默认为false"
                }
            },
            "required": []
        }
    }
}

@register_function("get_temperature_humidity", GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_temperature_humidity(conn, temperature=None, humidity=None, confirm=False, cancel=False):
    # 实现逻辑
    pass
```

### 4.3 辅助函数

#### 参数解析函数
```python
def parse_temperature(temp_str):
    """从字符串中提取温度数值"""
    # 匹配：22度、22℃、22摄氏度等
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:度|℃|摄氏度)?', temp_str)
    if match:
        return float(match.group(1))
    return None

def parse_humidity(humidity_str):
    """从字符串中提取湿度数值"""
    # 匹配：60%、60等
    match = re.search(r'(\d+(?:\.\d+)?)\s*%?', humidity_str)
    if match:
        value = float(match.group(1))
        # 如果数值大于1，认为是百分比
        if value > 1:
            return value
        else:
            return value * 100
    return None
```

#### 状态初始化函数
```python
def initialize_temp_humidity_state(conn):
    """初始化或获取温湿度设置状态"""
    if not hasattr(conn, "temp_humidity_setting"):
        conn.temp_humidity_setting = {
            "temperature": None,
            "temperature_raw": None,
            "humidity": None,
            "humidity_raw": None,
            "stage": "init"
        }
    return conn.temp_humidity_setting
```

### 4.4 主函数逻辑流程

```
1. 初始化状态
2. 如果cancel=True，清空状态并返回取消消息
3. 如果提供了temperature，更新状态
4. 如果提供了humidity，更新状态
5. 检查是否已有温度和湿度
   - 如果都有且confirm=True，返回最终结果
   - 如果都有但confirm=False，请求用户确认
   - 如果缺少任一参数，提示用户补充
6. 返回相应的ActionResponse
```

## 5. 测试场景

### 5.1 单元测试
- 测试参数解析函数的正确性
- 测试各种输入格式的识别

### 5.2 集成测试
- 测试一次性输入所有参数
- 测试分步输入参数
- 测试修改参数
- 测试取消操作
- 测试异常输入处理

### 5.3 对话测试示例

```
测试1：完整流程
用户: "我要设置温湿度"
预期: 系统询问温度
用户: "温度22度"
预期: 系统记录温度，询问湿度
用户: "湿度60%"
预期: 系统显示汇总，请求确认
用户: "确认"
预期: 返回JSON结果

测试2：一次性输入
用户: "设置温度25度湿度70%"
预期: 系统显示汇总，请求确认
用户: "好的"
预期: 返回JSON结果

测试3：修改参数
用户: "温度20度湿度50%"
预期: 系统请求确认
用户: "温度改成22度"
预期: 系统更新并再次请求确认
用户: "确认"
预期: 返回JSON结果
```

## 6. 注意事项

### 6.1 参数验证
- 温度范围：建议限制在合理范围（如-10℃~50℃）
- 湿度范围：0%~100%
- 对超出范围的值给出友好提示

### 6.2 状态清理
- 成功返回结果后清理 `conn.temp_humidity_setting`
- 取消操作后清理状态
- 考虑添加超时清理机制（可选）

### 6.3 用户体验
- 提示语要友好、清晰
- 支持多种自然语言表达方式
- 错误处理要给出明确的引导

### 6.4 扩展性
- 预留添加更多参数的空间（如风速、模式等）
- 可以将状态持久化到数据库（如需跨会话）
- 可以添加参数预设功能（如"舒适模式"）

## 7. API返回格式说明

### 7.1 最终返回格式
当用户确认后，函数通过 `ActionResponse` 返回：

```python
ActionResponse(
    action=Action.RESPONSE,
    result="设置成功",
    response=json.dumps({
        "temperature": "22℃",
        "humidity": "60%",
        "confirm": True
    }, ensure_ascii=False)
)
```

### 7.2 中间状态返回
在收集参数过程中，使用 `Action.REQLLM` 让LLM生成友好的回复：

```python
ActionResponse(
    action=Action.REQLLM,
    result="已记录温度为22℃，请告诉我湿度值",
    response=None
)
```

## 8. 配置文件支持（可选）

可以在 `config.yaml` 或 `config_from_api.yaml` 中添加配置：

```yaml
plugins:
  get_temperature_humidity:
    enable: true
    temperature_range:
      min: -10
      max: 50
    humidity_range:
      min: 0
      max: 100
    timeout: 300  # 5分钟超时
    default_temperature: 22
    default_humidity: 60
```

## 9. 版本历史

- v1.0.0 (2024-10-09): 初始版本，支持基本的温湿度参数收集和确认功能

## 10. 参考资料

- OpenAI Function Calling API: https://platform.openai.com/docs/guides/function-calling
- 项目现有函数示例：
  - `get_weather.py` - 展示了复杂的参数处理和缓存机制
  - `get_news_from_newsnow.py` - 展示了状态存储和多轮交互
  - `change_role.py` - 展示了简单的函数实现模式
  - `handle_exit_intent.py` - 展示了系统控制类函数的实现

