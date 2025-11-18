import logging
import fastmcp
from pydantic import Field
from fastmcp.tools.tool import ToolResult, TextContent


logger = logging.getLogger(__name__)
mcp = fastmcp.FastMCP("base-server")


CASE_RETRIEVAL_DESCRIPTION = """
搜索实例类文档或者非制度类文档
问题举例:
1. 2025年度培训计划涵盖了哪些专业领域
2. 提供能效分析汇总
"""


@mcp.tool(
    name="case_retrieval",
    title="搜索实例类文档",
    description=CASE_RETRIEVAL_DESCRIPTION,
)
def case_retrieval(
    search_text: str = Field(
        ...,
        description="搜索查询文本",
    ),
) -> ToolResult:
    return ToolResult(
        content=[TextContent(type="text", text=f"{search_text} 搜索实例类文档成功")],
        structured_content={
            "tool_call_resp_meta": {},
            "tool_call_side_effects": [],
        },
    )


REGULATION_SEARCH_DESCRIPTION = """
在知识库中检索相关规章制度, 包括:
浦江数据中心人员设备进出管理规定
浦江数据中心培训管理规定
浦江数据中心应急管理规定
浦江数据中心门禁管理规定
浦江数据中心文档管理规定
浦江数据中心清洁管理规定
浦江数据中心维护管理规定
浦江数据中心事件管理规定
浦江数据中心作业管理规定
浦江数据中心上下电管理规定
浦江数据中心变更管理规定
浦江数据中心风险管理规定
浦江数据中心二次施工管理规定
浦江数据中心职能管理规定
浦江数据中心安全管理规定
浦江数据中心质量管理规定
浦江数据中心巡检管理规定
浦江数据中心交接班管理规定
浦江数据中心供应商管理规定
浦江数据中心容量管理规定
浦江数据中心能源管理规定
浦江数据中心备品备件管理规定
浦江数据中心标识标签管理规定
浦江数据中心问题管理规定
浦江数据中心配置管理规定
浦江数据中心采购管理规定
浦江数据中心预算管理规定
浦江数据中心重保管理规定
浦江数据中心钥匙管理规定
浦江数据中心工具管理规定
问题举例:纸质文档和电子文档怎么管理?
"""


@mcp.tool(
    name="regulation_search",
    title="搜索规章制度相关文档",
    description=REGULATION_SEARCH_DESCRIPTION,
)
def regulation_search(
    search_text: str = Field(..., description="搜索查询文本"),
) -> ToolResult:
    return ToolResult(
        content=[
            TextContent(type="text", text=f"{search_text} 搜索规章制度相关文档成功")
        ],
        structured_content={
            "tool_call_resp_meta": {},
            "tool_call_side_effects": [],
        },
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
