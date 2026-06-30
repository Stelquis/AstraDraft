"""
DeepAstraDraft 记忆层。

短期记忆：Checkpointer（对话历史持久化）
长期记忆：Store（用户偏好、参数别名学习、评估历史）

Phase 2: InMemoryStore（内存版）
Phase 4: PostgresStore（生产版）
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver


class AstraDraftMemory:
    """CAD Agent 记忆管理"""

    def __init__(self, data_dir: str = "data/memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 短期记忆（Checkpointer）
        self.checkpointer = MemorySaver()

        # 长期记忆（JSON 文件存储）
        self._store_file = self.data_dir / "store.json"
        self._store: Dict[str, Any] = self._load_store()

    # ---- 存储读写 ----

    def _load_store(self) -> dict:
        if self._store_file.exists():
            try:
                with open(self._store_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "user_preferences": {},      # 用户偏好（常用图纸路径等）
            "learned_aliases": {},       # 学习到的参数别名
            "query_history": [],         # 查询历史摘要
            "evaluation_results": [],    # 评估结果
        }

    def save_store(self):
        self._store_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_file, "w", encoding="utf-8") as f:
            json.dump(self._store, f, ensure_ascii=False, indent=2)

    # ---- 用户偏好 ----

    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        self._store["user_preferences"][key] = value
        self.save_store()

    def get_preference(self, key: str) -> Optional[Any]:
        """获取用户偏好"""
        return self._store["user_preferences"].get(key)

    def get_all_preferences(self) -> dict:
        return dict(self._store["user_preferences"])

    # ---- 别名学习 ----

    def learn_alias(self, param_name: str, user_term: str):
        """记录用户使用的非标准术语，下次自动匹配"""
        aliases = self._store["learned_aliases"]
        if param_name not in aliases:
            aliases[param_name] = []
        if user_term not in aliases[param_name]:
            aliases[param_name].append(user_term)
            self.save_store()

    def get_learned_aliases(self, param_name: str) -> List[str]:
        """获取已学习的别名"""
        return self._store["learned_aliases"].get(param_name, [])

    def get_all_learned_aliases(self) -> Dict[str, List[str]]:
        return dict(self._store["learned_aliases"])

    # ---- 查询历史 ----

    def record_query(self, question: str, answer: str, source: str = "rule"):
        """记录一次查询"""
        self._store["query_history"].append({
            "question": question[:200],
            "answer": answer[:200],
            "source": source,
        })
        # 只保留最近 500 条
        if len(self._store["query_history"]) > 500:
            self._store["query_history"] = self._store["query_history"][-500:]
        self.save_store()

    def get_recent_queries(self, n: int = 20) -> List[dict]:
        """获取最近 n 条查询"""
        return self._store["query_history"][-n:]

    def get_query_stats(self) -> dict:
        """查询统计"""
        history = self._store["query_history"]
        if not history:
            return {"total": 0, "rule_count": 0, "llm_count": 0}
        rule = sum(1 for h in history if h["source"] == "rule")
        llm = sum(1 for h in history if h["source"] == "llm")
        return {
            "total": len(history),
            "rule_count": rule,
            "llm_count": llm,
            "llm_ratio": f"{llm / len(history) * 100:.1f}%" if history else "0%",
        }

    # ---- 评估记录 ----

    def record_evaluation(self, result: dict):
        """记录评估结果"""
        self._store["evaluation_results"].append(result)
        self.save_store()

    def get_latest_evaluation(self) -> Optional[dict]:
        """获取最近一次评估结果"""
        results = self._store["evaluation_results"]
        return results[-1] if results else None

    # ---- 重置 ----

    def clear_query_history(self):
        """清空查询历史"""
        self._store["query_history"] = []
        self.save_store()

    def clear_all(self):
        """清空所有长期记忆"""
        self._store = {
            "user_preferences": {},
            "learned_aliases": {},
            "query_history": [],
            "evaluation_results": [],
        }
        self.save_store()
