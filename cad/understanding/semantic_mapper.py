from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import jieba

from cad.understanding.models import Parameter, ParameterIndexData

logger = logging.getLogger(__name__)

SYNONYM_MAP: Dict[str, List[str]] = {
    "高度": ["高", "H", "height", "高度", "总高", "总高度"],
    "宽度": ["宽", "W", "width", "宽度", "总宽", "总宽度"],
    "长度": ["长", "L", "length", "长度", "总长", "总长度"],
    "直径": ["孔径", "D", "diameter", "直径", "孔直径"],
    "半径": ["R", "radius", "半径", "圆角", "fillet", "倒角"],
    "厚度": ["厚", "T", "thickness", "厚度", "板厚"],
    "间距": ["间隔", "gap", "spacing", "间距", "距离"],
    "孔径": ["孔直径", "mesh size", "孔径", "网孔", "目", "目数", "mesh", "每英寸"],
    "外径": ["外径", "OD", "外直径"],
    "内径": ["内径", "ID", "内直径"],
    # 材料/树脂相关同义词
    "材质": ["材质", "材料", "material", "树脂", "resin", "原料"],
    # 成形方法
    "成形方法": ["成形", "成型", "注射", "注塑", "模压", "压缩", "挤压", "加工方法", "加工方式"],
    # 性能
    "耐油性": ["耐油", "耐油性", "oil resistance"],
    "耐酸性": ["耐酸", "耐酸性", "acid resistance"],
    "耐寒性": ["耐寒", "耐寒性", "cold resistance"],
    "耐热性": ["耐热", "耐热性", "heat resistance"],
    # 颜色
    "色调": ["色调", "颜色", "color", "色"],
    # 防菌/抗菌
    "防菌": ["防菌", "抗菌", "防菌型", "antibacterial", "anti-bacterial"],
}

_jieba_initialized = False


def _ensure_jieba():
    global _jieba_initialized
    if not _jieba_initialized:
        jieba.setLogLevel(logging.WARNING)
        _jieba_initialized = True


class SemanticMapper:
    def __init__(self, index: ParameterIndexData):
        self._index = index
        self._alias_index: Dict[str, Parameter] = {}
        self._build_alias_index()

    def _build_alias_index(self):
        for param in self._index.parameters:
            for alias in param.aliases:
                self._alias_index[alias.lower()] = param
            self._alias_index[param.name.lower()] = param

    def find_parameter(self, query: str) -> Optional[Parameter]:
        _ensure_jieba()
        query_lower = query.lower().strip()

        if query_lower in self._alias_index:
            return self._alias_index[query_lower]

        words = list(jieba.cut(query))

        best_match: Optional[Parameter] = None
        best_score = 0

        for param in self._index.parameters:
            score = self._score_match(words, param, query_lower)
            if score > best_score:
                best_score = score
                best_match = param

        return best_match if best_score > 0 else None

    def find_all_parameters(self) -> List[Parameter]:
        return self._index.parameters

    @staticmethod
    def _score_match(words: List[str], param: Parameter, query: str) -> int:
        score = 0
        all_names = [param.name.lower()] + [a.lower() for a in param.aliases]

        for name in all_names:
            if name in query:
                score += 10
            for word in words:
                if word.lower() == name:
                    score += 5
                elif name in word.lower() or word.lower() in name:
                    score += 2

        # 主名称分词后匹配加分（"滤网材料" 中含 "滤网" 匹配查询中的"滤网"）
        for word in words:
            wl = word.lower()
            if len(wl) >= 2 and wl in param.name.lower():
                score += 5

        for cn_key, synonyms in SYNONYM_MAP.items():
            query_has_synonym = any(s in query for s in synonyms)
            param_has_name = any(s in all_names for s in synonyms) or param.name in synonyms
            if query_has_synonym and param_has_name:
                score += 12

        return score
