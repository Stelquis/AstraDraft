from __future__ import annotations

import logging
import re
from typing import List, Optional

from cad_understanding.models import Parameter, ParameterIndexData
from cad_understanding.semantic_mapper import SemanticMapper
from nlp_interface.intent_classifier import IntentClassifier
from nlp_interface.parameter_parser import ParameterParser
from nlp_interface.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class QueryProcessor:
    def __init__(self, index: ParameterIndexData):
        self._index = index
        self._classifier = IntentClassifier()
        self._parser = ParameterParser(index)
        self._mapper = SemanticMapper(index)
        self._formatter = ResponseFormatter()

    def process(self, question: str) -> str:
        intent = self._classifier.classify(question)
        logger.info("Intent: %s, Question: %s", intent, question)

        result = self._try_superlative(question)
        if result:
            return result

        result = self._try_count_query(question)
        if result:
            return result

        result = self._try_value_search(question)
        if result:
            return result

        if intent == "query_multi":
            return self._formatter.format_all(self._index.parameters)

        if intent == "query_compare":
            targets_a, targets_b = self._parser.extract_compare_targets(question)
            params_a = [self._mapper.find_parameter(t) for t in targets_a]
            params_b = [self._mapper.find_parameter(t) for t in targets_b]
            params_a = [p for p in params_a if p]
            params_b = [p for p in params_b if p]
            if params_a and params_b:
                return self._formatter.format_compare(params_a, params_b)

        targets = self._parser.extract_targets(question)
        if targets:
            results = []
            for t in targets:
                param = self._mapper.find_parameter(t)
                if param:
                    results.append(param)
            if results:
                if len(results) == 1:
                    return self._formatter.format_single(results[0])
                return self._formatter.format_multiple(results)

        param = self._mapper.find_parameter(question)
        if param:
            return self._formatter.format_single(param)

        return self._formatter.format_no_match(question, self._index.parameters)

    def _try_superlative(self, question: str) -> Optional[str]:
        dims = [p for p in self._index.parameters if p.value > 0 and p.unit == "mm"]

        if re.search(r"有多大|总体尺寸|外框尺寸|整体尺寸|外形尺寸", question):
            top2 = sorted(dims, key=lambda p: -p.value)[:2]
            if top2:
                return self._formatter.format_multiple(top2)

        if re.search(r"最大|最长|最高|最宽", question):
            if "半径" in question or "圆角" in question or "R" in question:
                radii = [p for p in dims if p.name.startswith("半径")]
                if radii:
                    best = max(radii, key=lambda p: p.value)
                    return f"最大的圆角半径是 **{best.value} {best.unit}** ({best.name})"
            best = max(dims, key=lambda p: p.value) if dims else None
            if best:
                return f"最大的尺寸是 **{best.value} {best.unit}** ({best.name})"

        if re.search(r"最小|最短|最低|最窄", question):
            if "半径" in question or "圆角" in question or "R" in question:
                radii = [p for p in dims if p.name.startswith("半径")]
                if radii:
                    best = min(radii, key=lambda p: p.value)
                    return f"最小的圆角半径是 **{best.value} {best.unit}** ({best.name})"
            nonzero = [p for p in dims if p.value > 0]
            if nonzero:
                best = min(nonzero, key=lambda p: p.value)
                return f"最小的尺寸是 **{best.value} {best.unit}** ({best.name})"

        return None

    def _try_value_search(self, question: str) -> Optional[str]:
        nums = re.findall(r"(\d+\.?\d*)\s*(?:mm|MM|毫米)?", question)
        if not nums:
            return None

        target_val = float(nums[0])
        matches = [
            p for p in self._index.parameters
            if abs(p.value - target_val) < 0.5 and p.unit == "mm"
        ]

        if not matches:
            return None

        if re.search(r"代表什么|是什么|在哪里|哪[个里]", question):
            lines = []
            for p in matches:
                lines.append(f"- **{p.value} mm** ({p.name}), 图层: {p.layer}")
            return f"尺寸 {target_val}mm 在图纸中出现 {len(matches)} 处：\n" + "\n".join(lines)

        return self._formatter.format_multiple(matches)

    def _try_count_query(self, question: str) -> Optional[str]:
        if not re.search(r"几[处个处]|多少[处个]|有[几多少]", question):
            return None

        nums = re.findall(r"(\d+\.?\d*)\s*(?:mm)?", question)
        if not nums:
            return None

        target_val = float(nums[0])
        matches = [
            p for p in self._index.parameters
            if abs(p.value - target_val) < 0.5 and p.unit == "mm"
        ]

        if matches:
            return f"尺寸 **{target_val}mm** 在图纸中共出现 **{len(matches)}** 处。"
        return f"尺寸 {target_val}mm 在图纸中未找到。"
