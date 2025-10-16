# 温度负载率工具函数 - API集成改造完成总结

## ✅ 改造完成

已成功完成 `get_temperature_load_rate` 工具函数的API集成改造，实现了完整的递进式两轮确认流程，集成了外部API接口，可用于启动AI节能优化。

## 📁 改动文件

### 1. 核心功能文件

**文件**：`main/xiaozhi-server/plugins_func/functions/get_temperature_load_rate.py`

**主要改动**：
- ✅ 添加 `requests` 库支持
- ✅ 添加 API 配置管理（`get_api_base_url`）
- ✅ 实现接口1调用函数（`call_asr_api`）
- ✅ 实现接口2调用函数（`call_confirm_api`）
- ✅ 重构主函数，实现完整的递进式两轮确认流程
- ✅ 修改负载率解析和验证（从百分比改为kw单位）
- ✅ 添加预设参数支持（快速响应）
- ✅ 增强状态管理（添加 `api1_response`、`confirm_stage` 字段）
- ✅ 完善错误处理和超时保护
- ✅ 更新函数描述，明确负载率单位为kw

### 2. 文档文件

#### 详细开发文档
**文件**：`docs/get_temperature_load_rate_api_integration.md`

**内容**：
- 功能特点说明
- API接口详细说明
- 完整交互流程图
- 状态管理说明
- 配置说明
- 使用示例
- 错误处理
- 测试建议
- 性能优化
- 安全性考虑

#### 快速开始指南
**文件**：`docs/get_temperature_load_rate_quickstart.md`

**内容**：
- 快速配置步骤
- API验证方法
- 使用技巧
- 完整对话示例
- 常见问题解答
- 故障排查指南
- 性能对比表

## 🎯 核心功能

### 1. API集成

#### 接口1：/api/asr - 参数设置
```bash
POST http://10.100.193.243:9000/api/asr
Content-Type: application/json

{
    "temperature": "22.5",
    "load_rate": "90"
}
```

**功能**：提交温度和负载率参数，准备进入确认流程

#### 接口2：/api/confirm - 确认操作
```bash
POST http://10.100.193.243:9000/api/confirm
Content-Type: application/json

{
    "status": 1  // 1=确认, 0=取消
}
```

**功能**：
- 第一次调用：确认参数设置（返回 stage=1）
- 第二次调用：确认使用AI推荐模式（返回 stage=2）

### 2. 递进式两轮确认

```
用户输入参数
    ↓
调用接口1
    ↓
第一次确认请求 ——→ 用户确认 ——→ 调用接口2（第一次）
    ↓
第二次确认请求 ——→ 用户确认 ——→ 调用接口2（第二次）
    ↓
完成流程，启动AI节能优化
```

### 3. 预设快速响应参数

为了避免超时（10-30秒），系统预设了两组快速响应参数（毫秒级）：

| 温度 | 负载率 |
|------|--------|
| 22.5℃ | 90kw |
| 28℃ | 95.6kw |

### 4. 健壮性设计

- ✅ 参数范围验证（温度：-10~50℃，负载率：0~200kw）
- ✅ 超时保护（接口1：35秒，接口2：10秒）
- ✅ 任务冲突检测（409错误处理）
- ✅ 完整的错误处理和恢复
- ✅ 状态隔离（每个连接独立状态）
- ✅ 异常情况自动清除状态

## 📝 使用示例

### 示例1：使用预设参数（推荐）

```
用户："设置温度22.5度，负载率90千瓦"
系统：[调用接口1，毫秒级响应]
     "您要设置温度22.5℃，负载率90kw，请确认是否正确？"
用户："确认"
系统：[调用接口2第一次]
     "好的，参数已确认。是否使用AI推荐模式进行节能优化？"
用户："好的"
系统：[调用接口2第二次]
     "✅ 已确认使用AI推荐模式，开始AI节能优化
      温度: 22.5℃
      负载率: 90kw
      系统已启动AI节能优化流程"
```

### 示例2：分步输入

```
用户："设置温度"
系统："好的，请问您想设置的温度是多少度？"
用户："28度"
系统："温度已设置为28℃，请问负载率是多少千瓦？"
用户："95.6千瓦"
系统：[调用接口1，毫秒级响应]
     "您要设置温度28℃，负载率95.6kw，请确认是否正确？"
... [后续流程同示例1]
```

### 示例3：中途取消

```
用户："设置温度22度，负载率90千瓦"
系统："您要设置温度22℃，负载率90kw，请确认是否正确？"
用户："取消"
系统：[调用接口2，status=0]
     "好的，已取消温度负载率设置"
```

## ⚙️ 配置方法

在 `main/xiaozhi-server/config.yaml` 或 `data/.config.yaml`（推荐）中添加：

```yaml
plugins:
  get_temperature_load_rate:
    api_base_url: "http://10.100.193.243:9000"
```

**说明**：
- 如果不配置，使用默认值：`http://10.100.193.243:9000`
- 推荐在 `data/.config.yaml` 中配置，保护配置安全

## 🔍 验证方法

### 方法1：手动测试API

```bash
# 测试接口1
curl --location 'http://10.100.193.243:9000/api/asr' \
--header 'Content-Type: application/json' \
--data '{"temperature": "22.5", "load_rate": "90"}'

# 测试接口2
curl --location 'http://10.100.193.243:9000/api/confirm' \
--header 'Content-Type: application/json' \
--data '{"status": 1}'
```

