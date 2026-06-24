from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Session:
    history: List[Message] = field(default_factory=list)

    def add(self, role: str, content: str):
        self.history.append(Message(role=role, content=content))

    def clear(self):
        self.history.clear()

    @property
    def turn_count(self) -> int:
        return len(self.history) // 2
