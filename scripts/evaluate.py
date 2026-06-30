#!/usr/bin/env python3
"""评估 Agent 系统准确率

用法:
    python tools/evaluate.py --file data/cad/filter_modify.dxf --questions examples/sample_questions.txt
"""
import argparse
import json
import logging
import os
import re

from backend.config import AgentConfig
from agent.core import DeepAstraDraft as Agent

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_questions(path: str) -> list[dict]:
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                parts = line.split("|", 1)
                questions.append({"question": parts[0].strip(), "expected": parts[1].strip()})
            else:
                questions.append({"question": line, "expected": ""})
    return questions


def check_answer(answer: str, expected: str) -> bool:
    if not expected:
        return True

    # 支持 | 作为"或"分隔符：任一备选匹配即通过
    alternatives = expected.split("|")
    for alt in alternatives:
        if _check_single(answer, alt.strip()):
            return True
    return False


def _check_single(answer: str, expected: str) -> bool:
    """检查 answer 是否包含 expected（数值或文本）"""
    if not expected:
        return True

    answer_lower = answer.lower()
    expected_lower = expected.lower()

    # 先尝试数值匹配
    expected_nums = re.findall(r"[\d.]+", expected)
    answer_nums = re.findall(r"[\d.]+", answer)

    if expected_nums:
        # 检查所有期望数值是否都在答案中出现（容差 ±0.1）
        for en in expected_nums:
            if not any(abs(float(an) - float(en)) < 0.1 for an in answer_nums):
                return False
        return True

    # 纯文本匹配：检查每个期望词语是否包含在答案中
    # 支持用空格分隔多个关键词（都必须在答案中）
    keywords = expected_lower.split()
    return all(kw in answer_lower for kw in keywords)


def main():
    parser = argparse.ArgumentParser(description="评估 Agent 系统准确率")
    parser.add_argument("--file", "-f", required=True, help="CAD 文件路径")
    parser.add_argument("--questions", "-q", required=True, help="问题文件路径（每行: 问题|预期答案）")
    parser.add_argument("--output", "-o", help="结果输出路径（JSON）")
    args = parser.parse_args()

    config = AgentConfig(cad_file=args.file)
    agent = Agent(config)
    agent.load_cad()

    questions = load_questions(args.questions)
    results = []
    correct = 0

    for item in questions:
        q = item["question"]
        expected = item["expected"]
        answer = agent.ask(q)
        is_correct = check_answer(answer, expected)
        if is_correct:
            correct += 1

        results.append({
            "question": q,
            "expected": expected,
            "answer": answer,
            "correct": is_correct,
        })
        status = "PASS" if is_correct else "FAIL"
        print(f"[{status}] Q: {q}")
        print(f"       Expected: {expected}")
        print(f"       Got:      {answer}")
        print()

    total = len(questions)
    accuracy = correct / total * 100 if total > 0 else 0
    print(f"{'='*50}")
    print(f"总计: {total} 题, 正确: {correct}, 准确率: {accuracy:.1f}%")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"accuracy": accuracy, "total": total, "correct": correct, "results": results},
                      f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
