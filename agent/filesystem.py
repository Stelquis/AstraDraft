"""
CAD 图纸参数索引的虚拟文件系统后端。

将 ParameterIndexData 导出为结构化文件，供 Deep Agent 的
ls / read_file / grep 工具按需查询，避免全量注入 prompt。

用法:
    from agent.filesystem import CADIndexFilesystem

    fs = CADIndexFilesystem(base_dir="data/fs")
    index_dir = fs.export_index(index_data, "filter_modify.dwg")
"""
import json
import os
from pathlib import Path
from typing import List, Optional

from cad.understanding.models import Parameter, ParameterIndexData


class CADIndexFilesystem:
    """将参数索引导出为可查询的文件系统目录"""

    def __init__(self, base_dir: str = "data/fs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def export_index(
        self, index: ParameterIndexData, cad_filename: str
    ) -> str:
        """
        将参数索引导出为结构化文件。

        Returns:
            str: 索引目录的绝对路径
        """
        safe_name = cad_filename.replace(".", "_")
        doc_dir = self.base_dir / safe_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        # 1. 完整参数 JSON（供程序化查询）
        params_file = doc_dir / "parameters.json"
        params_data = [
            {
                "name": p.name,
                "value": p.value,
                "unit": p.unit,
                "layer": p.layer,
                "raw_text": p.raw_text,
                "aliases": p.aliases,
                "source_dim_id": p.source_dim_id,
            }
            for p in index.parameters
        ]
        with open(params_file, "w", encoding="utf-8") as f:
            json.dump(params_data, f, ensure_ascii=False, indent=2)

        # 2. 分类型清单（便于 grep / read_file 快速浏览）
        dims = [p for p in index.parameters if p.value > 0]
        infos = [p for p in index.parameters if p.value == 0]

        self._write_dimension_list(doc_dir / "dimensions.txt", dims)
        self._write_info_list(doc_dir / "info_params.txt", infos)
        self._write_summary(doc_dir / "summary.md", index, cad_filename)

        return str(doc_dir)

    # ---- 内部写入方法 ----

    @staticmethod
    def _write_dimension_list(path: Path, params: List[Parameter]):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# 尺寸参数（共 {len(params)} 个）\n\n")
            if not params:
                f.write("(无)\n")
                return
            # 按数值降序排列
            sorted_params = sorted(params, key=lambda p: -p.value)
            for p in sorted_params:
                f.write(
                    f"{p.name}: {p.value} {p.unit}"
                    f"  [图层: {p.layer}]  [别名: {', '.join(p.aliases[:5] if p.aliases else [])}]\n"
                )

    @staticmethod
    def _write_info_list(path: Path, params: List[Parameter]):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# 信息参数（共 {len(params)} 个）\n\n")
            if not params:
                f.write("(无)\n")
                return
            for p in params:
                # 截断过长的原始文本
                raw = p.raw_text[:300].replace("\n", " ").replace("|", " ")
                f.write(f"{p.name}: {raw}  [图层: {p.layer}]\n")

    @staticmethod
    def _write_summary(
        path: Path, index: ParameterIndexData, filename: str
    ):
        total = len(index.parameters)
        dims = len([p for p in index.parameters if p.value > 0])
        infos = total - dims
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# CAD 图纸索引摘要\n\n")
            f.write(f"- **文件**: {filename}\n")
            f.write(f"- **总参数数**: {total}\n")
            f.write(f"- **尺寸参数**: {dims}\n")
            f.write(f"- **信息参数**: {infos}\n")
            f.write(f"- **部件数**: {len(index.components)}\n")
            f.write(f"\n## 文件列表\n")
            f.write(f"- [parameters.json](./parameters.json) — 完整参数数据\n")
            f.write(f"- [dimensions.txt](./dimensions.txt) — 尺寸参数列表\n")
            f.write(f"- [info_params.txt](./info_params.txt) — 信息参数列表\n")
