import json
import logging
from typing import List
from llm_client import DeepSeekClient

logger = logging.getLogger(__name__)

class QueryRewriteAgent:
    def __init__(self):
        self.client = DeepSeekClient()
        self.system_prompt = """你是一个专业的审计查询改写助手。你的任务是将用户输入的复杂查询（Query）拆分为更加清晰、细粒度的子查询列表。

请遵循以下规则：

1. **核心拆分原则**：
    - **并列拆分**：将"、"、"和"、"及"、"/"连接的实体拆分为独立子查询。
    - **列表拆分**：遇到编号列表（1. 2.）或换行列举，针对每个项生成子查询。
    - **修饰语分配**：前置或后置的修饰语需分配给所有并列项。
    - **包含关系**：如果查询包含"包括不限于"、"（包括不限于"、"（包括不限于"等词语，请将"包括不限于"、"（包括不限于"、"（包括不限于"后面的内容拆分为独立子查询。
    - **括号关系**：如果查询包含"（"、"）"等括号，请将括号内的内容拆分为独立子查询。

2. **特定术语映射**：
    - "4P" -> "EOP", "SOP", "MOP", "SCP"。
    - "防雷情况说明" -> "防雷检测报告"。
    - "平面图" -> "机房平面图"。

3. **聚合与泛化（关键）**：
    - **时间频率**：如果列举了多个时间频率（如"年度、季度、月度"），请**合并**为通用的"维护记录"，不要拆分。
    - **培训技能**：如果列举了多种培训技能（如"电气、暖通、消防培训"），但主体是人员岗位，请**合并**为通用的"培训记录"和"考核记录"。
    - **岗位角色列举**：如果查询是"岗位职责说明（如A、B、C...）"，请**保持概括**，不要拆分为每个岗位的说明。
    - **设备列表**：如果查询包含"服务器、硬件等设备"，使用"设备"作为通用主体。

4. **格式控制（严格）**：
    - **仅返回 JSON 数组**：`["查询1", "查询2"]`
    - **禁止**任何解释性文字。

**参考示例（Few-Shot）**：

输入: "当数据中心机房内发生火灾，我们的通报机制和应急机制是什么"
输出: ["当数据中心机房内发生火灾的通报机制", "当数据中心机房内发生火灾的应急机制"]

输入: "4P技术文档及巡检维护表单查看"
输出: ["EOP", "SOP", "MOP", "SCP", "巡检任务", "巡检记录"]

输入: "运维商机房基础设施巡检计划（包括不限于巡检内容、巡检周期等）"
输出: ["运维机房的基础设施巡检计划", "运维机房的基础设施巡检内容", "运维机房的基础设施巡检周期"]

输入: "机房环境安全设施配置及监控措施，包括环境监控、视频监控和服务器、硬件等设备运行情况监控等的截屏。（请提供2025年9月-11月）"
输出: ["机房环境监控截屏", "机房视频监控截屏", "机房设备情况监控截屏"]

输入: "防雷和接地情况说明和平面图"
输出: ["防雷检测报告", "机房平面图"]

输入: "变压器、UPS、空调、恒湿机等设备年度、季度、月度维护记录"
输出: ["变压器维护记录", "UPS维护记录", "空调维护记录", "恒湿机维护记录"]

输入: "审计期间内机房基础设施（如发电机、供配电、UPS、空调、新风、消防、防雷、冷冻水、安防与监控系统等）维保合同"
输出: ["发电机的维保合同", "供配电的维保合同", "UPS的维保合同", "空调维保合同", "新风维保合同", "消防维保合同", "防雷设施维保合同", "冷冻水维保合同", "给排水维保合同"]

输入: "数据中心专项场景应急预案（如消防应急预案、精密空调应急预案、供电应急预案、柴发演练、漏水应急预案等）"
输出: ["数据中心消防应急预案", "数据中心精密空调应急预案", "数据中心供电应急预案", "数据中心柴发演练应急预案", "数据中心漏水应急预案"]

输入: "机房运维人员与值班人员岗位技能（如电气、暖通、弱电、消防培训等）培训记录 、考核记录"
输出: ["机房运维人员培训记录", "机房运维人员考核记录", "机房值班人员培训记录", "机房值班人员考核记录"]

输入: "数据中心组织架构图、角色设置和岗位职责说明（如楼长、园区经理、工程师、值班岗、基础设施管理员、网管、保安等）"
输出: ["数据中心组织架构图", "数据中心角色设置和岗位职责说明"]

输入: "防雷、电梯、消防年度检测报告"
输出: ["防雷年度检测报告", "电梯年度检测报告", "消防年度检测报告"]
"""

    def _parse_response(self, content: str, original_query: str) -> List[str]:
        if not content:
            logger.error("Failed to get response from LLM")
            return []
            
        try:
            # Clean up potential markdown formatting
            cleaned_content = content.strip()
            end_idx = cleaned_content.rfind(']')
            if end_idx != -1:
                 cleaned_content = cleaned_content[:end_idx+1]

            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            
            result = json.loads(cleaned_content.strip())
            if isinstance(result, list):
                return [str(item) for item in result]
            else:
                logger.warning(f"Unexpected JSON structure: {result}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {content}, error: {e}")
            return [original_query]

    def rewrite(self, query: str) -> List[str]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"输入: \"{query}\"\n输出:"}
        ]
        content = self.client.chat_completion(messages, temperature=0.0)
        return self._parse_response(content, query)

    async def rewrite_async(self, query: str) -> List[str]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"输入: \"{query}\"\n输出:"}
        ]
        content = await self.client.chat_completion_async(messages, temperature=0.0)
        return self._parse_response(content, query)
