import json
import logging
import asyncio
import time
from typing import List, Dict, Any
from query_rewriter import QueryRewriteAgent
from llm_client import DeepSeekClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TEST_CASE_PATH = "test_case.json"
OUTPUT_PATH = "evaluation_results.json"
REPEAT_COUNT = 3
CONCURRENCY_LIMIT = 20  # Adjust based on API rate limits

class Evaluator:
    def __init__(self):
        self.agent = QueryRewriteAgent()
        self.judge_client = DeepSeekClient()
        
    def load_test_cases(self):
        with open(TEST_CASE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def llm_judge_async(self, query: str, expected: List[str], generated: List[str]) -> Dict[str, Any]:
        """
        Use LLM to judge if the generated sub-queries are semantically equivalent to expected.
        """
        if not expected:
            return {"is_correct": True, "reason": "未提供期望结果 (No expected ground truth provided)."}

        # Exact match check
        expected_set = set(expected)
        generated_set = set(generated)
        
        if expected_set == generated_set:
            return {"is_correct": True, "reason": "完全匹配 (Exact match)."}

        prompt = f"""你是一个专业的评估裁判。
原始查询: "{query}"
期望的子查询列表: {json.dumps(expected, ensure_ascii=False)}
生成的子查询列表: {json.dumps(generated, ensure_ascii=False)}

任务: 判断“生成的子查询列表”是否在语义上等同于“期望的子查询列表”。
它们不需要逐字完全相同，但必须涵盖相同的信息和意图。
顺序不重要。

请仅返回一个JSON对象，包含以下字段：
"is_correct": boolean,
"reason": string (简要解释)
"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.judge_client.chat_completion_async(messages, temperature=0.0)
        
        if not response:
            logger.error("Judge failed to return response")
            return {"is_correct": False, "reason": "Judge API failure"}

        try:
            # Clean up potential markdown
            cleaned = response.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.error(f"Judge parsing failed: {e}")
            return {"is_correct": False, "reason": "Judge failed to parse response"}

    async def process_single_case(self, idx: int, case: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        head = case.get("head")
        expected = case.get("expected")
        
        logger.info(f"Starting case {idx}: {head[:30]}...")
        
        case_results = []
        
        async def run_iteration(iteration_idx):
            async with semaphore:
                start_time = time.time()
                generated = await self.agent.rewrite_async(head)
                rewrite_duration = time.time() - start_time
                
                judge_result = await self.llm_judge_async(head, expected, generated)
                
                return {
                    "iteration": iteration_idx + 1,
                    "generated": generated,
                    "is_correct": judge_result.get("is_correct", False),
                    "reason": judge_result.get("reason", ""),
                    "duration": rewrite_duration
                }

        # Run iterations concurrently or sequentially? 
        # Usually we want iterations to be independent samples.
        # Running them in parallel is faster.
        tasks = [run_iteration(i) for i in range(REPEAT_COUNT)]
        case_results = await asyncio.gather(*tasks)
        
        correct_count = sum(1 for r in case_results if r["is_correct"])
        pass_rate = correct_count / REPEAT_COUNT
        
        return {
            "id": idx,
            "head": head,
            "expected": expected,
            "metrics": {
                "pass_rate": pass_rate,
                "avg_duration": sum(r["duration"] for r in case_results) / REPEAT_COUNT
            },
            "iterations": case_results,
            "final_verdict": "pass" if pass_rate >= 0.6 else "fail",
            "human_reviewed": False,
            "human_comment": ""
        }

    async def run_evaluation_async(self):
        test_cases = self.load_test_cases()
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        tasks = [self.process_single_case(idx, case, semaphore) for idx, case in enumerate(test_cases)]
        results_list = await asyncio.gather(*tasks)
        
        # Sort by ID to maintain order
        results_list.sort(key=lambda x: x["id"])
        
        # Calculate summary
        total_score = 0
        total_cases = 0
        for r in results_list:
            if r["expected"]:
                total_score += r["metrics"]["pass_rate"]
                total_cases += 1
                
        final_metric = total_score / total_cases if total_cases > 0 else 0
        
        output = {
            "summary": {
                "total_cases": len(test_cases),
                "evaluated_cases": total_cases,
                "overall_accuracy": final_metric,
                "timestamp": time.time()
            },
            "details": results_list
        }
        
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Evaluation complete. Accuracy: {final_metric:.2%}")
        return output

if __name__ == "__main__":
    evaluator = Evaluator()
    asyncio.run(evaluator.run_evaluation_async())
