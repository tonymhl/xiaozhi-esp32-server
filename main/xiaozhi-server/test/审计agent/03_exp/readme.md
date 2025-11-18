# 命令示例
多次指定问题：
```python
python test/perf_test/03_exp/classify.py --question "检索培训管理规定" --question "提供能效分析汇总"
or
python main\xiaozhi-server\test\审计agent\03_exp\classify.py --question "检索培训管理规定" --question "提供能效分析汇总"
```
从文件读取问题（每行一个）：
```python
python test/perf_test/03_exp/classify.py --questions-file test/perf_test/03_exp/req.txt
```

# 输出示例

对每个问题输出对应被调用的工具名称（无调用则为 none）：
```bash
[1] QUESTION: 检索培训管理规定
TOOL_CALLS:
regulation_search
----------------------------------------
[2] QUESTION: 提供能效分析汇总
TOOL_CALLS:
case_retrieval
----------------------------------------
```