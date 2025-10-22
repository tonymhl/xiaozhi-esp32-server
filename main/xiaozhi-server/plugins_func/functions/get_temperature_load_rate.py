import re
import json
import requests
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# API 配置默认值
DEFAULT_API_BASE_URL = "http://10.3.193.243:9000"
DEFAULT_API_TIMEOUT = 35  # 接口超时时间（秒）

# 预设快速响应参数（毫秒级响应，避免超时）
PRESET_PARAMS = [
    {"temperature": 22.5, "load_rate": 90.0},
    {"temperature": 28.0, "load_rate": 95.6},
]

GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_temperature_load_rate",
        "description": (
            "【AI节能优化工具】用于设置新工况参数（温度和负载率），启动AI寻优计算。"
            "⚠️ 重要：只要用户提及温度、负载率、确认、节能优化等相关内容，必须立即调用此函数，不要只是文字回复！"
            "功能说明：根据用户输入新的温度（℃）和负载率（%），系统设置新工况并启动AI寻优计算。"
            "用户可以：①只设置温度；②只设置负载率；③同时设置温度和负载率；④使用预设推荐值。"
            "【必须调用的场景】："
            "- 用户提及'设置温度'、'调整负载率'、'温度XX度'、'负载率XX'等 → 立即调用本函数并传入参数"
            "- 用户说'确认/好的/是的/可以/没错/授权/同意/OK'等肯定词 → 立即调用get_temperature_load_rate(confirm=True)"
            "- 用户说'取消/不要/算了/不/错了/拒绝/NO'等否定词 → 立即调用get_temperature_load_rate(cancel=True)"
            "- 用户说'推荐值/帮我设置/默认值/随便设置' → 立即调用get_temperature_load_rate(use_preset=True)"
            "【禁止行为】：不要在没有调用此函数的情况下直接文字回复'好的我帮你设置'等内容，必须调用函数！"
            "注意：负载率的单位是百分比(%)，范围在0%-100%之间。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "string",
                    "description": "温度值，可以是数字加单位（如22度、22℃、28摄氏度）。如果用户没有提供则为空",
                },
                "load_rate": {
                    "type": "string",
                    "description": "负载率值，单位是百分比%（如90%、95.6%、90）。范围：0%-100%。如果用户没有提供则为空",
                },
                "use_preset": {
                    "type": "boolean",
                    "description": "用户是否希望使用预设的推荐参数。当用户说'随便设置'、'帮我设置'、'用推荐值'、'默认值'、'不知道设什么'等时为true",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "用户是否确认授权当前操作。当用户说'确认'、'是的'、'对的'、'好的'、'没错'、'授权'、'同意'等表示同意时为true",
                },
                "cancel": {
                    "type": "boolean",
                    "description": "用户是否取消设置。当用户说'取消'、'不要了'、'算了'、'拒绝'等表示放弃时为true",
                },
            },
            "required": [],
        },
    },
}


def parse_temperature(temp_str):
    """从字符串中提取温度数值
    
    支持格式：
    - 22度、22℃、22摄氏度
    - 数字：22、22.5
    """
    if temp_str is None:
        return None, None
    
    # 尝试匹配温度
    # 匹配：22度、22℃、22摄氏度、22.5度等
    match = re.search(r'(-?\d+(?:\.\d+)?)\s*(?:度|℃|摄氏度|°C|°c)?', str(temp_str))
    if match:
        temp_value = float(match.group(1))
        temp_formatted = f"{temp_value}℃"
        return temp_value, temp_formatted
    return None, None


def parse_load_rate(load_rate_str):
    """从字符串中提取负载率数值（百分比）
    
    支持格式：
    - 90、90.5、90%、90percent
    """
    if load_rate_str is None:
        return None, None
    
    # 移除可能的单位，提取数字
    # 匹配：90、90.5、90%、90percent、90 %等
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|百分比)?', str(load_rate_str), re.IGNORECASE)
    if match:
        load_rate_value = float(match.group(1))
        load_rate_formatted = f"{load_rate_value}%"
        return load_rate_value, load_rate_formatted
    return None, None


def validate_temperature(temp_value):
    """验证温度是否在合理范围内"""
    if temp_value is None:
        return True, None
    if temp_value < -15 or temp_value > 45:
        return False, f"温度{temp_value}℃超出合理范围（-15℃~45℃），请重新输入"
    return True, None


