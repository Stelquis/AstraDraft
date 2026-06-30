from __future__ import annotations

import argparse
import logging
import sys

from backend.config import AgentConfig
from agent.core import DeepAstraDraft


def main():
    parser = argparse.ArgumentParser(
        description="AstraDraft — CAD 图纸智能问答 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m agent.cli --file data/cad/filter_modify.dxf\n"
            "  python -m agent.cli --file data/cad/filter_modify.dwg\n"
            "  python -m agent.cli --file data/cad/filter_modify.dwg --engine deep\n"
        ),
    )
    parser.add_argument("--file", "-f", required=True, help="CAD 文件路径（.dxf 或 .dwg）")
    parser.add_argument("--log-level", default="INFO", help="日志级别 (DEBUG/INFO/WARNING)")
    parser.add_argument("--batch", help="批量查询模式：从文件读取问题（每行一个）")
    parser.add_argument(
        "--engine", choices=["rule", "llm", "deep"],
        default="rule",
        help="查询引擎: rule=规则匹配(默认), llm=LLM增强, deep=DeepAgent",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = AgentConfig(cad_file=args.file, log_level=args.log_level)
    agent = DeepAstraDraft(config)

    try:
        agent.load_cad(args.file)
    except Exception as e:
        print(f"加载 CAD 文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"AstraDraft Agent 已就绪（已索引 {agent.parameter_count} 个参数）")
    print("输入问题开始查询，输入 'quit' 或 'exit' 退出\n")

    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            questions = [line.strip() for line in f if line.strip()]
        for q in questions:
            print(f"Q: {q}")
            print(f"A: {agent.ask(q)}\n")
        return

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        try:
            answer = agent.ask(question)
            print(answer)
            print()
        except Exception as e:
            print(f"查询出错: {e}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
