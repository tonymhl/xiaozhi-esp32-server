import re
import json
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_temperature_load_rate",
        "description": (
            "用于设置或获取温度和负载率参数。"
            "用户可以一次性提供温度和负载率，也可以分步提供。"
            "当用户说'设置温度'、'调整负载率'、'温度负载率设置'等时调用此函数。"
            "系统会引导用户提供完整参数并确认。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "string",
                    "description": "温度值，可以是数字加单位（如22度、22℃、二十二度）。如果用户没有提供则为空",
                },
                "load_rate": {
                    "type": "string",
                    "description": "负载率值，可以是数字或百分比（如60%、60）。如果用户没有提供则为空",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "用户是否确认这组参数。当用户说'确认'、'是的'、'对的'、'没错'等表示同意时为true",
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
    """从字符串中提取负载率数值
    
    支持格式：
    - 60%、60
    - 百分之六十（需要LLM已转换为数字）
    """
    if load_rate_str is None:
        return None, None
    
    # 尝试匹配负载率
    match = re.search(r'(\d+(?:\.\d+)?)\s*%?', str(load_rate_str))
    if match:
        load_rate_value = float(match.group(1))
        # 如果数值在0-1之间，认为是小数形式的百分比
        if 0 < load_rate_value <= 1:
            load_rate_value = load_rate_value * 100
        load_rate_formatted = f"{int(load_rate_value)}%"
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
    """验证负载率是否在合理范围内"""
    if load_rate_value is None:
        return True, None
    if load_rate_value < 0 or load_rate_value > 100:
        return False, f"负载率{load_rate_value}%超出合理范围（0%~100%），请重新输入"
    return True, None


def initialize_temp_load_rate_state(conn):
    """初始化或获取温度负载率设置状态"""
    if not hasattr(conn, "temp_load_rate_setting"):
        conn.temp_load_rate_setting = {
            "temperature": None,         # 格式化的温度字符串，如"22℃"
            "temperature_raw": None,     # 原始温度数值
            "load_rate": None,           # 格式化的负载率字符串，如"60%"
            "load_rate_raw": None,       # 原始负载率数值
            "stage": "init",            # 当前阶段：init/collecting/confirming
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
    conn, temperature: str = None, load_rate: str = None, confirm: bool = False, cancel: bool = False
):
    """获取温度和负载率参数，支持多轮对话交互"""
    try:
        # 初始化状态
        state = initialize_temp_load_rate_state(conn)
        
        logger.bind(tag=TAG).debug(
            f"get_temperature_load_rate调用: temperature={temperature}, "
            f"load_rate={load_rate}, confirm={confirm}, cancel={cancel}"
        )
        
        # 处理取消操作
        if cancel:
            clear_temp_load_rate_state(conn)
            logger.bind(tag=TAG).info("用户取消了温度负载率设置")
            return ActionResponse(
                action=Action.RESPONSE,
                result="已取消温度负载率设置",
                response="好的，已取消温度负载率设置",
            )
        
        # 更新温度
        if temperature is not None:
            temp_value, temp_formatted = parse_temperature(temperature)
            if temp_value is not None:
                # 验证温度
                is_valid, error_msg = validate_temperature(temp_value)
                if not is_valid:
                    return ActionResponse(
                        action=Action.REQLLM,
                        result=error_msg,
                        response=None,
                    )
                state["temperature_raw"] = temp_value
                state["temperature"] = temp_formatted
                logger.bind(tag=TAG).info(f"温度已更新: {temp_formatted}")
            else:
                logger.bind(tag=TAG).warning(f"无法解析温度: {temperature}")
        
        # 更新负载率
        if load_rate is not None:
            load_rate_value, load_rate_formatted = parse_load_rate(load_rate)
            if load_rate_value is not None:
                # 验证负载率
                is_valid, error_msg = validate_load_rate(load_rate_value)
                if not is_valid:
                    return ActionResponse(
                        action=Action.REQLLM,
                        result=error_msg,
                        response=None,
                    )
                state["load_rate_raw"] = load_rate_value
                state["load_rate"] = load_rate_formatted
                logger.bind(tag=TAG).info(f"负载率已更新: {load_rate_formatted}")
            else:
                logger.bind(tag=TAG).warning(f"无法解析负载率: {load_rate}")
        
        # 检查当前状态
        has_temperature = state["temperature"] is not None
        has_load_rate = state["load_rate"] is not None
        
        # 情况1：用户确认，且已有完整参数
        if confirm and has_temperature and has_load_rate:
            result_json = {
                "temperature": state["temperature"],
                "load_rate": state["load_rate"],
                "confirm": True,
            }
            logger.bind(tag=TAG).info(f"温度负载率设置完成: {result_json}")
            
            # 清除状态
            clear_temp_load_rate_state(conn)
            
            # 返回JSON结果
            return ActionResponse(
                action=Action.RESPONSE,
                result="温度负载率设置成功",
                response=json.dumps(result_json, ensure_ascii=False),
            )
        
        # 情况2：已有完整参数，但用户未确认
        if has_temperature and has_load_rate:
            if state["stage"] != "confirming":
                state["stage"] = "confirming"
            
            confirm_message = (
                f"根据以下参数回复用户：\n"
                f"温度: {state['temperature']}\n"
                f"负载率: {state['load_rate']}\n"
                f"(请用自然语言向用户确认这些参数是否正确，并提示用户可以说'确认'完成设置，或者修改参数)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=confirm_message,
                response=None,
            )
        
        # 情况3：只有温度，缺少负载率
        if has_temperature and not has_load_rate:
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"温度已设置为: {state['temperature']}\n"
                f"(请用自然、友好的方式告诉用户温度已记录，并询问负载率值)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=prompt_message,
                response=None,
            )
        
        # 情况4：只有负载率，缺少温度
        if has_load_rate and not has_temperature:
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"负载率已设置为: {state['load_rate']}\n"
                f"(请用自然、友好的方式告诉用户负载率已记录，并询问温度值)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=prompt_message,
                response=None,
            )
        
        # 情况5：两个参数都没有
        state["stage"] = "collecting"
        initial_message = (
            "根据以下情况回复用户：\n"
            "用户想要设置温度负载率参数，但还未提供具体数值\n"
            "(请用自然、友好的方式询问用户想要设置的温度和负载率值，可以一起提供或分别提供)"
        )
        return ActionResponse(
            action=Action.REQLLM,
            result=initial_message,
            response=None,
        )
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"get_temperature_load_rate执行出错: {e}")
        # 清除状态，避免影响后续操作
        clear_temp_load_rate_state(conn)
        return ActionResponse(
            action=Action.ERROR,
            result=str(e),
            response="抱歉，设置温度负载率时出现错误，请稍后再试",
        )

