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
            "用于设置温度和/或负载率参数，并通过两轮确认交互启动AI节能优化。"
            "用户可以：①只设置温度；②只设置负载率；③同时设置温度和负载率；④使用预设推荐值。"
            "当用户说'设置温度'、'调整负载率'、'温度负载率设置'、'节能优化'、'确认'、'取消'等时调用此函数。"
            "系统支持灵活的参数设置，不强制要求同时提供两个参数，并通过两轮确认（参数确认、AI推荐模式确认）来完成设置。"
            "如果用户不知道设什么值，或说'随便设置'、'帮我设置'、'用推荐值'、'默认值'等，则使用预设的推荐参数。"
            "注意：负载率的单位是千瓦(kw)，不是百分比。"
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
                    "description": "负载率值，单位是千瓦kw（如90kw、95.6千瓦、90）。如果用户没有提供则为空",
                },
                "use_preset": {
                    "type": "boolean",
                    "description": "用户是否希望使用预设的推荐参数。当用户说'随便设置'、'帮我设置'、'用推荐值'、'默认值'、'不知道设什么'等时为true",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "用户是否确认当前操作。当用户说'确认'、'是的'、'对的'、'好的'、'没错'等表示同意时为true",
                },
                "cancel": {
                    "type": "boolean",
                    "description": "用户是否取消设置。当用户说'取消'、'不要了'、'算了'等表示放弃时为true",
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
    """从字符串中提取负载率数值（实际为kw千瓦值）
    
    支持格式：
    - 90、90.5、90kw、90千瓦
    """
    if load_rate_str is None:
        return None, None
    
    # 移除可能的单位，提取数字
    # 匹配：90、90.5、90kw、90千瓦、90 kw等
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kw|千瓦|KW)?', str(load_rate_str), re.IGNORECASE)
    if match:
        load_rate_value = float(match.group(1))
        load_rate_formatted = f"{load_rate_value}kw"
        return load_rate_value, load_rate_formatted
    return None, None


def validate_temperature(temp_value):
    """验证温度是否在合理范围内"""
    if temp_value is None:
        return True, None
    if temp_value < -10 or temp_value > 50:
        return False, f"温度{temp_value}℃超出合理范围（-10℃~50℃），请重新输入"
    return True, None