### 方法2：语法检查

```bash
cd main/xiaozhi-server
python -m py_compile plugins_func/functions/get_temperature_load_rate.py
```

### 方法3：实际对话测试

启动服务后，通过语音或文本与小智交互：
- "设置温度22.5度，负载率90千瓦"
- 观察完整的两轮确认流程

## 📊 关键技术点

### 1. 状态管理

使用 `conn.temp_load_rate_setting` 维护对话状态：

```python
{
    "temperature": "22.5℃",
    "temperature_raw": 22.5,
    "load_rate": "90kw",
    "load_rate_raw": 90.0,
    "stage": "stage1_confirming",  # 当前阶段
    "api1_response": {...},         # 接口1响应
    "confirm_stage": 0,             # 0/1/2
}
```

### 2. 阶段转换

```
init → collecting → api1_success → stage1_confirming 
  → stage1_success → stage2_confirming → completed
```

### 3. 预设参数检测

```python
is_preset = any(
    abs(temp_raw - p["temperature"]) < 0.01 and 
    abs(load_raw - p["load_rate"]) < 0.01
    for p in PRESET_PARAMS
)
```

### 4. API调用封装

- `call_asr_api(base_url, temperature, load_rate)` - 接口1
- `call_confirm_api(base_url, status)` - 接口2

返回格式：`(success: bool, response_data: dict, error_msg: str)`

## ⚠️ 重要注意事项

### 1. 负载率单位
- ✅ 正确：负载率单位是 **千瓦(kw)**
- ❌ 错误：不是百分比(%)

### 2. 预设参数
- 推荐使用预设参数 (22.5, 90) 或 (28, 95.6) 获得毫秒级响应
- 其他参数可能需要 10-30 秒处理时间

### 3. 超时设置
- 接口1：35秒超时（考虑非预设参数的处理时间）
- 接口2：10秒超时

### 4. 任务冲突
- 如果后台有优化任务在进行，接口1会返回409错误
- 用户需要等待几分钟后重试

### 5. 确认流程
- 必须按顺序完成：参数设置 → 第一次确认 → 第二次确认
- 跳过任何步骤都会导致流程失败

## 🐛 常见问题

### Q1: 如何修改API地址？
**A**: 在 `config.yaml` 的 `plugins.get_temperature_load_rate.api_base_url` 配置项中修改

### Q2: 为什么响应很慢？
**A**: 如果不使用预设参数，API处理需要10-30秒。建议使用预设参数 (22.5, 90) 或 (28, 95.6)

### Q3: 提示"优化任务正在进行中"怎么办？
**A**: 后台正在执行其他任务，请等待几分钟后重试

### Q4: 如何调试API调用？
**A**: 查看日志，搜索关键词：
- "调用ASR API"
- "ASR API响应"
- "调用确认API"
- "确认API响应"

### Q5: 可以修改温度和负载率的范围吗？
**A**: 可以，修改 `validate_temperature` 和 `validate_load_rate` 函数

## 📚 文档导航

| 文档 | 说明 | 路径 |
|------|------|------|
| 详细开发文档 | API集成技术细节 | `docs/get_temperature_load_rate_api_integration.md` |
| 快速开始指南 | 配置和使用指南 | `docs/get_temperature_load_rate_quickstart.md` |
| 本总结文档 | 改造完成总结 | `温度负载率工具函数API集成完成总结.md` |
| 源代码 | 核心功能实现 | `main/xiaozhi-server/plugins_func/functions/get_temperature_load_rate.py` |

## ✨ 亮点特性

1. **递进式确认**：两轮确认机制，确保用户充分理解操作
2. **预设快速响应**：毫秒级响应，极佳的用户体验
3. **健壮的错误处理**：完整的异常捕获和恢复机制
4. **灵活的对话方式**：支持一次性或分步输入参数
5. **清晰的状态管理**：每个连接独立维护状态
6. **详细的日志记录**：便于调试和问题排查
7. **配置灵活性**：支持自定义API地址

## 🎉 完成情况

- ✅ API接口集成完成
- ✅ 递进式两轮确认流程实现
- ✅ 预设快速响应参数配置
- ✅ 错误处理和超时保护
- ✅ 状态管理优化
- ✅ 负载率单位修正（kw）
- ✅ 详细开发文档编写
- ✅ 快速开始指南编写
- ✅ 完成总结文档编写

## 🚀 下一步建议

1. **测试验证**：
   - 启动服务进行实际对话测试
   - 验证两轮确认流程
   - 测试预设参数快速响应
   - 测试异常情况处理

2. **性能监控**：
   - 监控API调用响应时间
   - 统计预设参数使用率
   - 记录超时和失败情况

3. **用户反馈**：
   - 收集用户使用体验
   - 优化对话引导语
   - 调整参数范围限制

4. **功能扩展**（可选）：
   - 支持更多预设参数组合
   - 添加参数历史记录
   - 实现参数模板功能

## 📞 技术支持

如有问题，请：
1. 查看详细开发文档
2. 检查日志输出
3. 使用 curl 手动测试API
4. 提供详细的错误信息

---

**改造完成！祝使用愉快！** 🎊

**开发日期**：2025年10月15日  
**版本**：v2.0 - API集成版