def validate_load_rate(load_rate_value):
    """验证负载率（百分比）是否在合理范围内"""
    if load_rate_value is None:
        return True, None
    if load_rate_value < 0 or load_rate_value > 100:
        return False, f"负载率{load_rate_value}%超出合理范围（0%-100%），请重新输入"
    return True, None


def get_api_base_url(conn):
    """从配置中获取API基础URL"""
    try:
        if conn.config.get("plugins") and conn.config["plugins"].get("get_temperature_load_rate"):
            return conn.config["plugins"]["get_temperature_load_rate"].get("api_base_url", DEFAULT_API_BASE_URL)
    except Exception as e:
        logger.bind(tag=TAG).warning(f"获取API配置失败，使用默认值: {e}")
    return DEFAULT_API_BASE_URL


def call_asr_api(base_url, temperature=None, load_rate=None):
    """调用接口1: /api/asr 设置温度和/或负载率
    
    Args:
        base_url: API基础URL
        temperature: 温度数值（不带单位），可选
        load_rate: 负载率数值（不带单位），可选
    
    Returns:
        (success: bool, response_data: dict, error_msg: str)
    
    Note:
        至少需要提供 temperature 或 load_rate 其中一个参数
    """
    url = f"{base_url}/api/asr"
    payload = {}
    
    # 只添加非空参数
    if temperature is not None:
        payload["temperature"] = str(temperature)
    if load_rate is not None:
        payload["load_rate"] = str(load_rate)
    
    try:
        logger.bind(tag=TAG).info(f"调用ASR API: {url}, 参数: {payload}")
        response = requests.post(url, json=payload, timeout=DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        logger.bind(tag=TAG).info(f"ASR API响应: {data}")
        
        if data.get("status") == "success":
            return True, data, None
        elif data.get("status") == "fail":
            error_msg = data.get("message", "未知错误")
            code = data.get("code", 0)
            if code == 409:
                return False, data, "优化任务正在进行中，请稍后再试"
            return False, data, error_msg
        else:
            error_msg = data.get("message", "未知错误")
            return False, data, error_msg
            
    except requests.Timeout:
        logger.bind(tag=TAG).error(f"ASR API调用超时")
        return False, None, "接口调用超时，请稍后再试"
    except requests.RequestException as e:
        logger.bind(tag=TAG).error(f"ASR API调用失败: {e}")
        return False, None, f"接口调用失败: {str(e)}"
    except Exception as e:
        logger.bind(tag=TAG).error(f"ASR API调用异常: {e}")
        return False, None, f"调用异常: {str(e)}"


def call_confirm_api(base_url, status):
    """调用接口2: /api/confirm 确认操作
    
    Args:
        base_url: API基础URL
        status: 1=确认, 0=取消
    
    Returns:
        (success: bool, response_data: dict, error_msg: str)
    """
    url = f"{base_url}/api/confirm"
    payload = {"status": status}
    
    try:
        logger.bind(tag=TAG).info(f"调用确认API: {url}, 参数: {payload}")
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.bind(tag=TAG).info(f"确认API响应: {data}")
        
        if data.get("status") == "success":
            stage = data.get("stage", 0)
            message = data.get("message", {})
            return True, data, None
        elif data.get("status") == "canceled":
            return True, data, None  # 取消也算成功
        elif data.get("status") == "fail":
            error_msg = data.get("message", "未知错误")
            return False, data, error_msg
        else:
            error_msg = data.get("message", "未知错误")
            return False, data, error_msg
            
    except requests.Timeout:
        logger.bind(tag=TAG).error(f"确认API调用超时")
        return False, None, "接口调用超时"
    except requests.RequestException as e:
        logger.bind(tag=TAG).error(f"确认API调用失败: {e}")
        return False, None, f"接口调用失败: {str(e)}"
    except Exception as e:
        logger.bind(tag=TAG).error(f"确认API调用异常: {e}")
        return False, None, f"调用异常: {str(e)}"


def initialize_temp_load_rate_state(conn):
    """初始化或获取温度负载率设置状态"""
    if not hasattr(conn, "temp_load_rate_setting"):
        conn.temp_load_rate_setting = {
            "temperature": None,         # 格式化的温度字符串，如"22℃"
            "temperature_raw": None,     # 原始温度数值
            "load_rate": None,           # 格式化的负载率字符串，如"90kw"
            "load_rate_raw": None,       # 原始负载率数值
            "stage": "init",            # 当前阶段：init/collecting/waiting_first_confirm/waiting_second_confirm/completed
            "api1_response": None,       # 保存接口1的响应
            "confirm_stage": 0,          # 确认阶段：0=未确认, 1=第一次确认完成, 2=第二次确认完成
        }
    return conn.temp_load_rate_setting


def clear_temp_load_rate_state(conn):
    """清除温度负载率设置状态"""
    if hasattr(conn, "temp_load_rate_setting"):
        delattr(conn, "temp_load_rate_setting")


@register_function(
    "get_temperature_load_rate",
    GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_temperature_load_rate(
    conn, temperature: str = None, load_rate: str = None, use_preset: bool = False, confirm: bool = True, cancel: bool = False
):
    """获取温度和负载率参数，集成API调用，支持授权确认"""
    try:
        # 初始化状态
        state = initialize_temp_load_rate_state(conn)
        api_base_url = get_api_base_url(conn)
        
        logger.bind(tag=TAG).debug(
            f"get_temperature_load_rate调用: temperature={temperature}, "
            f"load_rate={load_rate}, use_preset={use_preset}, confirm={confirm}, cancel={cancel}, "
            f"当前阶段={state['stage']}, confirm_stage={state['confirm_stage']}"
        )
        
        # ==================== 处理取消操作 ====================
        if cancel:
            logger.bind(tag=TAG).info(f"【取消操作】用户取消设置，当前阶段：{state['stage']}")
            
            # 如果在确认阶段，调用API取消
            if state["stage"] in ["waiting_first_confirm", "waiting_second_confirm"]:
                logger.bind(tag=TAG).info("【取消操作】调用API取消...")
                success, data, error = call_confirm_api(api_base_url, 0)
                if success:
                    logger.bind(tag=TAG).info("【取消操作】API取消成功")
                else:
                    logger.bind(tag=TAG).warning(f"【取消操作】API取消失败: {error}")
            
            clear_temp_load_rate_state(conn)
            logger.bind(tag=TAG).info("【取消操作】状态已清除，返回取消消息")
            return ActionResponse(
                action=Action.RESPONSE,
                result="已取消温度负载率设置",
                response="好的，已取消温度负载率设置",
            )
        
        # ==================== 阶段：参数收集 ====================
        # 更新温度
        if temperature is not None:
            logger.bind(tag=TAG).info(f"【参数收集】收到温度输入: {temperature}")
            temp_value, temp_formatted = parse_temperature(temperature)
            if temp_value is not None:
                # 验证温度
                is_valid, error_msg = validate_temperature(temp_value)
                if not is_valid:
                    logger.bind(tag=TAG).warning(f"【参数收集】温度验证失败: {error_msg}")
                    return ActionResponse(
                        action=Action.RESPONSE,
                        result=None,
                        response=error_msg,
                    )
                state["temperature_raw"] = temp_value
                state["temperature"] = temp_formatted
                logger.bind(tag=TAG).info(f"【参数收集】✅ 温度已更新: {temp_formatted} (原始值: {temp_value})")
            else:
                logger.bind(tag=TAG).warning(f"【参数收集】❌ 无法解析温度: {temperature}")
        
        # 更新负载率
        if load_rate is not None:
            logger.bind(tag=TAG).info(f"【参数收集】收到负载率输入: {load_rate}")
            load_rate_value, load_rate_formatted = parse_load_rate(load_rate)
            if load_rate_value is not None:
                # 验证负载率是否在合理范围内（0%-100%）
                is_valid, error_msg = validate_load_rate(load_rate_value)
                if not is_valid:
                    logger.bind(tag=TAG).warning(f"【参数收集】负载率验证失败: {error_msg}")
                    return ActionResponse(
                        action=Action.RESPONSE,
                        result=None,
                        response=error_msg,
                    )
                state["load_rate_raw"] = load_rate_value
                state["load_rate"] = load_rate_formatted
                logger.bind(tag=TAG).info(f"【参数收集】✅ 负载率已更新: {load_rate_formatted} (原始值: {load_rate_value})")
            else:
                logger.bind(tag=TAG).warning(f"【参数收集】❌ 无法解析负载率: {load_rate}")
        
        # 检查当前状态
        has_temperature = state["temperature"] is not None
        has_load_rate = state["load_rate"] is not None
        
        # ==================== 阶段：第二次确认（AI节能优化确认） ====================
        if state["stage"] == "waiting_second_confirm" and confirm:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第二次确认】用户确认使用AI节能优化")
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第二次确认】准备调用确认API（第二次）...")
            
            success, data, error = call_confirm_api(api_base_url, 1)
            
            if success:
                logger.bind(tag=TAG).info(f"【第二次确认】API调用成功，响应数据: {data}")
                
                if data.get("status") == "success" and data.get("stage") == 2:
                    # 第二次确认成功，完成流程
                    logger.bind(tag=TAG).info(f"【第二次确认】✅ 成功！AI寻优计算启动")
                    
                    state["confirm_stage"] = 2
                    state["stage"] = "completed"
                    
                    # 使用暖通建议的专业话术，根据实际参数动态构建消息
                    params_parts = []
                    if state.get("temperature"):
                        params_parts.append(f"温度：{state['temperature']}")
                    if state.get("load_rate"):
                        params_parts.append(f"负载：{state['load_rate']}")
                    
                    if params_parts:
                        params_info = "，".join(params_parts)
                        result_message = (
                            f"新工况已设置，{params_info}。\n"
                            f"AI寻优计算完毕，已锁定当前工况最优节能方案，新控制参数正在执行。"
                        )
                    else:
                        # 理论上不应该出现这种情况，但作为兜底
                        result_message = (
                            f"AI寻优计算完毕，已锁定当前工况最优节能方案，新控制参数正在执行。"
                        )
                    
                    logger.bind(tag=TAG).info("【第二次确认】流程完成，清除状态")
                    # 清除状态
                    clear_temp_load_rate_state(conn)
                    
                    logger.bind(tag=TAG).info("【第二次确认】返回完成消息")
                    return ActionResponse(
                        action=Action.RESPONSE,
                        result="AI寻优计算完毕，节能方案正在执行",
                        response=result_message,
                    )
                else:
                    # API返回异常
                    error_msg = f"确认失败: {error}"
                    logger.bind(tag=TAG).error(f"【第二次确认】❌ API返回异常: {error_msg}")
                    return ActionResponse(
                        action=Action.RESPONSE,
                        result=error_msg,
                        response=error_msg,
                    )
            else:
                # API调用失败
                logger.bind(tag=TAG).error(f"【第二次确认】❌ API调用失败: {error}")
                return ActionResponse(
                    action=Action.RESPONSE,
                    result=f"确认操作失败: {error}，请稍后重试",
                    response=f"确认操作失败: {error}，请稍后重试",
                )
        
        # ==================== 处理使用预设参数 ====================
        if use_preset:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【使用预设参数】用户请求使用预设推荐参数")
            logger.bind(tag=TAG).info("=" * 80)
            
            # 使用第一组预设参数（最常用的推荐值）
            preset = PRESET_PARAMS[0]
            preset_temp = preset["temperature"]
            preset_load = preset["load_rate"]
            
            logger.bind(tag=TAG).info(f"【使用预设参数】推荐参数：温度={preset_temp}℃, 负载率={preset_load}%")
            
            # 如果用户没有提供温度，使用预设温度
            if state["temperature"] is None:
                state["temperature_raw"] = preset_temp
                state["temperature"] = f"{preset_temp}℃"
                logger.bind(tag=TAG).info(f"【使用预设参数】✅ 温度已设置为预设值: {state['temperature']}")
            else:
                logger.bind(tag=TAG).info(f"【使用预设参数】温度已由用户提供: {state['temperature']}")
            
            # 如果用户没有提供负载率，使用预设负载率
            if state["load_rate"] is None:
                state["load_rate_raw"] = preset_load
                state["load_rate"] = f"{preset_load}%"
                logger.bind(tag=TAG).info(f"【使用预设参数】✅ 负载率已设置为预设值: {state['load_rate']}")
            else:
                logger.bind(tag=TAG).info(f"【使用预设参数】负载率已由用户提供: {state['load_rate']}")
            
            # 直接进入等待第一次确认状态
            state["stage"] = "waiting_first_confirm"
            
            logger.bind(tag=TAG).info("【使用预设参数】参数设置完成，请求用户确认")
            
            # 请求用户确认（优化：使用专业话术）
            confirm_message = (
                f"告知用户：新工况已设置，温度：{state['temperature']}，负载：{state['load_rate']}\n"
                f"然后简洁询问：是否启动AI寻优计算？（15字以内）\n"
                f"\n"
                f"【流程状态】waiting_first_confirm（需要用户授权）\n"
                f"用户说【确认/授权/同意/好的/是的】→ 立即调用 get_temperature_load_rate(confirm=True)\n"
                f"用户说【取消/拒绝/不要】→ 立即调用 get_temperature_load_rate(cancel=True)"
            )
            
            return ActionResponse(
                action=Action.REQLLM,
                result=confirm_message,
                response=None,
            )
        
        # ==================== 阶段：参数收集完成，请求第一次确认 ====================
        # 只要有至少一个参数就可以进入确认阶段（接口支持单参数）
        if (has_temperature or has_load_rate) and state["stage"] in ["init", "collecting"]:
            logger.bind(tag=TAG).info("=" * 80)
            if has_temperature and has_load_rate:
                logger.bind(tag=TAG).info(f"【参数收集完成】温度={state['temperature_raw']}℃, 负载率={state['load_rate_raw']}%")
            elif has_temperature:
                logger.bind(tag=TAG).info(f"【参数收集完成】温度={state['temperature_raw']}℃ (负载率未提供)")
            else:
                logger.bind(tag=TAG).info(f"【参数收集完成】负载率={state['load_rate_raw']}% (温度未提供)")
            logger.bind(tag=TAG).info("=" * 80)
            
            # 检查是否使用预设参数（避免超时）
            temp_raw = state.get('temperature_raw')
            load_raw = state.get('load_rate_raw')
            
            if temp_raw is not None and load_raw is not None:
                is_preset = any(
                    abs(temp_raw - p["temperature"]) < 0.01 and abs(load_raw - p["load_rate"]) < 0.01
                    for p in PRESET_PARAMS
                )
                if is_preset:
                    logger.bind(tag=TAG).info(f"【参数收集完成】✅ 使用预设参数，预期毫秒级响应")
                else:
                    logger.bind(tag=TAG).warning(f"【参数收集完成】⚠️ 非预设参数，可能需要10-30秒响应时间")
            else:
                logger.bind(tag=TAG).info(f"【参数收集完成】单参数设置，API支持")
            
            # 进入等待第一次确认状态
            state["stage"] = "waiting_first_confirm"
            
            logger.bind(tag=TAG).info("【参数收集完成】状态已更新为 waiting_first_confirm，请求用户确认参数")
            
            # 构建确认信息
            params_info = []
            if has_temperature:
                params_info.append(f"温度: {state['temperature']}")
            if has_load_rate:
                params_info.append(f"负载率: {state['load_rate']}")
            
            params_str = "\n".join(params_info)
            
            # 请求用户第一次确认（优化：使用专业话术）
            temp_str = state['temperature'] if has_temperature else "未设置"
            load_str = state['load_rate'] if has_load_rate else "未设置"
            
            confirm_message = (
                f"告知用户：新工况已设置，温度：{temp_str}，负载：{load_str}\n"
                f"然后简洁询问：是否启动AI寻优计算？（15字以内）\n"
                f"\n"
                f"【流程状态】waiting_first_confirm（需要用户授权）\n"
                f"用户说【确认/授权/同意/好的/是的】→ 立即调用 get_temperature_load_rate(confirm=True)\n"
                f"用户说【取消/拒绝/不要】→ 立即调用 get_temperature_load_rate(cancel=True)"
            )
            
            # return ActionResponse(
            #     action=Action.REQLLM,
            #     result=confirm_message,
            #     response=None,
            # )
        
        # ==================== 阶段：第一次确认（参数确认 + 调用API） ====================
        if state["stage"] == "waiting_first_confirm" and confirm:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第一次确认】用户确认参数")
            logger.bind(tag=TAG).info("=" * 80)
            
            temp_raw = state.get('temperature_raw')
            load_raw = state.get('load_rate_raw')
            
            # 步骤1: 调用API1（ASR接口），支持单参数或双参数
            if temp_raw is not None and load_raw is not None:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 温度={temp_raw}℃, 负载率={load_raw}%")
            elif temp_raw is not None:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 温度={temp_raw}℃ (仅温度)")
            else:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 负载率={load_raw}% (仅负载率)")
            
            success1, data1, error1 = call_asr_api(api_base_url, temperature=temp_raw, load_rate=load_raw)
            
            if not success1:
                # API1调用失败
                logger.bind(tag=TAG).error(f"【第一次确认-步骤1】❌ ASR API调用失败: {error1}")
                return ActionResponse(
                    action=Action.RESPONSE,
                    result=None,
                    response=f"参数设置失败: {error1}",
                )
            
            # API1调用成功
            logger.bind(tag=TAG).info(f"【第一次确认-步骤1】✅ ASR API调用成功")
            logger.bind(tag=TAG).info(f"【第一次确认-步骤1】响应数据: {data1}")
            
            message = data1.get("message", {})
            description = message.get("descripetion", "请确认是否设置参数")
            state["api1_response"] = data1
            
            # 检查是否是mock数据
            if data1.get("source") == "mock":
                mock_folder = data1.get("mock_folder", "")
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】使用Mock数据: {mock_folder}")
            
            # 步骤2: 立即调用API2（确认接口 - 第一次）
            logger.bind(tag=TAG).info("【第一次确认-步骤2】准备调用确认API（第一次）...")
            success2, data2, error2 = call_confirm_api(api_base_url, 1)
            
            if not success2:
                # API2调用失败
                logger.bind(tag=TAG).error(f"【第一次确认-步骤2】❌ 确认API调用失败: {error2}")
                return ActionResponse(
                    action=Action.RESPONSE,
                    result=f"确认操作失败: {error2}，请稍后重试",
                    response=f"确认操作失败: {error2}，请稍后重试",
                )
            
            # API2调用成功
            logger.bind(tag=TAG).info(f"【第一次确认-步骤2】✅ 确认API调用成功")
            logger.bind(tag=TAG).info(f"【第一次确认-步骤2】响应数据: {data2}")
            
            if data2.get("status") == "success" and data2.get("stage") == 1:
                # 第一次确认成功，进入第二次确认阶段
                description2 = data2.get("message", {}).get("descripetion", "已确认设置参数")
                logger.bind(tag=TAG).info(f"【第一次确认-步骤2】✅ 成功！{description2}")
                
                state["confirm_stage"] = 1
                state["stage"] = "waiting_second_confirm"
                
                logger.bind(tag=TAG).info("【第一次确认】两个API都调用成功，状态已更新为 waiting_second_confirm")
                logger.bind(tag=TAG).info("【第一次确认】请求用户第二次确认（AI节能优化）")
                
                prompt_message = (
                    f"询问：是否启动AI寻优计算？（15字以内）\n"
                    f"\n"
                    f"【流程状态】waiting_second_confirm（最后一步：需要用户授权启动AI寻优计算）\n"
                    f"用户说【确认/授权/同意/好的/是的】→ 立即调用 get_temperature_load_rate(confirm=True)\n"
                    f"用户说【取消/拒绝/不要】→ 立即调用 get_temperature_load_rate(cancel=True)"
                )
                
                return ActionResponse(
                    action=Action.REQLLM,
                    result=prompt_message,
                    response=None,
                )
            else:
                # API2返回异常
                error_msg = f"确认失败: {error2}"
                logger.bind(tag=TAG).error(f"【第一次确认-步骤2】❌ API返回异常: {error_msg}")
                return ActionResponse(
                    action=Action.RESPONSE,
                    result=error_msg,
                    response=error2,
                )

        # ==================== 已移除：参数收集中的反问环节 ====================
        # 优化说明：为了减少交互轮次，即使用户只提供单个参数，也直接进入确认阶段
        # 而不是询问"是否需要设置另一个参数"，这样可以确保用户只需2次确认即可完成流程
        # 
        # 原逻辑：用户只提供温度 → 询问是否需要负载率 → 用户确认参数 → 用户确认AI模式
        # 新逻辑：用户提供参数 → 直接确认参数 → 用户确认AI模式
        # 
        # API支持单参数或双参数，所以这个优化是可行的
        
        # 情况：两个参数都没有
        logger.bind(tag=TAG).info("【参数收集中】两个参数都没有，询问用户提供参数或使用预设值")
        state["stage"] = "collecting"
        initial_message = (
            "询问用户：请设置新工况参数，温度（℃）和负载率（%）。\n"
            "提示：不确定可说'用推荐值'。保持15字以内。\n"
            "\n"
            "【流程状态】collecting（参数收集阶段）\n"
            "⚠️ 重要：用户一旦提供参数，必须立即调用 get_temperature_load_rate 并传入参数！\n"
            "用户说【推荐值/帮我设置/默认】→ 调用 get_temperature_load_rate(use_preset=True)\n"
            "用户说【取消】→ 调用 get_temperature_load_rate(cancel=True)"
        )
        return ActionResponse(
            action=Action.REQLLM,
            result=initial_message,
            response=None,
        )
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"get_temperature_load_rate执行出错: {e}")
        import traceback
        logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
        # 清除状态，避免影响后续操作
        clear_temp_load_rate_state(conn)
        return ActionResponse(
            action=Action.ERROR,
            result=str(e),
            response="抱歉，设置温度负载率时出现错误，请稍后再试",
        )

