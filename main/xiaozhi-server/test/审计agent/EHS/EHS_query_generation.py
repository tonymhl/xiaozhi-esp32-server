import asyncio
import pandas as pd
import json
import os
import sys
import time
from openai import AsyncOpenAI
from typing import List

# 设置标准输出编码为utf-8
sys.stdout.reconfigure(encoding='utf-8')

# 配置信息
API_KEY = "av7b4VoBryCMu3hZ9"
BASE_URL = "https://deepseek.gds-services.com/v1"
MODEL = "deepseek-ai/DeepSeek-V3"

SYSTEM_PROMPT = """你是一个专业的数据中心审计助理，负责根据文档名称生成相关的查询问题。
你的任务是针对给定的制度文档，生成2个用户可能会问的“制度类”查询问题。

【什么是制度类查询？】
制度类查询关注的是：
- 管理要求、规定、标准
- 流程、审批规则
- 职责分工
- 定义、分类、等级
- 普遍性的管理机制

【什么不是制度类查询？】（请避免生成此类问题）
- 具体的执行记录（如“是否有2024年的培训记录”）
- 具体的计划（如“2025年维护计划”）
- 具体的操作手册（MOP）
- 具体的证书、报告、清单

【生成要求】
1. 问题必须与文档标题相关，但尽量避免出现文档标题本身。
2. 问题风格应自然、专业。
3. 必须生成2个不同的问题。
4. 返回格式必须是JSON对象，包含一个"queries"字段，值为字符串列表。例如：{"queries": ["问题1", "问题2"]}。
"""

async def generate_queries(client: AsyncOpenAI, doc_name: str, doc_path: str, retries=3) -> List[str]:
    user_prompt = f"""
文档名称：{doc_name}
文档路径：{doc_path}

请生成2个针对该文档的“制度类”查询问题。
"""
    
    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            
            if "queries" in result and isinstance(result["queries"], list):
                return result["queries"][:2]
            
            for val in result.values():
                if isinstance(val, list):
                    return val[:2]
                    
            return []
        except Exception as e:
            print(f"Error generating queries for {doc_name} (Attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 * (attempt + 1)) # 指数退避
            else:
                return []

async def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "EHS制度文档.xlsx")
    output_file = os.path.join(script_dir, "EHS_generated_queries.csv")
    
    print(f"Reading from: {input_file}")
    
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    
    if '制度' not in df.columns or '路径' not in df.columns:
        print("Error: Excel file must contain '制度' and '路径' columns.")
        return

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    results = []
    tasks = []
    
    # 降低并发数到 20
    sem = asyncio.Semaphore(20) 
    
    async def process_row(index, row):
        async with sem:
            doc_name = row['制度']
            doc_path = row['路径']
            
            if pd.isna(doc_name): return
            
            print(f"Processing: {doc_name}")
            queries = await generate_queries(client, str(doc_name), str(doc_path))
            
            if queries:
                for q in queries:
                    results.append({
                        "文档": doc_name,
                        "Q": q,
                        "A": "",
                        "标签": "制度类",
                        "路径": doc_path
                    })
                print(f"Success: {doc_name}")
            else:
                print(f"Failed: {doc_name}")
            
            # 增加请求间隔
            await asyncio.sleep(0.05)

    for index, row in df.iterrows():
        tasks.append(process_row(index, row))
        
    if tasks:
        await asyncio.gather(*tasks)
    
    if results:
        output_df = pd.DataFrame(results)
        output_df.insert(0, '编号', range(1, len(output_df) + 1))
        output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(output_df)} queries to {output_file}")
    else:
        print("No queries generated.")

if __name__ == "__main__":
    asyncio.run(main())
