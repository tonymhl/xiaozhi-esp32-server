"""
get_temperature_humidity 函数单元测试

使用方法：
    python -m pytest test_get_temperature_humidity.py -v
或直接运行:
    python test_get_temperature_humidity.py
"""

import unittest
import json
from unittest.mock import Mock
from plugins_func.functions.get_temperature_humidity import (
    parse_temperature,
    parse_humidity,
    validate_temperature,
    validate_humidity,
    initialize_temp_humidity_state,
    clear_temp_humidity_state,
    get_temperature_humidity,
)
from plugins_func.register import Action


class TestTemperatureHumidityParsing(unittest.TestCase):
    """测试参数解析功能"""

    def test_parse_temperature_with_degree(self):
        """测试解析带'度'的温度"""
        value, formatted = parse_temperature("22度")
        self.assertEqual(value, 22.0)
        self.assertEqual(formatted, "22.0℃")

    def test_parse_temperature_with_celsius(self):
        """测试解析带'℃'的温度"""
        value, formatted = parse_temperature("22℃")
        self.assertEqual(value, 22.0)
        self.assertEqual(formatted, "22.0℃")

    def test_parse_temperature_with_decimal(self):
        """测试解析小数温度"""
        value, formatted = parse_temperature("22.5度")
        self.assertEqual(value, 22.5)
        self.assertEqual(formatted, "22.5℃")

    def test_parse_temperature_negative(self):
        """测试解析负温度"""
        value, formatted = parse_temperature("-5度")
        self.assertEqual(value, -5.0)
        self.assertEqual(formatted, "-5.0℃")

    def test_parse_temperature_plain_number(self):
        """测试解析纯数字温度"""
        value, formatted = parse_temperature("25")
        self.assertEqual(value, 25.0)
        self.assertEqual(formatted, "25.0℃")

    def test_parse_temperature_none(self):
        """测试解析None"""
        value, formatted = parse_temperature(None)
        self.assertIsNone(value)
        self.assertIsNone(formatted)

    def test_parse_humidity_with_percent(self):
        """测试解析带百分号的湿度"""
        value, formatted = parse_humidity("60%")
        self.assertEqual(value, 60.0)
        self.assertEqual(formatted, "60%")

    def test_parse_humidity_plain_number(self):
        """测试解析纯数字湿度"""
        value, formatted = parse_humidity("60")
        self.assertEqual(value, 60.0)
        self.assertEqual(formatted, "60%")

    def test_parse_humidity_decimal(self):
        """测试解析小数形式的湿度（0-1之间）"""
        value, formatted = parse_humidity("0.6")
        self.assertEqual(value, 60.0)
        self.assertEqual(formatted, "60%")

    def test_parse_humidity_none(self):
        """测试解析None"""
        value, formatted = parse_humidity(None)
        self.assertIsNone(value)
        self.assertIsNone(formatted)


class TestParameterValidation(unittest.TestCase):
    """测试参数验证功能"""

    def test_validate_temperature_valid(self):
        """测试验证有效温度"""
        is_valid, msg = validate_temperature(22.0)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_validate_temperature_too_high(self):
        """测试验证过高温度"""
        is_valid, msg = validate_temperature(100.0)
        self.assertFalse(is_valid)
        self.assertIn("超出合理范围", msg)

    def test_validate_temperature_too_low(self):
        """测试验证过低温度"""
        is_valid, msg = validate_temperature(-20.0)
        self.assertFalse(is_valid)
        self.assertIn("超出合理范围", msg)

    def test_validate_temperature_none(self):
        """测试验证None温度"""
        is_valid, msg = validate_temperature(None)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_validate_humidity_valid(self):
        """测试验证有效湿度"""
        is_valid, msg = validate_humidity(60.0)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_validate_humidity_too_high(self):
        """测试验证过高湿度"""
        is_valid, msg = validate_humidity(150.0)
        self.assertFalse(is_valid)
        self.assertIn("超出合理范围", msg)

    def test_validate_humidity_too_low(self):
        """测试验证过低湿度"""
        is_valid, msg = validate_humidity(-10.0)
        self.assertFalse(is_valid)
        self.assertIn("超出合理范围", msg)


class TestStateManagement(unittest.TestCase):
    """测试状态管理功能"""

    def setUp(self):
        """每个测试前创建mock连接对象"""
        self.mock_conn = Mock()

    def test_initialize_state(self):
        """测试初始化状态"""
        state = initialize_temp_humidity_state(self.mock_conn)
        self.assertIsNotNone(state)
        self.assertIsNone(state["temperature"])
        self.assertIsNone(state["humidity"])
        self.assertEqual(state["stage"], "init")

    def test_initialize_state_already_exists(self):
        """测试状态已存在时不会覆盖"""
        # 先设置一个状态
        self.mock_conn.temp_humidity_setting = {
            "temperature": "22℃",
            "temperature_raw": 22.0,
            "humidity": "60%",
            "humidity_raw": 60.0,
            "stage": "confirming",
        }
        # 再次初始化
        state = initialize_temp_humidity_state(self.mock_conn)
        # 应该返回现有状态
        self.assertEqual(state["temperature"], "22℃")
        self.assertEqual(state["stage"], "confirming")

    def test_clear_state(self):
        """测试清除状态"""
        self.mock_conn.temp_humidity_setting = {"test": "data"}
        clear_temp_humidity_state(self.mock_conn)
        self.assertFalse(hasattr(self.mock_conn, "temp_humidity_setting"))


