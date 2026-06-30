"""
DeepAstraDraft 主 Agent。

组装子 Agent、中间件、Skills、记忆，提供生产级 CAD 问答能力。

用法:
    from agent.core import DeepAstraDraft

    agent = DeepAstraDraft()
    agent.load_cad("data/cad/filter_modify.dwg")
    answer = agent.ask("总长度是多少")
"""
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_deepseek import ChatDeepSeek

from backend.config import AgentConfig
from agent.session import Session
from agent.filesystem import CADIndexFilesystem
from agent.memory import AstraDraftMemory
from backend.middleware import collect_middleware
from agent.skills import SkillRegistry
from agent.sub_agents import (
    parser_subagent,
    indexer_subagent,
    evaluator_subagent,
)

logger = logging.getLogger(__name__)


class DeepAstraDraft:
    """生产级 CAD 智能问答 Agent（Deep Agents 架构）"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.session = Session()
        self.memory = AstraDraftMemory()
        self.fs_backend = CADIndexFilesystem()
        self.skills = SkillRegistry()

        self._agent = None
        self._index_dir: Optional[str] = None
        self._llm: Optional[ChatDeepSeek] = None
        self._index = None

    # ================================================================
    # 公共接口
    # ================================================================

    def load_cad(self, file_path: str):
        """加载 CAD 图纸：解析 → 构建索引 → 导出虚拟文件系统 → 初始化 Agent"""
        path = file_path

        # Step 1: 解析并构建索引（复用现有 Pipeline）
        from cad.parser import CADParser
        from cad.understanding.component_recognizer import ComponentRecognizer
        from cad.understanding.parameter_index import ParameterIndex
        from cad.understanding.scale_inferencer import ScaleInferencer

        logger.info("Parsing CAD: %s", path)

        index_path = self.config.index_path
        if os.path.isfile(str(index_path)):
            logger.info("Loading cached index: %s", index_path)
            self._index = ParameterIndex.load(str(index_path))
        else:
            parser = CADParser(path)
            doc = parser.parse()
            unit = ScaleInferencer().infer(doc)
            components = ComponentRecognizer().recognize(doc)
            idx = ParameterIndex()
            self._index = idx.build(doc)
            self._index.components = components
            os.makedirs(os.path.dirname(str(index_path)) or ".", exist_ok=True)
            idx.save(str(index_path))

        # 单位归一化
        for param in self._index.parameters:
            if param.value == 0 and param.raw_text:
                continue
            if not param.unit or param.unit == "inches":
                param.unit = "mm"

        # Step 2: 导出虚拟文件系统
        self._index_dir = self.fs_backend.export_index(
            self._index, os.path.basename(path)
        )
        logger.info("Virtual FS ready: %s", self._index_dir)

        # Step 3: 初始化 LLM + LangSmith 追踪
        self._init_llm()
        self._init_langsmith()

        # Step 4: 发现 Skills
        skill_names = self.skills.discover()
        logger.info("Available skills: %s", skill_names)

        # Step 5: 初始化 Deep Agent
        self._init_agent()

        logger.info("DeepAstraDraft ready. %d params, %d skills.",
                     len(self._index.parameters), len(skill_names))

    def ask(self, question: str) -> str:
        """回答用户问题（使用 Deep Agent）"""
        if self._agent:
            return self._ask_deep(question)
        return self._ask_fallback(question)

    # ================================================================
    # 内部方法
    # ================================================================

    def _init_llm(self):
        """初始化 LLM 客户端"""
        api_key = self.config.llm_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        base_url = self.config.llm_base_url or os.environ.get(
            "ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"
        )
        model = self.config.llm_model or os.environ.get(
            "ANTHROPIC_MODEL", "deepseek-v4-flash[1m]"
        )
        if api_key:
            self._llm = ChatDeepSeek(
                model=model,
                api_key=api_key,
                api_base=base_url,
                temperature=0,
                max_tokens=1024,
            )
            logger.info("LLM ready: %s", model)

    def _init_langsmith(self):
        """初始化 LangSmith 全链路追踪（可选）"""
        ls_key = (self.config.langsmith_api_key
                  or os.environ.get("LANGCHAIN_API_KEY", ""))
        if ls_key:
            os.environ["LANGCHAIN_API_KEY"] = ls_key
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault(
                "LANGCHAIN_PROJECT",
                self.config.langsmith_project or "deepastradraft",
            )
            os.environ.setdefault(
                "LANGCHAIN_ENDPOINT",
                self.config.langsmith_endpoint or "https://api.smith.langchain.com",
            )
            logger.info("LangSmith tracing enabled (project: %s)",
                         os.environ["LANGCHAIN_PROJECT"])

    def _init_agent(self):
        """初始化 Deep Agent（Phase 3 核心）"""
        try:
            from deepagents import create_deep_agent

            # 收集中间件
            middleware = collect_middleware(self._index_dir)

            self._agent = create_deep_agent(
                model=self._llm,
                system_prompt=self._build_system_prompt(),
                subagents=[
                    parser_subagent,
                    indexer_subagent,
                    evaluator_subagent,
                ],
                middleware=middleware,
                tools=self._build_tools(),
                checkpointer=self.memory.checkpointer if self.memory else None,
            )
            logger.info("Deep Agent created with %d subagents, %d middleware",
                         3, len(middleware))
        except Exception as e:
            logger.warning("Failed to create Deep Agent, will use fallback: %s", e)
            self._agent = None

    def _build_system_prompt(self) -> str:
        skills_prompt = self.skills.build_system_prompt()
        return (
            "你是 DeepAstraDraft，一个工业级 CAD 图纸智能问答助手。\n\n"
            "## 工作流程\n"
            "1. 分析用户问题\n"
            "2. 在图纸索引文件中查询参数\n"
            "3. 简洁准确地回答\n\n"
            f"## 图纸索引\n"
            f"索引目录: {self._index_dir}\n"
            "  - summary.md — 索引摘要\n"
            "  - dimensions.txt — 尺寸参数（按值降序）\n"
            "  - info_params.txt — 信息参数\n"
            "  - parameters.json — 完整数据\n\n"
            f"{skills_prompt}\n\n"
            "## 回答规则\n"
            "- 只回答索引中存在的参数\n"
            "- 数值参数: 格式 '数值 单位'\n"
            "- 信息参数: 给出原始文本\n"
            "- 未找到时说'未找到'\n"
        )

    def _build_tools(self):
        """构建自定义查询工具"""
        from langchain_core.tools import tool

        @tool
        def lookup_parameter(name: str) -> str:
            """按名称查询 CAD 参数。输入中文或英文参数名，返回详情。"""
            if not self._index:
                return "索引未加载"
            import json
            for p in self._index.parameters:
                if p.name == name or name in p.aliases:
                    if p.value > 0 or p.unit:
                        return json.dumps({
                            "name": p.name, "value": p.value,
                            "unit": p.unit, "layer": p.layer,
                        }, ensure_ascii=False)
                    return json.dumps({
                        "name": p.name, "raw_text": p.raw_text[:500],
                        "layer": p.layer,
                    }, ensure_ascii=False)
            return f"未找到参数: {name}"

        @tool
        def list_all_parameters(query: str = "") -> str:
            """列出所有可用参数名。可选 query 过滤。"""
            if not self._index:
                return "索引未加载"
            names = []
            for p in self._index.parameters:
                if not query or query.lower() in p.name.lower():
                    names.append(p.name)
            return "\n".join(names)

        @tool
        def search_by_value(value: float, tolerance: float = 0.5) -> str:
            """按数值搜索参数。返回匹配的参数列表。"""
            if not self._index:
                return "索引未加载"
            matches = []
            for p in self._index.parameters:
                if p.value > 0 and abs(p.value - value) < tolerance:
                    matches.append(f"{p.name} = {p.value} {p.unit}")
            if matches:
                return f"找到 {len(matches)} 个匹配:\n" + "\n".join(matches)
            return f"未找到数值 {value} 附近的参数"

        return [lookup_parameter, list_all_parameters, search_by_value]

    # ================================================================
    # 查询执行
    # ================================================================

    def _ask_deep(self, question: str) -> str:
        """使用 Deep Agent 回答"""
        try:
            config = {"configurable": {"thread_id": "cad-session-1"}}
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config=config,
            )
            answer = result["messages"][-1].content
            self.memory.record_query(question, answer, "deep_agent")
            return answer
        except Exception as e:
            logger.warning("Deep Agent query failed, falling back: %s", e)
            return self._ask_fallback(question)

    def _ask_fallback(self, question: str) -> str:
        """回退到规则引擎查询"""
        from cad.nlp.query_processor import QueryProcessor
        import re

        if not self._index:
            return "Agent 未初始化，请先调用 load_cad()"

        qp = QueryProcessor(self._index)
        answer = qp.process(question)
        self.memory.record_query(question, answer, "rule")
        return answer

    # ================================================================
    # 属性
    # ================================================================

    @property
    def parameter_count(self) -> int:
        return len(self._index.parameters) if self._index else 0

    @property
    def parameter_names(self) -> list:
        if self._index:
            return [p.name for p in self._index.parameters]
        return []

    @property
    def is_deep_agent_available(self) -> bool:
        return self._agent is not None
