#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速验证 get_temperature_humidity 函数代码

这个脚本只验证代码语法和基本结构，不会触发系统初始化
"""

import sys
import os
import ast

def verify_syntax(file_path):
    """验证Python文件语法"""
    print(f"检查文件语法: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print("✅ 语法检查通过")
        return True
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


def check_function_structure(file_path):
    """检查函数结构"""
    print(f"\n检查函数结构: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        checks = {
            "装饰器@register_function": "@register_function" in code,
            "函数定义get_temperature_humidity": "def get_temperature_humidity" in code,
            "函数描述GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC": "GET_TEMPERATURE_HUMIDITY_FUNCTION_DESC" in code,
            "导入ActionResponse": "ActionResponse" in code,
            "导入Action": "from plugins_func.register import" in code and "Action" in code,
            "导入ToolType": "ToolType" in code,
            "参数temperature": "temperature:" in code or "temperature =" in code,
            "参数humidity": "humidity:" in code or "humidity =" in code,
            "参数confirm": "confirm:" in code or "confirm =" in code,
            "参数cancel": "cancel:" in code or "cancel =" in code,
            "辅助函数parse_temperature": "def parse_temperature" in code,
            "辅助函数parse_humidity": "def parse_humidity" in code,
            "辅助函数validate_temperature": "def validate_temperature" in code,
            "辅助函数validate_humidity": "def validate_humidity" in code,
        }
        
        all_passed = True
        for name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_test_file(file_path):
    """检查测试文件"""
    print(f"\n检查测试文件: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        checks = {
            "导入unittest": "import unittest" in code,
            "测试类定义": "class Test" in code,
            "测试方法": "def test_" in code,
            "导入被测函数": "from get_temperature_humidity import" in code,
        }
        
        all_passed = True
        for name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    print("=" * 70)
    print("get_temperature_humidity 快速验证")
    print("=" * 70)
    
    # 获取文件路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    func_file = os.path.join(base_dir, "plugins_func", "functions", "get_temperature_humidity.py")
    test_file = os.path.join(base_dir, "plugins_func", "functions", "test_get_temperature_humidity.py")
    
    results = []
    
    # 检查函数文件
    print("\n" + "=" * 70)
    print("1. 检查函数文件")
    print("=" * 70)
    if os.path.exists(func_file):
        print(f"✅ 文件存在: {func_file}")
        results.append(("语法检查", verify_syntax(func_file)))
        results.append(("结构检查", check_function_structure(func_file)))
    else:
        print(f"❌ 文件不存在: {func_file}")
        results.append(("函数文件", False))
    
    # 检查测试文件
    print("\n" + "=" * 70)
    print("2. 检查测试文件")
    print("=" * 70)
    if os.path.exists(test_file):
        print(f"✅ 文件存在: {test_file}")
        results.append(("测试文件语法", verify_syntax(test_file)))
        results.append(("测试文件结构", check_test_file(test_file)))
    else:
        print(f"❌ 文件不存在: {test_file}")
        results.append(("测试文件", False))
    
    # 打印总结
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20s} {status}")
    
    print("=" * 70)
    
    # 计算通过率
    passed = sum(1 for _, r in results if r)
    total = len(results)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"\n总计: {passed}/{total} 检查通过 ({percentage:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有检查通过！代码结构正确。")
        print("\n下一步：")
        print("  1. 启动 xiaozhi-server 服务")
        print("  2. 通过对话测试功能：'设置温度22度湿度60%'")
        print("  3. 查看日志确认函数被正确加载")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个检查失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

