import re
import json
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_temperature_humidity",
        "description": (
            "用于设置或获取温度和湿度参数。"
            "用户可以一次性提供温度和湿度，也可以分步提供。"
            "当用户说'设置温度'、'调整湿度'、'温湿度设置'等时调用此函数。"
            "系统会引导用户提供完整参数并确认。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "string",
                    "description": "温度值，可以是数字加单位（如22度、22℃、二十二度）。如果用户没有提供则为空",
                },
                "humidity": {
                    "type": "string",
                    "description": "湿度值，可以是数字或百分比（如60%、60）。如果用户没有提供则为空",
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


def parse_humidity(humidity_str):
    """从字符串中提取湿度数值

    支持格式：
    - 60%、60
    - 百分之六十（需要LLM已转换为数字）
    """
    if humidity_str is None:
        return None, None

    # 尝试匹配湿度
    match = re.search(r'(\d+(?:\.\d+)?)\s*%?', str(humidity_str))
    if match:
        humidity_value = float(match.group(1))
        # 如果数值在0-1之间，认为是小数形式的百分比
        if 0 < humidity_value <= 1:
            humidity_value = humidity_value * 100
        humidity_formatted = f"{int(humidity_value)}%"
        return humidity_value, humidity_formatted
    return None, None


def validate_temperature(temp_value):
    """验证温度是否在合理范围内"""
    if temp_value is None:
        return True, None
    if temp_value < -10 or temp_value > 50:
        return False, f"温度{temp_value}℃超出合理范围（-10℃~50℃），请重新输入"
    return True, None


def validate_humidity(humidity_value):
    """验证湿度是否在合理范围内"""
    if humidity_value is None:
        return True, None
    if humidity_value < 0 or humidity_value > 100:
        return False, f"湿度{humidity_value}%超出合理范围（0%~100%），请重新输入"
    return True, None


def initialize_temp_humidity_state(conn):
    """初始化或获取温湿度设置状态"""
    if not hasattr(conn, "temp_humidity_setting"):
        conn.temp_humidity_setting = {
            "temperature": None,         # 格式化的温度字符串，如"22℃"
            "temperature_raw": None,     # 原始温度数值
            "humidity": None,            # 格式化的湿度字符串，如"60%"
            "humidity_raw": None,        # 原始湿度数值
            "stage": "init",            # 当前阶段：init/collecting/confirming
        }
    return conn.temp_humidity_setting


def clear_temp_humidity_state(conn):
    """清除温湿度设置状态"""
    if hasattr(conn, "temp_humidity_setting"):
        delattr(conn, "temp_humidity_setting")


@register_function(
    "get_temperature_humidity",
    GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_temperature_humidity(
    conn, temperature: str = None, humidity: str = None, confirm: bool = False, cancel: bool = False
):
    """获取温度和湿度参数，支持多轮对话交互"""
    try:
        # 初始化状态
        state = initialize_temp_humidity_state(conn)

        logger.bind(tag=TAG).debug(
            f"get_temperature_humidity调用: temperature={temperature}, "
            f"humidity={humidity}, confirm={confirm}, cancel={cancel}"
        )

        # 处理取消操作
        if cancel:
            clear_temp_humidity_state(conn)
            logger.bind(tag=TAG).info("用户取消了温湿度设置")
            return ActionResponse(
                action=Action.RESPONSE,
                result="已取消温湿度设置",
                response="好的，已取消温湿度设置",
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

        # 更新湿度
        if humidity is not None:
            humidity_value, humidity_formatted = parse_humidity(humidity)
            if humidity_value is not None:
                # 验证湿度
                is_valid, error_msg = validate_humidity(humidity_value)
                if not is_valid:
                    return ActionResponse(
                        action=Action.REQLLM,
                        result=error_msg,
                        response=None,
                    )
                state["humidity_raw"] = humidity_value
                state["humidity"] = humidity_formatted
                logger.bind(tag=TAG).info(f"湿度已更新: {humidity_formatted}")
            else:
                logger.bind(tag=TAG).warning(f"无法解析湿度: {humidity}")

        # 检查当前状态
        has_temperature = state["temperature"] is not None
        has_humidity = state["humidity"] is not None

        # 情况1：用户确认，且已有完整参数
        if confirm and has_temperature and has_humidity:
            result_json = {
                "temperature": state["temperature"],
                "humidity": state["humidity"],
                "confirm": True,
            }
            logger.bind(tag=TAG).info(f"温湿度设置完成: {result_json}")

            # 清除状态
            clear_temp_humidity_state(conn)

            # 返回JSON结果
            return ActionResponse(
                action=Action.RESPONSE,
                result="温湿度设置成功",
                response=json.dumps(result_json, ensure_ascii=False),
            )

        # 情况2：已有完整参数，但用户未确认
        if has_temperature and has_humidity:
            if state["stage"] != "confirming":
                state["stage"] = "confirming"

            confirm_message = (
                f"根据以下参数回复用户：\n"
                f"温度: {state['temperature']}\n"
                f"湿度: {state['humidity']}\n"
                f"(请用自然语言向用户确认这些参数是否正确，并提示用户可以说'确认'完成设置，或者修改参数)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=confirm_message,
                response=None,
            )

        # 情况3：只有温度，缺少湿度
        if has_temperature and not has_humidity:
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"温度已设置为: {state['temperature']}\n"
                f"(请用自然、友好的方式告诉用户温度已记录，并询问湿度值)"
            )
            return ActionResponse(
                action=Action.REQLLM,
                result=prompt_message,
                response=None,
            )

        # 情况4：只有湿度，缺少温度
        if has_humidity and not has_temperature:
            state["stage"] = "collecting"
            prompt_message = (
                f"根据以下信息回复用户：\n"
                f"湿度已设置为: {state['humidity']}\n"
                f"(请用自然、友好的方式告诉用户湿度已记录，并询问温度值)"
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
            "用户想要设置温湿度参数，但还未提供具体数值\n"
            "(请用自然、友好的方式询问用户想要设置的温度和湿度值，可以一起提供或分别提供)"
        )
        return ActionResponse(
            action=Action.REQLLM,
            result=initial_message,
            response=None,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"get_temperature_humidity执行出错: {e}")
        # 清除状态，避免影响后续操作
        clear_temp_humidity_state(conn)
        return ActionResponse(
            action=Action.ERROR,
            result=str(e),
            response="抱歉，设置温湿度时出现错误，请稍后再试",
        )

