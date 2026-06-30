#!/usr/bin/env python3
"""DeepAstraDraft v1.0 — CAD 图纸智能问答 Agent

用法:
    # CLI 交互模式
    python main.py --file data/cad/filter_modify.dwg

    # CLI 批量模式
    python main.py --file data/cad/filter_modify.dwg --batch questions.txt

    # DeepAgent 引擎 (需 LLM Key)
    python main.py --file data/cad/filter_modify.dwg --engine deep

    # API 服务模式
    uvicorn backend.api:app --host 0.0.0.0 --port 8000
    # 或 ./scripts/start-api.sh

    # Web 前端
    cd frontend && npm run dev  # → http://localhost:5173
"""
from agent.cli import main

if __name__ == "__main__":
    main()
