from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import httpx

from agent.config import AgentConfig
from agent.session import Session
from cad_parser import CADParser
from cad_understanding.component_recognizer import ComponentRecognizer
from cad_understanding.parameter_index import ParameterIndex
from cad_understanding.scale_inferencer import ScaleInferencer
from nlp_interface.prompt_templates import SYSTEM_PROMPT
from nlp_interface.query_processor import QueryProcessor

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: Optional[AgentConfig] = None):
        self._config = config or AgentConfig()
        self._session = Session()
        self._query_processor: Optional[QueryProcessor] = None
        self._index = None
        self._llm_available = False
        self._cad_document = None

    def load_cad(self, file_path: Optional[str] = None):
        path = file_path or self._config.cad_file
        if not path:
            raise ValueError("No CAD file specified.")

        if not os.path.isfile(path):
            raise FileNotFoundError(f"CAD file not found: {path}")

        logger.info("Loading CAD file: %s", path)

        index_path = self._config.index_path
        if os.path.isfile(str(index_path)):
            logger.info("Loading cached index: %s", index_path)
            self._index = ParameterIndex.load(str(index_path))
        else:
            logger.info("Parsing CAD and building index...")
            parser = CADParser(path)
            doc = parser.parse()

            unit = ScaleInferencer().infer(doc)
            components = ComponentRecognizer().recognize(doc)

            idx = ParameterIndex()
            self._index = idx.build(doc)
            self._index.components = components
            self._cad_document = doc

            os.makedirs(os.path.dirname(str(index_path)) or ".", exist_ok=True)
            idx.save(str(index_path))

        for param in self._index.parameters:
            if param.value == 0 and param.raw_text:
                continue
            if not param.unit or param.unit == "inches":
                param.unit = "mm"

        self._query_processor = QueryProcessor(self._index)
        self._llm_available = self._check_llm()

        logger.info("Agent ready. %d parameters indexed. LLM: %s",
                     len(self._index.parameters), "enabled" if self._llm_available else "disabled")

    def ask(self, question: str) -> str:
        if self._query_processor is None:
            raise RuntimeError("Agent not initialized. Call load_cad() first.")

        self._session.add("user", question)

        answer = self._query_processor.process(question)

        if self._llm_available and (self._is_fallback_answer(answer) or self._is_complex_question(question)):
            llm_answer = self._ask_llm(question)
            if llm_answer:
                answer = llm_answer

        self._session.add("assistant", answer)
        return answer

    def _is_fallback_answer(self, answer: str) -> bool:
        if "未找到" in answer or "抱歉" in answer:
            return True
        if "没有" in answer and ("参数" in answer or "数据" in answer or "图纸" in answer):
            return True
        if "图纸中" in answer and "未" in answer:
            return True
        if "= 0.0" in answer:
            return True
        if "可查询的参数" in answer:
            return True
        return False

    def _is_complex_question(self, question: str) -> bool:
        if re.search(r"\d+.*几[处个]", question) or re.search(r"几[处个].*\d+", question):
            return False
        if re.search(r"几[处个]$", question) and re.search(r"\d", question):
            return False
        complex_patterns = [
            r"分别|组成|结构",
            r"什么材料|什么用|做什么|技术要求|技术条件",
            r"性能|测试|要求|温度|范围",
            r"耐[油酸寒热]|抗[病氧]",
            r"部品|部件",
            # 扩展模式：覆盖标题栏/签字栏/技术要求问题
            r"名称|图号|比例|图幅|分类|版本号|版本",
            r"设计|审核|工艺|标准化|批准|归档",
            r"日期|签名|签字|是谁|喷涂|颜色|颜色",
            r"外观|缺陷|缺陷|折弯|半径|吊装|吊绳|堆码|堆码",
            r"材质|材料|规格|标准|温度|湿度|尺寸检测",
            r"序号|编号|索引|位置",
        ]
        return any(re.search(p, question) for p in complex_patterns)

    def _check_llm(self) -> bool:
        api_key = self._config.llm_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        return bool(api_key)

    def _ask_llm(self, question: str) -> Optional[str]:
        try:
            params_context = self._build_params_context()
            system = SYSTEM_PROMPT.format(parameters_context=params_context)

            api_key = self._config.llm_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
            base_url = self._config.llm_base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
            model = self._config.llm_model or os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro[1m]")

            history = [{"role": m.role, "content": m.content} for m in self._session.history[-6:]]

            response = httpx.post(
                f"{base_url}/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": history + [{"role": "user", "content": question}],
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", [])
                for block in content:
                    if block.get("type") == "text" and block.get("text"):
                        return block["text"]
        except Exception as e:
            logger.warning("LLM query failed: %s", e)

        return None

    def _build_params_context(self) -> str:
        if not self._index:
            return "无可用参数"

        lines = ["===== 图纸参数 ====="]
        for p in self._index.parameters:
            if p.value == 0 and p.raw_text:
                lines.append(f"- {p.name}: {p.raw_text} (图层: {p.layer})")
            else:
                lines.append(f"- {p.name} = {p.value} {p.unit} (ID: {p.source_dim_id}, 图层: {p.layer})")

        # 添加全部文本注释
        if self._cad_document:
            lines.append("\n===== 图纸全部文字注释 =====")
            for t in self._cad_document.text_annotations:
                txt = t.text.strip().replace("\n", " \\n ")
                if txt:
                    lines.append(f"[图层:{t.layer}] (位置:{t.position.get('x',0):.0f},{t.position.get('y',0):.0f}): {txt}")

        return "\n".join(lines)

    @property
    def session(self) -> Session:
        return self._session

    @property
    def parameter_count(self) -> int:
        return len(self._index.parameters) if self._index else 0

    @property
    def parameter_names(self) -> list[str]:
        if self._index:
            return [p.name for p in self._index.parameters]
        return []
