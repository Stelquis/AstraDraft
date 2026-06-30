from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

import jieba
import jieba.analyse

from cad.understanding.models import Parameter, ParameterIndexData

logger = logging.getLogger(__name__)

_jieba_initialized = False


def _ensure_jieba():
    global _jieba_initialized
    if not _jieba_initialized:
        jieba.setLogLevel(logging.WARNING)
        _jieba_initialized = True


class ParameterParser:
    def __init__(self, index: ParameterIndexData):
        _ensure_jieba()
        self._index = index
        self._param_keywords = self._build_keywords()

    def _build_keywords(self) -> Dict[str, str]:
        keywords = {}
        for param in self._index.parameters:
            keywords[param.name.lower()] = param.name
            for alias in param.aliases:
                keywords[alias.lower()] = param.name
        return keywords

    def extract_targets(self, question: str) -> List[str]:
        words = list(jieba.cut(question))
        matched = []

        for word in words:
            wl = word.lower().strip()
            if wl in self._param_keywords:
                matched.append(self._param_keywords[wl])

        if matched:
            return matched

        for param in self._index.parameters:
            if param.name in question:
                matched.append(param.name)
                continue
            for alias in param.aliases:
                if alias in question:
                    matched.append(param.name)
                    break

        if not matched:
            tfidf_words = jieba.analyse.extract_tags(question, topK=5)
            for w in tfidf_words:
                wl = w.lower()
                if wl in self._param_keywords:
                    matched.append(self._param_keywords[wl])

        return matched

    def extract_compare_targets(self, question: str) -> Tuple[List[str], List[str]]:
        compare_patterns = [
            r"(.+?)(?:和|与|跟)(.+?)(?:哪个|哪边|比较|对比)",
            r"(?:比较|对比)(.+?)(?:和|与|跟)(.+)",
        ]
        for pattern in compare_patterns:
            m = re.search(pattern, question)
            if m:
                part_a = self.extract_targets(m.group(1))
                part_b = self.extract_targets(m.group(2))
                return part_a, part_b
        return [], []