def validate_load_rate(load_rate_value):
    """验证负载率（kw值）是否在合理范围内"""
    if load_rate_value is None:
        return True, None
    if load_rate_value < 0 or load_rate_value > 200:
        return False, f"负载率{load_rate_value}kw超出合理范围（0~200kw），请重新输入"
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
            error_msg = data.get("error", "未知错误")
            code = data.get("code", 0)
            if code == 409:
                return False, data, "优化任务正在进行中，请稍后再试"
            return False, data, error_msg
        else:
            return False, data, "接口返回状态异常"
            
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
            return True, data, None
        elif data.get("status") == "canceled":
            return True, data, None  # 取消也算成功
        elif data.get("status") == "fail":
            error_msg = data.get("message", "未知错误")
            return False, data, error_msg
        else:
            return False, data, "接口返回状态异常"
            
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
    conn, temperature: str = None, load_rate: str = None, use_preset: bool = False, confirm: bool = False, cancel: bool = False
):
    """获取温度和负载率参数，集成API调用，支持递进式两轮确认"""
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
        
        # ==================== 处理使用预设参数 ====================
        if use_preset:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【使用预设参数】用户请求使用预设推荐参数")
            logger.bind(tag=TAG).info("=" * 80)
            
            # 使用第一组预设参数（最常用的推荐值）
            preset = PRESET_PARAMS[0]
            preset_temp = preset["temperature"]
            preset_load = preset["load_rate"]
            
            logger.bind(tag=TAG).info(f"【使用预设参数】推荐参数：温度={preset_temp}℃, 负载率={preset_load}kw")
            
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
                state["load_rate"] = f"{preset_load}kw"
                logger.bind(tag=TAG).info(f"【使用预设参数】✅ 负载率已设置为预设值: {state['load_rate']}")
            else:
                logger.bind(tag=TAG).info(f"【使用预设参数】负载率已由用户提供: {state['load_rate']}")
            
            # 直接进入等待第一次确认状态
            state["stage"] = "waiting_first_confirm"
            
            logger.bind(tag=TAG).info("【使用预设参数】参数设置完成，请求用户确认")
            
            # 请求用户确认
            confirm_message = (
                f"根据以下信息回复用户：\n"
                f"已为您设置推荐参数：\n"
                f"温度: {state['temperature']}\n"
                f"负载率: {state['load_rate']}\n"
                f"(请用自然语言告知用户已使用推荐参数，并询问用户是否确认这些参数)\n"
                f"\n"
                f"【重要提醒】当前正在执行【温度/负载率设置】流程，已进行到 waiting_first_confirm 阶段。\n"
                f"若用户回复【确认/是的/好/可以/对的/没错/OK】等肯定词，请必须立即调用：\n"
                f"get_temperature_load_rate(confirm=True)\n"
                f"若用户回复【取消/算了/不要/不用了】等否定词，请必须立即调用：\n"
                f"get_temperature_load_rate(cancel=True)"
            )
            
            return ActionResponse(
                action=Action.REQLLM,
                result=confirm_message,
                response=None,
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
                        action=Action.REQLLM,
                        result=error_msg,
                        response=None,
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
                # 注意：负载率实际是kw值，不做百分比验证，改为合理范围验证
                # 这里假设负载率在0-200kw之间
                if load_rate_value < 0 or load_rate_value > 200:
                    logger.bind(tag=TAG).warning(f"【参数收集】负载率验证失败: 超出范围")
                    return ActionResponse(
                        action=Action.REQLLM,
                        result=f"负载率{load_rate_value}kw超出合理范围（0~200kw），请重新输入",
                        response=None,
                    )
                state["load_rate_raw"] = load_rate_value
                state["load_rate"] = f"{load_rate_value}kw"
                logger.bind(tag=TAG).info(f"【参数收集】✅ 负载率已更新: {load_rate_value}kw")
            else:
                logger.bind(tag=TAG).warning(f"【参数收集】❌ 无法解析负载率: {load_rate}")
        
        # 检查当前状态
        has_temperature = state["temperature"] is not None
        has_load_rate = state["load_rate"] is not None
        
        # ==================== 阶段：第二次确认（AI推荐模式确认） ====================
        if state["stage"] == "waiting_second_confirm" and confirm:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第二次确认】用户确认使用AI推荐模式")
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第二次确认】准备调用确认API（第二次）...")
            
            success, data, error = call_confirm_api(api_base_url, 1)
            
            if success:
                logger.bind(tag=TAG).info(f"【第二次确认】API调用成功，响应数据: {data}")
                
                if data.get("status") == "success" and data.get("stage") == 2:
                    # 第二次确认成功，完成流程
                    description = data.get("message", {}).get("descripetion", "已确认使用AI推荐模式，开始AI节能优化")
                    logger.bind(tag=TAG).info(f"【第二次确认】✅ 成功！{description}")
                    
                    state["confirm_stage"] = 2
                    state["stage"] = "completed"
                    
                    result_message = (
                        f"✅ {description}\n"
                        f"温度: {state['temperature']}\n"
                        f"负载率: {state['load_rate']}\n"
                        f"系统已启动AI节能优化流程"
                    )
                    
                    logger.bind(tag=TAG).info("【第二次确认】流程完成，清除状态")
                    # 清除状态
                    clear_temp_load_rate_state(conn)
                    
                    logger.bind(tag=TAG).info("【第二次确认】返回完成消息")
                    return ActionResponse(
                        action=Action.RESPONSE,
                        result="AI节能优化已启动",
                        response=result_message,
                    )
                else:
                    # API返回异常
                    error_msg = f"确认失败: {data}"
                    logger.bind(tag=TAG).error(f"【第二次确认】❌ API返回异常: {error_msg}")
                    return ActionResponse(
                        action=Action.REQLLM,
                        result=error_msg,
                        response=None,
                    )
            else:
                # API调用失败
                logger.bind(tag=TAG).error(f"【第二次确认】❌ API调用失败: {error}")
                return ActionResponse(
                    action=Action.REQLLM,
                    result=f"确认操作失败: {error}，请稍后重试",
                    response=None,
                )
        
        # ==================== 阶段：参数收集完成，请求第一次确认 ====================
        # 只要有至少一个参数就可以进入确认阶段（接口支持单参数）
        if (has_temperature or has_load_rate) and state["stage"] in ["init", "collecting"]:
            logger.bind(tag=TAG).info("=" * 80)
            if has_temperature and has_load_rate:
                logger.bind(tag=TAG).info(f"【参数收集完成】温度={state['temperature_raw']}℃, 负载率={state['load_rate_raw']}kw")
            elif has_temperature:
                logger.bind(tag=TAG).info(f"【参数收集完成】温度={state['temperature_raw']}℃ (负载率未提供)")
            else:
                logger.bind(tag=TAG).info(f"【参数收集完成】负载率={state['load_rate_raw']}kw (温度未提供)")
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
            
            # 请求用户第一次确认
            confirm_message = (
                f"根据以下信息回复用户：\n"
                f"{params_str}\n"
                f"(请用自然语言向用户确认这些参数是否正确，并提示用户可以说'确认'完成设置)\n"
                f"\n"
                f"【重要提醒】当前正在执行【温度/负载率设置】流程，已进行到 waiting_first_confirm 阶段。\n"
                f"若用户回复【确认/是的/好/可以/对的/没错/OK】等肯定词，请必须立即调用：\n"
                f"get_temperature_load_rate(confirm=True)\n"
                f"若用户回复【取消/算了/不要/不用了】等否定词，请必须立即调用：\n"
                f"get_temperature_load_rate(cancel=True)"
            )
            
            return ActionResponse(
                action=Action.REQLLM,
                result=confirm_message,
                response=None,
            )
        
        # ==================== 阶段：第一次确认（参数确认 + 调用API） ====================
        if state["stage"] == "waiting_first_confirm" and confirm:
            logger.bind(tag=TAG).info("=" * 80)
            logger.bind(tag=TAG).info("【第一次确认】用户确认参数")
            logger.bind(tag=TAG).info("=" * 80)
            
            temp_raw = state.get('temperature_raw')
            load_raw = state.get('load_rate_raw')
            
            # 步骤1: 调用API1（ASR接口），支持单参数或双参数
            if temp_raw is not None and load_raw is not None:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 温度={temp_raw}℃, 负载率={load_raw}kw")
            elif temp_raw is not None:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 温度={temp_raw}℃ (仅温度)")
            else:
                logger.bind(tag=TAG).info(f"【第一次确认-步骤1】准备调用ASR API: 负载率={load_raw}kw (仅负载率)")
            
            success1, data1, error1 = call_asr_api(api_base_url, temperature=temp_raw, load_rate=load_raw)
            
            if not success1:
                # API1调用失败
                logger.bind(tag=TAG).error(f"【第一次确认-步骤1】❌ ASR API调用失败: {error1}")
                return ActionResponse(
                    action=Action.REQLLM,
                    result=f"参数设置失败: {error1}",
                    response=None,
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
                    action=Action.REQLLM,
                    result=f"确认操作失败: {error2}，请稍后重试",
                    response=None,
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
                logger.bind(tag=TAG).info("【第一次确认】请求用户第二次确认（AI推荐模式）")
                
                prompt_message = (
                    f"根据以下信息回复用户：\n"
                    f"第一次确认成功: {description2}\n"
                    f"(请友好地询问用户是否使用AI推荐模式进行节能优化，并提示用户可以说'确认'或'好的'来同意)\n"
                    f"\n"
                    f"【重要提醒】当前正在执行【温度/负载率设置】流程，已进行到 waiting_second_confirm 阶段（第二次确认）。\n"
                    f"若用户回复【确认/是的/好/可以/对的/没错/OK】等肯定词，请必须立即调用：\n"
                    f"get_temperature_load_rate(confirm=True)\n"
                    f"若用户回复【取消/算了/不要/不用了】等否定词，请必须立即调用：\n"
                    f"get_temperature_load_rate(cancel=True)"
                )
                
                return ActionResponse(
                    action=Action.REQLLM,
                    result=prompt_message,
                    response=None,
                )
            else:
                # API2返回异常
                error_msg = f"确认失败: {data2}"
                logger.bind(tag=TAG).error(f"【第一次确认-步骤2】❌ API返回异常: {error_msg}")
                return ActionResponse(
                    action=Action.REQLLM,
                    result=error_msg,
                    response=None,
                )

        # ==================== 阶段：参数收集中（单参数情况） ====================
        # 注意：现在API支持单参数，所以有一个参数就已经可以进入确认阶段了
        # 这里只是给用户提供继续添加参数的机会，但不强制要求
        
        # 情况：只有温度，询问是否需要设置负载率
        if has_temperature and not has_load_rate:
            logger.bind(tag=TAG).info(f"【参数收集中】只有温度({state['temperature']})，询问用户是否需要设置负载率")
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"温度已设置为: {state['temperature']}\n"
                f"(请用自然、友好的方式告诉用户温度已记录。"
                f"询问用户：是否还需要设置负载率？也可以直接确认当前参数。"
                f"提示：如果不确定负载率设什么值，可以说'使用推荐值'或'帮我设置'；如果只设置温度，可以直接说'确认')\n"
                f"\n"
                f"【提醒】当前正在执行【温度/负载率设置】流程，collecting 阶段（收集参数中）。\n"
                f"若用户说【使用推荐值/帮我设置/随便/默认值】等，请调用：get_temperature_load_rate(use_preset=True)\n"
                f"若用户说【确认/好的】等表示只设置温度，系统会自动进入确认流程\n"
                f"若用户说【取消/不要了】等，请调用：get_temperature_load_rate(cancel=True)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=prompt_message,
                response=None,
            )
        
        # 情况：只有负载率，询问是否需要设置温度
        if has_load_rate and not has_temperature:
            logger.bind(tag=TAG).info(f"【参数收集中】只有负载率({state['load_rate']})，询问用户是否需要设置温度")
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"负载率已设置为: {state['load_rate']}\n"
                f"(请用自然、友好的方式告诉用户负载率已记录。"
                f"询问用户：是否还需要设置温度？也可以直接确认当前参数。"
                f"提示：如果不确定温度设什么值，可以说'使用推荐值'或'帮我设置'；如果只设置负载率，可以直接说'确认')\n"
                f"\n"
                f"【提醒】当前正在执行【温度/负载率设置】流程，collecting 阶段（收集参数中）。\n"
                f"若用户说【使用推荐值/帮我设置/随便/默认值】等，请调用：get_temperature_load_rate(use_preset=True)\n"
                f"若用户说【确认/好的】等表示只设置负载率，系统会自动进入确认流程\n"
                f"若用户说【取消/不要了】等，请调用：get_temperature_load_rate(cancel=True)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=prompt_message,
                response=None,
            )
        
        # 情况：两个参数都没有
        logger.bind(tag=TAG).info("【参数收集中】两个参数都没有，询问用户提供参数或使用预设值")
        state["stage"] = "collecting"
        initial_message = (
            "根据以下情况回复用户：\n"
            "用户想要设置温度和负载率参数，但还未提供具体数值\n"
            "(请用自然、友好的方式询问用户想要设置的温度（摄氏度）和负载率（千瓦kw），可以一起提供或分别提供。"
            "同时提示用户：如果不确定设什么值，可以说'使用推荐值'或'帮我设置'，系统将使用预设的推荐参数)\n"
            "\n"
            "【提醒】当前正在执行【温度/负载率设置】流程，collecting 阶段（收集参数中）。\n"
            "若用户说【使用推荐值/帮我设置/随便/默认值】等，请调用：get_temperature_load_rate(use_preset=True)\n"
            "若用户说【取消/不要了】等，请调用：get_temperature_load_rate(cancel=True)"
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

