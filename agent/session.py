from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Session:
    history: List[Message] = field(default_factory=list)
    _memory: Optional[object] = None  # AstraDraftMemory 引用（Phase 2+）

    def add(self, role: str, content: str):
        self.history.append(Message(role=role, content=content))

    def clear(self):
        self.history.clear()

    @property
    def turn_count(self) -> int:
        return len(self.history) // 2

    # Phase 2: 记忆集成
    def set_memory(self, memory: object):
        """绑定 AstraDraftMemory 实例"""
        self._memory = memory

    def to_messages(self) -> list:
        """转换为 LangChain 消息列表"""
        messages = []
        for m in self.history:
            if m.role == "user":
                from langchain_core.messages import HumanMessage
                messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=m.content))
            elif m.role == "system":
                from langchain_core.messages import SystemMessage
                messages.append(SystemMessage(content=m.content))
        return messages

    def record_to_memory(self, question: str, answer: str, source: str = "rule"):
        """将当前 Q&A 记录到长期记忆"""
        if self._memory:
            self._memory.record_query(question, answer, source)

    def learn_alias(self, param_name: str, user_term: str):
        """学习用户自定义别名"""
        if self._memory:
            self._memory.learn_alias(param_name, user_term)
