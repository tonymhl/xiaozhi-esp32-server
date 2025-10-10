# get_temperature_load_rate 工具函数

## 📖 概述

`get_temperature_load_rate` 是为 xiaozhi-esp32-server 项目新增的工具函数，支持通过智能多轮对话交互的方式获取并确认用户的**温度和负载率**参数设置。

> **注意**：本函数是从 `get_temperature_humidity` 改造而来，将湿度参数替换为负载率参数。

## ✨ 特性

- ✅ **智能多轮对话** - 支持分步输入或一次性输入
- ✅ **参数确认机制** - 避免误操作，确保参数准确
- ✅ **灵活输入格式** - 支持多种自然语言表达（22度、22℃、60%等）
- ✅ **参数验证** - 自动验证温度（-10℃~50℃）和负载率（0%~100%）范围
- ✅ **随时修改** - 确认前可随时修改任何参数
- ✅ **取消操作** - 支持随时取消当前设置流程
- ✅ **自动加载** - 无需额外配置，系统自动注册

## 🚀 快速开始

### 1. 验证安装

运行验证脚本：

```bash
cd main/xiaozhi-server
python verify_temperature_load_rate.py
```

预期输出：
```
🎉 所有检查通过！代码结构正确。
```

### 2. 启动服务

按照项目正常流程启动 xiaozhi-server 服务。

### 3. 对话测试

通过终端设备或Web界面测试：

```
👤 "设置温度22度负载率60%"
🤖 "温度为22℃，负载率为60%，请确认是否正确？"
👤 "确认"
🤖 {"temperature": "22℃", "load_rate": "60%", "confirm": true}
```

## 💡 使用示例

### 示例1：一次性设置

```
用户: "设置温度25度负载率70%"
系统: "温度为25℃，负载率为70%，请确认是否正确？"
用户: "确认"
系统: {"temperature": "25℃", "load_rate": "70%", "confirm": true}
```

### 示例2：分步设置

```
用户: "我要设置温度和负载率"
系统: "好的，请告诉我温度和负载率值"
用户: "温度22度"
系统: "温度已设置为22℃，请告诉我负载率值"
用户: "60%"
系统: "温度为22℃，负载率为60%，请确认"
用户: "好的"
系统: {"temperature": "22℃", "load_rate": "60%", "confirm": true}
```

### 示例3：修改参数

```
用户: "温度20度负载率50%"
系统: "温度为20℃，负载率为50%，请确认"
用户: "温度改成22度"
系统: "已修改，温度为22℃，负载率为50%，请确认"
用户: "确认"
系统: {"temperature": "22℃", "load_rate": "50%", "confirm": true}
```

## 🔧 技术信息

### 函数签名

```python
@register_function(
    "get_temperature_load_rate",
    GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_temperature_load_rate(
    conn,
    temperature: str = None,
    load_rate: str = None,
    confirm: bool = False,
    cancel: bool = False
) -> ActionResponse
```

### 返回格式

```json
{
    "temperature": "22℃",
    "load_rate": "60%",
    "confirm": true
}
```

### 支持的输入格式

**温度**：22度、22℃、22摄氏度、-5度、22.5度  
**负载率**：60%、60、0.6

### 参数范围

- **温度**：-10℃ ~ 50℃
- **负载率**：0% ~ 100%

## 🧪 测试

### 运行单元测试

```bash
cd main/xiaozhi-server/plugins_func/functions
python test_get_temperature_load_rate.py
```

### 运行验证脚本

```bash
cd main/xiaozhi-server
python verify_temperature_load_rate.py
```

## 📁 文件结构

```
main/xiaozhi-server/
├── plugins_func/functions/
│   ├── get_temperature_load_rate.py              # 主函数实现
│   └── test_get_temperature_load_rate.py         # 单元测试
├── verify_temperature_load_rate.py               # 验证脚本
└── docs/
    └── get_temperature_load_rate_README.md       # 本文件
```

## 🔗 集成应用示例

### 设备负载监控

```python
@register_function("monitor_device", monitor_desc, ToolType.SYSTEM_CTL)
def monitor_device(conn, params_json: str):
    """使用温度和负载率参数监控设备状态"""
    params = json.loads(params_json)
    
    if params.get("confirm"):
        temp = float(params["temperature"].replace("℃", ""))
        load_rate = float(params["load_rate"].replace("%", ""))
        
        # 调用监控API
        # ...
```

## 🐛 常见问题

### Q1: 负载率的含义是什么？

A: 负载率通常指设备的工作负载百分比，范围为0%-100%。0%表示空载，100%表示满载。

### Q2: 为什么负载率范围是0%-100%？

A: 负载率通常以百分比表示设备的工作状态，与湿度的范围相同。如需其他范围，可以修改 `validate_load_rate` 函数。

### Q3: 如何与旧的 get_temperature_humidity 共存？

A: 两个函数可以同时存在，系统会根据函数描述中的关键词判断调用哪个函数。

## 📋 与 get_temperature_humidity 的区别

| 项目 | get_temperature_humidity | get_temperature_load_rate |
|------|--------------------------|---------------------------|
| 第二参数 | humidity（湿度） | load_rate（负载率） |
| 参数名称 | humidity | load_rate |
| 状态存储 | temp_humidity_setting | temp_load_rate_setting |
| 函数描述关键词 | 温湿度、湿度 | 温度负载率、负载率 |

## 📝 更新记录

- **v1.0.0** (2024-10-09): 从 get_temperature_humidity 改造而来，将湿度参数改为负载率参数

## 🙏 致谢

本函数基于 `get_temperature_humidity` 工具函数改造而成。

---

**创建时间**：2024-10-09  
**版本**：v1.0.0  
**状态**：✅ 已完成并通过验证

