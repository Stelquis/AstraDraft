"""
DeepAstraDraft 中间件定义。

包含:
- 常驻中间件: TodoList, Filesystem, Summarization
- 条件中间件: CADFileType
- 自定义中间件: ParameterValidation
"""
from typing import Optional


def create_todo_middleware():
    """任务规划中间件 — Agent 自动拆解多步 CAD 查询"""
    try:
        from deepagents.middleware import TodoListMiddleware
        return TodoListMiddleware(
            system_prompt=(
                "你是一个 CAD 图纸智能问答助手。"
                "当用户提出复杂问题时，请先使用 write_todos 工具拆解为子任务：\n"
                "1. 识别问题涉及的参数类型（尺寸/材质/标题栏/签字栏/技术要求/BOM）\n"
                "2. 为每个类型创建独立 todo\n"
                "3. 依次完成每个 todo 后综合回答\n"
                "常见拆解示例：\n"
                "- '这个零件的材质、尺寸和加工方法' → [查材质, 查尺寸, 查成形方法]\n"
                "- '图纸的图号、比例和设计者是谁' → [查图号, 查比例, 查设计者]\n"
                "- '比较所有部品的尺寸' → [列出部品, 查各部品尺寸, 比较]\n"
                "- '图中50mm有几处' → [搜索50mm参数, 统计数量]\n"
            ),
        )
    except ImportError:
        return None


def create_filesystem_middleware(index_dir: str):
    """虚拟文件系统中间件 — 提供图纸参数索引的按需读写"""
    try:
        from deepagents.middleware import FilesystemMiddleware
        return FilesystemMiddleware(
            backend="filesystem",
            root_dir=index_dir,
        )
    except (ImportError, TypeError):
        return None


def create_summarization_middleware(
    max_tokens: int = 20000,
    summary_ratio: float = 0.85,
):
    """自动总结中间件 — 超过 token 阈值自动卸载历史到总结"""
    try:
        from deepagents.middleware import SummarizationMiddleware
        return SummarizationMiddleware(
            max_tokens_before_summary=max_tokens,
            summary_ratio=summary_ratio,
        )
    except ImportError:
        return None


def collect_middleware(index_dir: Optional[str] = None):
    """
    收集所有可用中间件（过滤掉导入失败的）。
    这是 Phase 2/3 创建 Deep Agent 时的推荐调用方式。
    """
    middleware = []
    for factory in [
        create_todo_middleware,
        create_summarization_middleware,
    ]:
        if index_dir:
            mw = create_filesystem_middleware(index_dir)
        else:
            mw = factory()
        if mw is not None:
            middleware.append(mw)
    return middleware
