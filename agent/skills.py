"""
Skills 注册表 — 管理所有 CAD 领域 Skill。

遵循 Deep Agents Skills 规范的三阶段渐进式加载：
  Phase 1: discover() → 仅返回技能名称列表
  Phase 2: load_metadata() → 返回 frontmatter 元数据
  Phase 3: load_full() → 返回完整 SKILL.md 内容
"""
from pathlib import Path
from typing import Dict, List, Optional


class SkillRegistry:
    """CAD 领域 Skills 注册表"""

    SKILLS_DIR = Path(__file__).parent.parent / "skills"

    def __init__(self):
        self._skills: Dict[str, dict] = {}
        self._discovered: List[str] = []

    # ---- Phase 1: 发现 ----

    def discover(self) -> List[str]:
        """发现所有可用 Skill（仅返回名称列表）"""
        if self._discovered:
            return self._discovered

        names = []
        if self.SKILLS_DIR.exists():
            for d in sorted(self.SKILLS_DIR.iterdir()):
                if d.is_dir() and (d / "SKILL.md").exists():
                    names.append(d.name)
        self._discovered = names
        return names

    # ---- Phase 2: 元数据 ----

    def load_metadata(self, skill_name: str) -> Optional[dict]:
        """加载 Skill 元数据（frontmatter 部分）"""
        cached = self._skills.get(skill_name)
        if cached and "metadata" in cached:
            return cached["metadata"]

        content = self._read_skill_file(skill_name)
        if not content:
            return None

        metadata = self._parse_frontmatter(content)

        self._skills.setdefault(skill_name, {})
        self._skills[skill_name]["metadata"] = metadata
        return metadata

    # ---- Phase 3: 全文 ----

    def load_full(self, skill_name: str) -> Optional[str]:
        """加载 Skill 完整内容（全文）"""
        cached = self._skills.get(skill_name)
        if cached and "body" in cached:
            return cached["body"]

        content = self._read_skill_file(skill_name)
        if not content:
            return None

        self._skills.setdefault(skill_name, {})
        self._skills[skill_name]["body"] = content
        return content

    # ---- 工具方法 ----

    def get_tool_names(self, skill_name: str) -> List[str]:
        """获取 Skill 声明的工具列表"""
        meta = self.load_metadata(skill_name)
        if not meta:
            return []
        tools = meta.get("tools", "")
        if isinstance(tools, str):
            return [t.strip() for t in tools.split(",") if t.strip()]
        return tools

    def build_system_prompt(self, skill_names: Optional[List[str]] = None) -> str:
        """
        构建 Agent 系统提示词，包含指定 Skills 的元数据。
        如果未指定 skill_names，则加载所有已发现的 Skill。
        """
        names = skill_names or self.discover()
        parts = ["## 可用能力 (Skills)\n"]
        for name in names:
            meta = self.load_metadata(name)
            if meta:
                desc = meta.get("description", "").strip()
                tools = meta.get("tools", "")
                parts.append(f"### {name}")
                parts.append(f"{desc}\n")
                if tools:
                    parts.append(f"工具: {tools}\n")
        return "\n".join(parts)

    def get_all_skill_descriptions(self) -> Dict[str, str]:
        """返回所有 Skill 的名称→描述映射"""
        result = {}
        for name in self.discover():
            meta = self.load_metadata(name)
            if meta:
                result[name] = meta.get("description", "").strip()
        return result

    # ---- 内部方法 ----

    def _read_skill_file(self, skill_name: str) -> Optional[str]:
        skill_file = self.SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_file.exists():
            return None
        with open(skill_file, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        """解析 YAML frontmatter（简化实现）"""
        metadata = {}
        if not content.startswith("---"):
            return metadata

        parts = content.split("---", 2)
        if len(parts) < 2:
            return metadata

        current_key: Optional[str] = None
        list_values: List[str] = []

        for line in parts[1].strip().split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # 列表项（如 - parse_cad_file）
            if stripped.startswith("- ") and current_key:
                list_values.append(stripped[2:].strip())
                continue

            # 如果有缓存的列表，先保存
            if current_key and list_values:
                metadata[current_key] = ", ".join(list_values)
                list_values = []
                current_key = None

            # key: value 行
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()

                # 检查 value 是否为内联列表
                if val.startswith("[") and val.endswith("]"):
                    val = val[1:-1].strip()
                    metadata[key] = val
                elif val:
                    metadata[key] = val
                else:
                    # value 为空 → 可能下一行是列表
                    current_key = key

        # 处理最后一组
        if current_key and list_values:
            metadata[current_key] = ", ".join(list_values)

        return metadata