class TestGetTemperatureHumidityFunction(unittest.TestCase):
    """测试主函数功能"""

    def setUp(self):
        """每个测试前创建mock连接对象"""
        self.mock_conn = Mock()
        # 清理状态
        if hasattr(self.mock_conn, "temp_humidity_setting"):
            delattr(self.mock_conn, "temp_humidity_setting")

    def test_cancel_operation(self):
        """测试取消操作"""
        response = get_temperature_humidity(
            self.mock_conn, cancel=True
        )
        self.assertEqual(response.action, Action.RESPONSE)
        self.assertIn("取消", response.response)

    def test_set_temperature_only(self):
        """测试只设置温度"""
        response = get_temperature_humidity(
            self.mock_conn, temperature="22度"
        )
        self.assertEqual(response.action, Action.REQLLM)
        self.assertIn("22℃", response.result)
        # 验证状态已保存
        self.assertEqual(self.mock_conn.temp_humidity_setting["temperature"], "22.0℃")

    def test_set_humidity_only(self):
        """测试只设置湿度"""
        response = get_temperature_humidity(
            self.mock_conn, humidity="60%"
        )
        self.assertEqual(response.action, Action.REQLLM)
        self.assertIn("60%", response.result)
        # 验证状态已保存
        self.assertEqual(self.mock_conn.temp_humidity_setting["humidity"], "60%")

    def test_set_both_without_confirm(self):
        """测试同时设置温度和湿度但未确认"""
        response = get_temperature_humidity(
            self.mock_conn, temperature="22度", humidity="60%"
        )
        self.assertEqual(response.action, Action.REQLLM)
        self.assertIn("22", response.result)
        self.assertIn("60", response.result)
        # 验证状态
        self.assertEqual(self.mock_conn.temp_humidity_setting["temperature"], "22.0℃")
        self.assertEqual(self.mock_conn.temp_humidity_setting["humidity"], "60%")

    def test_set_both_with_confirm(self):
        """测试同时设置温度和湿度并确认"""
        response = get_temperature_humidity(
            self.mock_conn, temperature="22度", humidity="60%", confirm=True
        )
        self.assertEqual(response.action, Action.RESPONSE)
        
        # 解析返回的JSON
        result = json.loads(response.response)
        self.assertEqual(result["temperature"], "22.0℃")
        self.assertEqual(result["humidity"], "60%")
        self.assertTrue(result["confirm"])
        
        # 验证状态已清除
        self.assertFalse(hasattr(self.mock_conn, "temp_humidity_setting"))

    def test_multi_step_interaction(self):
        """测试多步交互"""
        # 步骤1：设置温度
        response1 = get_temperature_humidity(
            self.mock_conn, temperature="22度"
        )
        self.assertEqual(response1.action, Action.REQLLM)
        
        # 步骤2：设置湿度
        response2 = get_temperature_humidity(
            self.mock_conn, humidity="60%"
        )
        self.assertEqual(response2.action, Action.REQLLM)
        self.assertIn("确认", response2.result)
        
        # 步骤3：确认
        response3 = get_temperature_humidity(
            self.mock_conn, confirm=True
        )
        self.assertEqual(response3.action, Action.RESPONSE)
        result = json.loads(response3.response)
        self.assertTrue(result["confirm"])

    def test_modify_temperature(self):
        """测试修改温度"""
        # 先设置初始值
        get_temperature_humidity(
            self.mock_conn, temperature="22度", humidity="60%"
        )
        # 修改温度
        response = get_temperature_humidity(
            self.mock_conn, temperature="25度"
        )
        self.assertEqual(response.action, Action.REQLLM)
        # 验证温度已更新
        self.assertEqual(self.mock_conn.temp_humidity_setting["temperature"], "25.0℃")
        # 湿度保持不变
        self.assertEqual(self.mock_conn.temp_humidity_setting["humidity"], "60%")

    def test_invalid_temperature(self):
        """测试无效温度"""
        response = get_temperature_humidity(
            self.mock_conn, temperature="100度"
        )
        self.assertEqual(response.action, Action.REQLLM)
        self.assertIn("超出合理范围", response.result)

    def test_invalid_humidity(self):
        """测试无效湿度"""
        response = get_temperature_humidity(
            self.mock_conn, humidity="150%"
        )
        self.assertEqual(response.action, Action.REQLLM)
        self.assertIn("超出合理范围", response.result)


def run_tests():
    """运行所有测试"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    print("=" * 70)
    print("get_temperature_humidity 函数单元测试")
    print("=" * 70)
    run_tests()

