#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
温度负载率工具函数 - API集成验证脚本

用途：验证 get_temperature_load_rate.py 的语法、导入和基本结构
"""

import sys
import os

def verify_import():
    """验证模块能否正确导入"""
    print("=" * 60)
    print("1. 验证模块导入...")
    print("=" * 60)
    
    try:
        # 添加项目路径
        sys.path.insert(0, os.path.dirname(__file__))
        
        # 导入模块
        from plugins_func.functions import get_temperature_load_rate
        
        print("✅ 模块导入成功")
        return get_temperature_load_rate
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_structure(module):
    """验证模块结构"""
    print("\n" + "=" * 60)
    print("2. 验证模块结构...")
    print("=" * 60)
    
    required_items = [
        ("GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC", "函数描述"),
        ("get_temperature_load_rate", "主函数"),
        ("parse_temperature", "温度解析函数"),
        ("parse_load_rate", "负载率解析函数"),
        ("validate_temperature", "温度验证函数"),
        ("validate_load_rate", "负载率验证函数"),
        ("call_asr_api", "接口1调用函数"),
        ("call_confirm_api", "接口2调用函数"),
        ("get_api_base_url", "API地址获取函数"),
        ("initialize_temp_load_rate_state", "状态初始化函数"),
        ("clear_temp_load_rate_state", "状态清除函数"),
        ("PRESET_PARAMS", "预设参数"),
        ("DEFAULT_API_BASE_URL", "默认API地址"),
        ("DEFAULT_API_TIMEOUT", "默认超时时间"),
    ]
    
    all_ok = True
    for item_name, description in required_items:
        if hasattr(module, item_name):
            print(f"✅ {description:20s} ({item_name})")
        else:
            print(f"❌ {description:20s} ({item_name}) - 未找到")
            all_ok = False
    
    return all_ok


def verify_constants(module):
    """验证常量值"""
    print("\n" + "=" * 60)
    print("3. 验证常量值...")
    print("=" * 60)
    
    try:
        # 检查预设参数
        preset_params = module.PRESET_PARAMS
        print(f"✅ 预设参数: {preset_params}")
        
        # 检查默认API地址
        default_url = module.DEFAULT_API_BASE_URL
        print(f"✅ 默认API地址: {default_url}")
        
        # 检查超时时间
        timeout = module.DEFAULT_API_TIMEOUT
        print(f"✅ 默认超时时间: {timeout}秒")
        
        # 检查函数描述
        func_desc = module.GET_TEMPERATURE_LOAD_RATE_FUNCTION_DESC
        print(f"✅ 函数名称: {func_desc['function']['name']}")
        print(f"✅ 函数描述: {func_desc['function']['description'][:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ 常量验证失败: {e}")
        return False


def verify_functions(module):
    """验证函数签名"""
    print("\n" + "=" * 60)
    print("4. 验证函数签名...")
    print("=" * 60)
    
    try:
        import inspect
        
        # 检查主函数签名
        main_func = module.get_temperature_load_rate
        sig = inspect.signature(main_func)
        params = list(sig.parameters.keys())
        print(f"✅ 主函数参数: {params}")
        
        expected_params = ['conn', 'temperature', 'load_rate', 'confirm', 'cancel']
        if params == expected_params:
            print(f"✅ 参数列表正确")
        else:
            print(f"⚠️  参数列表: 期望 {expected_params}, 实际 {params}")
        
        return True
    except Exception as e:
        print(f"❌ 函数签名验证失败: {e}")
        return False


def test_parse_functions(module):
    """测试解析函数"""
    print("\n" + "=" * 60)
    print("5. 测试解析函数...")
    print("=" * 60)
    
    try:
        # 测试温度解析
        test_temps = ["22.5", "28度", "25℃", "30摄氏度"]
        print("\n温度解析测试:")
        for temp_str in test_temps:
            value, formatted = module.parse_temperature(temp_str)
            if value is not None:
                print(f"  ✅ '{temp_str}' -> {value}℃ ({formatted})")
            else:
                print(f"  ⚠️  '{temp_str}' -> 解析失败")
        
        # 测试负载率解析
        test_loads = ["90", "95.6kw", "80千瓦", "100 kw"]
        print("\n负载率解析测试:")
        for load_str in test_loads:
            value, formatted = module.parse_load_rate(load_str)
            if value is not None:
                print(f"  ✅ '{load_str}' -> {value}kw ({formatted})")
            else:
                print(f"  ⚠️  '{load_str}' -> 解析失败")
        
        return True
    except Exception as e:
        print(f"❌ 解析函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_functions(module):
    """测试验证函数"""
    print("\n" + "=" * 60)
    print("6. 测试验证函数...")
    print("=" * 60)
    
    try:
        # 测试温度验证
        test_temps = [-15, 0, 22.5, 50, 60]
        print("\n温度验证测试 (合理范围: -10~50℃):")
        for temp in test_temps:
            is_valid, error_msg = module.validate_temperature(temp)
            if is_valid:
                print(f"  ✅ {temp}℃ - 有效")
            else:
                print(f"  ❌ {temp}℃ - 无效: {error_msg}")
        
        # 测试负载率验证
        test_loads = [-10, 0, 90, 200, 250]
        print("\n负载率验证测试 (合理范围: 0~200kw):")
        for load in test_loads:
            is_valid, error_msg = module.validate_load_rate(load)
            if is_valid:
                print(f"  ✅ {load}kw - 有效")
            else:
                print(f"  ❌ {load}kw - 无效: {error_msg}")
        
        return True
    except Exception as e:
        print(f"❌ 验证函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("温度负载率工具函数 - API集成验证")
    print("=" * 60)
    
    # 验证导入
    module = verify_import()
    if not module:
        print("\n❌ 验证失败：无法导入模块")
        return False
    
    # 验证结构
    if not verify_structure(module):
        print("\n⚠️  警告：模块结构不完整")
    
    # 验证常量
    if not verify_constants(module):
        print("\n⚠️  警告：常量验证失败")
    
    # 验证函数签名
    if not verify_functions(module):
        print("\n⚠️  警告：函数签名验证失败")
    
    # 测试解析函数
    if not test_parse_functions(module):
        print("\n⚠️  警告：解析函数测试失败")
    
    # 测试验证函数
    if not test_validate_functions(module):
        print("\n⚠️  警告：验证函数测试失败")
    
    print("\n" + "=" * 60)
    print("✅ 验证完成！")
    print("=" * 60)
    print("\n📝 说明：")
    print("  - 此脚本仅验证基本语法和结构")
    print("  - 完整测试需要启动服务并进行实际对话")
    print("  - API接口调用需要实际的API服务支持")
    print("\n📚 相关文档：")
    print("  - 详细开发文档: docs/get_temperature_load_rate_api_integration.md")
    print("  - 快速开始指南: docs/get_temperature_load_rate_quickstart.md")
    print("  - 完成总结: 温度负载率工具函数API集成完成总结.md")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

