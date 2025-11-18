
import argparse
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from fastmcp import Client
from openai import AsyncOpenAI


async def build_openai_tools_from_mcp(mcp_url: str) -> List[Dict[str, Any]]:
    """从 MCP 客户端动态获取工具，并转换为 OpenAI Tools 结构"""
    async with Client(mcp_url) as mcp:
        await mcp.ping()
        tools = await mcp.list_tools()

    openai_tools: List[Dict[str, Any]] = []
    for tool in tools:
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
        )
    return openai_tools


async def run_once(
    aclient: AsyncOpenAI,
    model: str,
    question: str,
    temperature: float,
    max_tokens: int,
    tools: List[Dict[str, Any]],
) -> list[str]:
    """执行一次非流式对话，返回被调用的工具名称列表"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = (
        "你是一个专业的审计与知识检索助手。"
        f"\n现在的时间是上海时间: {now}"
        "\n当有合适的工具可用时，应优先选择工具以获取更准确的信息。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    response = await aclient.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        tools=tools,
        tool_choice="auto",
        max_completion_tokens=max_tokens,
    )

    message = response.choices[0].message
    called_tool_names: list[str] = []
    if getattr(message, "tool_calls", None):
        for call in message.tool_calls:
            if getattr(call, "function", None) and getattr(call.function, "name", None):
                called_tool_names.append(call.function.name)

    return called_tool_names


def parse_args() -> argparse.Namespace:
    mcp_path = str((Path(__file__).parent / "audit_mcp.py").absolute())
    parser = argparse.ArgumentParser(description="MCP 分类实验：解析被调用的工具名称")
    parser.add_argument("--question", action="append", help="用户问题，可重复多次指定")
    parser.add_argument("--questions-file", type=str, help="包含问题列表的文件，每行一个问题")
    parser.add_argument("--mcp-url", type=str, default=os.getenv("MCP_URL", mcp_path))
    parser.add_argument("--api-key", type=str, default=os.getenv("OPENAI_API_KEY", "av7b4VoBryCMu3hZ9"))
    parser.add_argument("--base-url", type=str, default=os.getenv("OPENAI_BASE_URL", "https://deepseek.gds-services.com/v1"))
    parser.add_argument("--model", type=str, default=os.getenv("MODEL", "deepseek-ai/DeepSeek-V3"))
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


async def amain() -> None:
    args = parse_args()

    # 聚合问题列表
    questions: List[str] = []
    if args.question:
        questions.extend([q for q in args.question if q and q.strip()])
    if args.questions_file:
        with open(args.questions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    questions.append(line)
    if not questions:
        raise SystemExit("必须通过 --question 多次指定或提供 --questions-file 才能执行。")

    client_kwargs = {
        "api_key": args.api_key or "",
        "base_url": args.base_url,
        "timeout": args.timeout,
    }
    # 过滤 None
    client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}

    aclient = AsyncOpenAI(**client_kwargs)

    # 从 MCP 获取工具列表
    tools = await build_openai_tools_from_mcp(args.mcp_url)

    # 批量执行
    for idx, q in enumerate(questions, start=1):
        tool_names = await run_once(
            aclient=aclient,
            model=args.model,
            question=q,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            tools=tools,
        )
        unique_tool_names = list(dict.fromkeys(tool_names))
        print(f"[{idx}] QUESTION: {q}")
        if unique_tool_names:
            print("TOOL_CALLS:")
            for name in unique_tool_names:
                print(name)
        else:
            print("TOOL_CALLS: (none)")
        print("-" * 40)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()