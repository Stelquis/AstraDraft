from __future__ import annotations

import logging
import re
from typing import Optional

import jieba

logger = logging.getLogger(__name__)

_jieba_initialized = False


def _ensure_jieba():
    global _jieba_initialized
    if not _jieba_initialized:
        jieba.setLogLevel(logging.WARNING)
        _jieba_initialized = True


INTENT_PATTERNS = {
    "query_parameter": [
        r"(.+?)的(.+?)是",
        r"(.+?)的(.+?)多少",
        r"(.+?)的(.+?)多[少大高宽长]",
        r"(.+?)有[多几](.+)",
        r"查询(.+)",
        r"(?:请问|请告诉我)?(.+?)的(.+)",
    ],
    "query_multi": [
        r"有哪些参数",
        r"所有参数",
        r"列出.*参数",
        r"图纸.*信息",
        r"什么参数",
    ],
    "query_compare": [
        r"(.+?)和(.+?)哪",
        r"(.+?)与(.+?)比较",
        r"比较(.+?)和(.+)",
    ],
    "query_info": [
        r"什么[用做]",
        r"什么零件",
        r"图纸.*信息",
        r"介绍一下",
    ],
}


class IntentClassifier:
    def __init__(self):
        _ensure_jieba()

    def classify(self, question: str) -> str:
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question):
                    logger.debug("Classified '%s' as '%s'", question, intent)
                    return intent
        return "query_parameter"
