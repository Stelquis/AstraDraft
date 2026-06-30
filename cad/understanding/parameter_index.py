from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List

from cad.parser.models import CADDocument, Dimension, TextAnnotation
from cad.understanding.models import Parameter, ParameterIndexData

logger = logging.getLogger(__name__)


class ParameterIndex:
    def __init__(self):
        self._params: List[Parameter] = []
        self._data: ParameterIndexData | None = None

    def build(self, doc: CADDocument) -> ParameterIndexData:
        self._params.clear()

        self._extract_from_dimensions(doc.dimensions, doc.text_annotations)
        self._extract_from_text(doc.text_annotations)
        self._add_info_params(doc.text_annotations)
        self._assign_semantic_aliases()

        self._data = ParameterIndexData(
            document=os.path.basename(doc.file_path),
            parameters=self._params,
        )
        logger.info("Built parameter index with %d parameters", len(self._params))
        return self._data

    def save(self, output_path: str):
        if self._data is None:
            raise RuntimeError("No index built yet. Call build() first.")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self._data.model_dump(), f, ensure_ascii=False, indent=2)
        logger.info("Saved index to %s", output_path)

    @staticmethod
    def load(path: str) -> ParameterIndexData:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ParameterIndexData(**data)

    def query(self, name: str) -> Parameter | None:
        name_lower = name.lower()
        for p in self._params:
            if p.name.lower() == name_lower:
                return p
            for alias in p.aliases:
                if alias.lower() == name_lower:
                    return p
        return None

    def _extract_from_dimensions(self, dimensions: List[Dimension], texts: List[TextAnnotation]):
        text_positions = []
        for t in texts:
            if t.position and "x" in t.position and "y" in t.position:
                text_positions.append(t)

        for dim in dimensions:
            if dim.measurement is None or dim.measurement == 0:
                continue

            nearby_text = self._find_nearby_text(dim, text_positions, max_dist=80)
            name, aliases = self._infer_param_name(dim, nearby_text)

            self._params.append(Parameter(
                name=name,
                value=round(dim.measurement, dim.precision),
                source_dim_id=dim.id,
                aliases=aliases,
                layer=dim.layer,
                raw_text=dim.text,
            ))

    def _extract_from_text(self, texts: List[TextAnnotation]):
        kv_pattern = re.compile(
            r"([A-Za-z\u4e00-\u9fff]+)\s*[=＝:：]\s*([+-]?\d+\.?\d*)\s*(mm|MM|cm|CM|m|M)?",
        )
        for ann in texts:
            for match in kv_pattern.finditer(ann.text):
                raw_name = match.group(1).strip()
                value = float(match.group(2))
                unit = (match.group(3) or "mm").lower()

                name, aliases = self._normalize_name(raw_name)
                self._params.append(Parameter(
                    name=name,
                    value=round(value, 2),
                    unit=unit,
                    aliases=aliases,
                    layer=ann.layer,
                    raw_text=ann.text,
                ))

    @staticmethod
    def _infer_param_name(dim: Dimension, nearby_text: List[TextAnnotation] | None = None) -> tuple[str, List[str]]:
        text = dim.text.strip()
        if text and text not in ("(<>)", "()", ""):
            cleaned = re.sub(r"[^\d.\-+]", "", text)
            if cleaned:
                pass
            else:
                return _normalize_name(text)

        if nearby_text:
            for t in nearby_text:
                txt = t.text.strip()
                if re.search(r'[\u4e00-\u9fff]', txt) and len(txt) > 1:
                    return _normalize_name(txt)

        return _build_name_from_type(dim), _build_aliases(dim)

    @staticmethod
    def _find_nearby_text(dim: Dimension, text_positions: List[TextAnnotation], max_dist: float) -> List[TextAnnotation]:
        if not dim.points or not text_positions:
            return []

        dim_points = []
        for key in ("text_midpoint", "defpoint", "defpoint2", "defpoint3"):
            if key in dim.points:
                dim_points.append(dim.points[key])

        if not dim_points:
            return []

        dim_cx = sum(p[0] for p in dim_points) / len(dim_points)
        dim_cy = sum(p[1] for p in dim_points) / len(dim_points)

        nearby = []
        for t in text_positions:
            tx, ty = t.position["x"], t.position["y"]
            dist = ((tx - dim_cx) ** 2 + (ty - dim_cy) ** 2) ** 0.5
            if dist < max_dist:
                nearby.append(t)

        return nearby

    def _add_info_params(self, texts: List[TextAnnotation]):
        seen = set()
        all_text = " ".join(t.text.strip() for t in texts)

        for ann in texts:
            txt = ann.text.strip()

            if ("材 质" in txt or ("材质" in txt and "材料转移" not in txt)) and "材质" not in seen:
                seen.add("材质")
                self._params.append(Parameter(
                    name="材质", value=0, unit="",
                    aliases=["材质", "材料", "material"],
                    layer=ann.layer, raw_text=txt,
                ))

            if ("色 调" in txt or "色调" in txt) and "色调" not in seen:
                all_colors = []
                for t2 in texts:
                    c = t2.text.strip()
                    if c in ("黑色", "浅蓝色", "白色"):
                        all_colors.append(c)
                if all_colors:
                    seen.add("色调")
                    self._params.append(Parameter(
                        name="色调", value=0, unit="",
                        aliases=["色调", "颜色", "color", "色"],
                        layer="", raw_text=", ".join(all_colors),
                    ))

            if "成形方法" in txt and "成形方法" not in seen:
                forming_texts = []
                for t2 in texts:
                    if "注射" in t2.text or "挤压" in t2.text or "压缩" in t2.text or "模压" in t2.text:
                        forming_texts.append(t2.text.strip())
                if forming_texts:
                    seen.add("成形方法")
                    self._params.append(Parameter(
                        name="成形方法", value=0, unit="",
                        aliases=["成形方法", "成形", "成型", "加工方法", "注塑"],
                        layer="", raw_text=" | ".join(forming_texts),
                    ))
                elif "成形方法" not in seen:
                    seen.add("成形方法")
                    self._params.append(Parameter(
                        name="成形方法", value=0, unit="",
                        aliases=["成形方法", "成形", "成型", "加工方法", "注塑"],
                        layer=ann.layer, raw_text=txt,
                    ))

            if ("部品 1" in txt or "边框" in txt) and "PS" in txt and "部品_边框" not in seen:
                seen.add("部品_边框")
                self._params.append(Parameter(
                    name="部品_边框", value=0, unit="",
                    aliases=["边框", "边框材料", "frame", "部品1"],
                    layer=ann.layer, raw_text=txt,
                ))

            if ("滤 网" in txt or "滤网" in txt) and "聚丙烯" in txt and "滤网材料" not in seen:
                seen.add("滤网材料")
                self._params.append(Parameter(
                    name="滤网材料", value=0, unit="",
                    aliases=["滤网", "滤网材料", "filter mesh", "mesh", "部品2", "部品3"],
                    layer=ann.layer, raw_text=txt,
                ))

            if "标 贴" in txt and "标贴" not in seen:
                for t2 in texts:
                    if "铜版纸" in t2.text:
                        seen.add("标贴")
                        self._params.append(Parameter(
                            name="标贴", value=0, unit="",
                            aliases=["标贴", "标签", "label"],
                            layer=t2.layer, raw_text=t2.text.strip(),
                        ))
                        break

        if "技术要求" not in seen:
            for t in texts:
                if "PS注塑" in t.text or "模压加工" in t.text:
                    seen.add("技术要求")
                    self._params.append(Parameter(
                        name="技术要求", value=0, unit="",
                        aliases=["技术要求", "加工要求"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break

        if "产品名称" not in seen and "过滤网" in all_text:
            seen.add("产品名称")
            self._params.append(Parameter(
                name="产品名称", value=0, unit="",
                aliases=["产品", "产品名称", "零件名", "图名"],
                layer="", raw_text="过滤网",
            ))

        # --- 编织方式 ---
        if "编织方式" not in seen:
            for t in texts:
                txt = t.text.strip()
                if "蜂窝形" in txt or "编织" in txt:
                    seen.add("编织方式")
                    self._params.append(Parameter(
                        name="编织方式", value=0, unit="",
                        aliases=["编织方式", "编织", "网孔形状", "weave", "weave pattern"],
                        layer=t.layer, raw_text=txt,
                    ))
                    break

        # --- 防菌/抗菌 ---
        if "防菌型" not in seen:
            for t in texts:
                txt = t.text.strip()
                if "防菌" in txt or "抗菌" in txt:
                    seen.add("防菌型")
                    self._params.append(Parameter(
                        name="防菌型", value=0, unit="",
                        aliases=["防菌", "防菌型", "抗菌", "抗菌型", "antibacterial"],
                        layer=t.layer, raw_text=txt,
                    ))
                    break

        # --- 退火处理 ---
        if "退火处理" not in seen:
            for t in texts:
                txt = t.text.strip()
                if "退火" in txt:
                    seen.add("退火处理")
                    self._params.append(Parameter(
                        name="退火处理", value=0, unit="",
                        aliases=["退火", "退火处理", "annealing", "热处理"],
                        layer=t.layer, raw_text=txt,
                    ))
                    break

        # --- 滤网支数 ---
        if "滤网支数" not in seen:
            for t in texts:
                txt = t.text.strip()
                if "支" in txt and any(c.isdigit() for c in txt):
                    seen.add("滤网支数")
                    self._params.append(Parameter(
                        name="滤网支数", value=0, unit="",
                        aliases=["支数", "多少支", "count", "支"],
                        layer=t.layer, raw_text=txt,
                    ))
                    break

        # --- 部品表信息 ---
        if "部品表" not in seen:
            parts = []
            for t in texts:
                txt = t.text.strip()
                if "部品" in txt and not txt.startswith("部品   尺寸"):
                    parts.append(txt)
            if parts:
                seen.add("部品表")
                self._params.append(Parameter(
                    name="部品表", value=0, unit="",
                    aliases=["部品", "部品表", "零件表", "部件", "BOM", "parts", "零件"],
                    layer="", raw_text=" | ".join(parts),
                ))

        if "使用温度" not in seen:
            for t in texts:
                if "-15" in t.text and "50" in t.text:
                    seen.add("使用温度")
                    self._params.append(Parameter(
                        name="使用温度", value=0, unit="",
                        aliases=["使用温度", "温度范围", "工作温度", "耐温范围", "耐温"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break

        if "抗病毒性能" not in seen and "ISO 18184" in all_text:
            for t in texts:
                if "ISO 18184" in t.text or "抗病毒" in t.text:
                    seen.add("抗病毒性能")
                    self._params.append(Parameter(
                        name="抗病毒性能", value=0, unit="",
                        aliases=["抗病毒", "抗病毒性能", "ISO 18184", "virus"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break

        perf_keywords = {
            "耐油性": ["耐油性", "耐油"],
            "耐酸性": ["耐酸性", "耐酸"],
            "耐寒性": ["耐寒性", "耐寒"],
            "耐热性": ["耐热性", "耐热"],
            "耐腐蚀性": ["耐腐蚀性", "耐腐蚀"],
            "耐冲击性": ["耐冲击性", "耐冲击"],
        }
        for key, aliases in perf_keywords.items():
            if key not in seen:
                for t in texts:
                    if t.text.strip() == key:
                        seen.add(key)
                        self._params.append(Parameter(
                            name=key, value=0, unit="",
                            aliases=aliases,
                            layer=t.layer, raw_text=key,
                        ))
                        break

        if "耐油测试介质" not in seen:
            for t in texts:
                if "色拉油" in t.text or "机械油" in t.text:
                    seen.add("耐油测试介质")
                    self._params.append(Parameter(
                        name="耐油测试介质", value=0, unit="",
                        aliases=["耐油测试", "测试用油", "耐油介质"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break

        if "耐酸测试介质" not in seen:
            for t in texts:
                if "醋酸" in t.text or "盐酸" in t.text or "硫酸" in t.text:
                    seen.add("耐酸测试介质")
                    self._params.append(Parameter(
                        name="耐酸测试介质", value=0, unit="",
                        aliases=["耐酸测试", "测试用酸", "耐酸介质"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break

        for p in self._params:
            if p.name in ("部品_边框", "材质"):
                if "树脂" not in p.aliases:
                    p.aliases.append("树脂")
            if p.name == "滤网材料":
                if "PP" not in p.aliases:
                    p.aliases.append("PP")

        # --- 通用标题栏信息提取 ---
        self._extract_general_title_block(texts, seen, all_text)

        # --- 通用签字栏信息提取 ---
        self._extract_signoff_info(texts, seen)

        # --- 通用技术要求/备注提取 ---
        self._extract_general_notes(texts, seen)

        # --- BOM表信息提取 ---
        self._extract_bom_info(texts, seen)

    # ========== 通用文本提取辅助方法 ==========

    def _extract_general_title_block(self, texts, seen, all_text):
        """从标题栏图层提取图纸基本信息"""
        # 收集 HHLayerShuxinglan 层上的文字（标签+值在同一层的不同位置）
        tb_texts = [t for t in texts if t.layer == "HHLayerShuxinglan"]

        # 检测关键词并提取相邻位置的值
        title_keywords = {
            "名称": ("图纸名称", ["图纸名称", "名称", "图名", "drawing name"]),
            "图号": ("图号", ["图号", "图纸编号", "drawing number"]),
            "比  例": ("比例", ["比例", "scale"]),
            "比例": ("比例", ["比例", "scale"]),
            "分  类": ("分类", ["分类", "类别", "classification"]),
            "分类": ("分类", ["分类", "类别", "classification"]),
            "图 幅": ("图幅", ["图幅", "图纸幅面", "sheet size"]),
            "图幅": ("图幅", ["图幅", "图纸幅面", "sheet size"]),
            "版本号": ("版本号", ["版本号", "版本", "version", "版次"]),
            "重要等级": ("重要等级", ["重要等级", "等级", "importance"]),
            "标  准": ("标准", ["标准", "标准号", "standard"]),
            "标准": ("标准", ["标准", "标准号", "standard"]),
            "管 理 编 号": ("管理编号", ["管理编号", "管理号", "management number"]),
            "管理编号": ("管理编号", ["管理编号", "管理号", "management number"]),
        }

        # 1. 先从标题栏图层匹配标签+值对（x坐标接近，y坐标相同或下方）
        #    标题栏布局：标签在上方行(y≈27)，值在下方行(y≈20)或同行的右侧
        for t in tb_texts:
            txt = t.text.strip()
            if txt in title_keywords:
                param_name, aliases = title_keywords[txt]
                if param_name in seen:
                    continue

                # 搜索值：在标签右侧（同行）或正下方（下一行）
                val_text = ""
                # 优先在 HHLayerShuxinglan 层找
                candidates = []
                for t2 in tb_texts:
                    if t2 is t:
                        continue
                    dy = t2.position["y"] - t.position["y"]
                    dx = t2.position["x"] - t.position["x"]
                    # 同行右侧：dy绝对值小, dx为正且不太远
                    # 下方：dy在[-15, -3]范围内（值在标签下方）
                    if (abs(dy) < 4 and 5 < dx < 100) or (-15 < dy < -3 and -30 < dx < 100):
                        v = t2.text.strip()
                        if v and v not in title_keywords and not v.startswith("更"):
                            candidates.append((v, abs(dy) + abs(dx) * 0.1))

                if candidates:
                    candidates.sort(key=lambda x: x[1])
                    val_text = candidates[0][0]

                # 如果没找到，在所有文本中找
                if not val_text:
                    candidates = []
                    for t2 in texts:
                        if t2 is t:
                            continue
                        dy = t2.position["y"] - t.position["y"]
                        dx = t2.position["x"] - t.position["x"]
                        if (abs(dy) < 4 and 5 < dx < 100) or (-15 < dy < -3 and -30 < dx < 100):
                            v = t2.text.strip()
                            if v and len(v) < 50 and v not in title_keywords:
                                candidates.append((v, abs(dy) + abs(dx) * 0.1))
                    if candidates:
                        candidates.sort(key=lambda x: x[1])
                        val_text = candidates[0][0]

                raw = val_text if val_text else txt
                seen.add(param_name)
                self._params.append(Parameter(
                    name=param_name, value=0, unit="",
                    aliases=aliases,
                    layer=t.layer, raw_text=raw,
                ))

        # 2. 扫描大号文字作为图纸名称（h>=5.0 的文字）
        if "图纸名称" not in seen:
            candidates = []
            for t in tb_texts:
                if t.height >= 5.0 and len(t.text.strip()) > 1:
                    txt = t.text.strip()
                    # 排除明显不是名称的内容
                    if txt not in title_keywords and not txt.isdigit() and "有限" not in txt:
                        candidates.append(t)
            # 选择y坐标最大的（底部标题栏通常在最下方）
            if candidates:
                candidates.sort(key=lambda t: -t.position["y"])
                seen.add("图纸名称")
                self._params.append(Parameter(
                    name="图纸名称", value=0, unit="",
                    aliases=["图纸名称", "名称", "图名", "drawing name", "零件名"],
                    layer=candidates[0].layer,
                    raw_text=candidates[0].text.strip(),
                ))

        # 3. 材料信息提取
        if "材料" not in seen:
            # 在 BOM 表中查找：HHLayerMingxilan 层的文字
            for t in texts:
                if t.layer == "HHLayerMingxilan" and t.text.strip() in ("SPCC", "SECC", "SUS304"):
                    seen.add("材料")
                    self._params.append(Parameter(
                        name="材料", value=0, unit="",
                        aliases=["材料", "材质", "材料牌号", "material"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break
            if "材料" not in seen:
                # 在 BOM 表或技术要求中找材料相关
                for t in texts:
                    txt = t.text.strip()
                    if "BC瓦楞纸" in txt:
                        seen.add("材料")
                        self._params.append(Parameter(
                            name="材料", value=0, unit="",
                            aliases=["材料", "材质", "材料牌号", "material"],
                            layer=t.layer, raw_text="BC瓦楞纸",
                        ))
                        # 找同一行的规格（如 7T）
                        for t2 in texts:
                            if t2.layer == t.layer and t2 is not t:
                                dy = abs(t2.position.get("y", 0) - t.position.get("y", 0))
                                dx = t2.position.get("x", 0) - t.position.get("x", 0)
                                if dy < 5 and dx > 0 and re.match(r"^\d+T$", t2.text.strip()):
                                    seen.add("材料规格")
                                    self._params.append(Parameter(
                                        name="材料规格", value=0, unit="",
                                        aliases=["材料规格", "规格", "材料尺寸", "material spec"],
                                        layer=t2.layer, raw_text=t2.text.strip(),
                                    ))
                                    break
                        break
                    elif "SPCC" in txt:
                        seen.add("材料")
                        self._params.append(Parameter(
                            name="材料", value=0, unit="",
                            aliases=["材料", "材质", "材料牌号", "material"],
                            layer=t.layer, raw_text="SPCC",
                        ))
                        break

        # 4. 材料规格
        if "材料规格" not in seen:
            for t in texts:
                if t.layer == "HHLayerMingxilan" and ("T" in t.text.strip() and "mm" in t.text.strip()):
                    seen.add("材料规格")
                    self._params.append(Parameter(
                        name="材料规格", value=0, unit="",
                        aliases=["材料规格", "规格", "材料尺寸", "material spec"],
                        layer=t.layer, raw_text=t.text.strip(),
                    ))
                    break
            if "材料规格" not in seen:
                for t in texts:
                    if t.layer == "HHLayerMingxilan" and re.match(r"\d+T$", t.text.strip()):
                        seen.add("材料规格")
                        self._params.append(Parameter(
                            name="材料规格", value=0, unit="",
                            aliases=["材料规格", "规格", "材料尺寸", "material spec"],
                            layer=t.layer, raw_text=t.text.strip(),
                        ))
                        break
            if "材料规格" not in seen:
                for t in texts:
                    if t.layer == "HHLayerMingxilan" and "7T" in t.text.strip():
                        seen.add("材料规格")
                        self._params.append(Parameter(
                            name="材料规格", value=0, unit="",
                            aliases=["材料规格", "规格", "材料尺寸", "material spec"],
                            layer=t.layer, raw_text=t.text.strip(),
                        ))
                        break

    def _extract_signoff_info(self, texts, seen):
        """提取签字栏信息（设计、审核、工艺、标准化、批准、归档等）
        策略：收集签字栏区域的原始文本，按y坐标分组形成表格行，
        让LLM根据上下文判断对应关系。
        """
        # 角色标签定义
        role_labels = {
            "设计": "设计", "审核": "审核", "工艺": "工艺",
            "标准化": "标准化", "批准": "批准", "归档": "归档",
            "再归档": "再归档",
        }

        # 收集HHLayerShuxinglan层上的角色标签及位置
        shuxinglan_texts = [t for t in texts if t.layer == "HHLayerShuxinglan"]
        role_entries = []
        for t in shuxinglan_texts:
            txt = t.text.strip().replace(" ", "")
            if txt in role_labels:
                role_entries.append({
                    "role": role_labels[txt],
                    "x": t.position["x"], "y": t.position["y"],
                })

        # 收集签字栏区域的原始行数据（签名和日期）
        # 侧板：signoff在右下角 x≈960-1010, y≈0-40
        # 印刷版：signoff在右下角 x≈385-435, y≈0-40
        signoff_rows = {}  # key = rounded y
        for t in texts:
            x, y = t.position.get("x", 0), t.position.get("y", 0)
            # 只取signoff区域的文本（包含标签和值）
            if (960 <= x <= 1010 or 385 <= x <= 435) and 0 <= y <= 45:
                txt = t.text.strip()
                if txt and len(txt) < 30:
                    y_rounded = round(y / 5) * 5  # 按5取整分组
                    if y_rounded not in signoff_rows:
                        signoff_rows[y_rounded] = []
                    signoff_rows[y_rounded].append({
                        "text": txt, "x": x,
                    })

        # 对每行按x排序
        sorted_rows = []
        for y_key in sorted(signoff_rows.keys(), reverse=True):
            row_texts = sorted(signoff_rows[y_key], key=lambda r: r["x"])
            row_txt = " | ".join(r["text"] for r in row_texts)
            sorted_rows.append(f"  [y≈{y_key}] {row_txt}")

        # 角色标签列表
        role_list = [f"  {r['role']} (y≈{round(r['y']/5)*5})" for r in sorted(role_entries, key=lambda r: -r['y'])]

        if sorted_rows:
            context = "\n".join(sorted_rows)
            roles = "\n".join(role_list)
            raw = f"签字栏角色标签：\n{roles}\n\n签字栏数据行：\n{context}"

            if "签字栏" not in seen:
                seen.add("签字栏")
                self._params.append(Parameter(
                    name="签字栏", value=0, unit="",
                    aliases=["签字栏", "签章", "签名", "signoff", "签字", "签章信息"],
                    layer="", raw_text=raw,
                ))

    def _extract_general_notes(self, texts, seen):
        """提取技术要求/备注等长文本信息"""
        # 检测长文本（多段内容，含换行或技术条款）
        long_texts = []
        for t in texts:
            txt = t.text.strip()
            if len(txt) >= 20 and ("\n" in txt or "。" in txt or "；" in txt):
                long_texts.append(t)

        # 如果有长文本且没有"技术要求"参数，添加到参数中
        if "技术要求" not in seen and long_texts:
            for t in long_texts:
                txt = t.text.strip().replace("\n", "|")
                if "技术" in txt or "表面" in txt or "材料" in txt or "尺寸" in txt or "喷涂" in txt:
                    if "技术要求" not in seen:
                        seen.add("技术要求")
                        self._params.append(Parameter(
                            name="技术要求", value=0, unit="",
                            aliases=["技术要求", "技术条件", "工艺要求", "备注"],
                            layer=t.layer, raw_text=txt,
                        ))

        # 提取所有长文本作为上下文信息
        context_parts = []
        for t in long_texts:
            txt = t.text.strip().replace("\n", "|")
            context_parts.append(f"[{t.layer}] {txt}")
        if context_parts:
            all_notes = " || ".join(context_parts)
            if "图纸备注" not in seen:
                seen.add("图纸备注")
                self._params.append(Parameter(
                    name="图纸备注", value=0, unit="",
                    aliases=["备注", "注释", "图纸说明", "note", "notes", "说明"],
                    layer="", raw_text=all_notes,
                ))

    def _extract_bom_info(self, texts, seen):
        """提取BOM表信息"""
        bom_texts = [t for t in texts if t.layer == "HHLayerMingxilan"]

        # 收集BOM内容按y坐标分组
        rows = {}
        for t in bom_texts:
            y_key = round(t.position["y"] / 5) * 5
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append({
                "text": t.text.strip(),
                "x": t.position["x"],
            })

        # 对每行按x排序
        for y_key in sorted(rows.keys(), reverse=True):
            row_texts = sorted(rows[y_key], key=lambda r: r["x"])
            combined = " | ".join(r["text"] for r in row_texts)
            if len(combined) > 5 and any(c.isalpha() for c in combined):
                row_label = f"BOM行_y{y_key}"
                if row_label not in seen:
                    seen.add(row_label)
                    self._params.append(Parameter(
                        name=row_label, value=0, unit="",
                        aliases=[f"BOM_{y_key}", f"物料清单_{y_key}"],
                        layer="HHLayerMingxilan", raw_text=combined,
                    ))

    def _assign_semantic_aliases(self):
        linear_dims = [p for p in self._params
                       if p.name.startswith("线性尺寸") or p.name.startswith("对齐尺寸")
                       or p.name == "<>（大）" or p.name == "（<>）"]
        linear_dims.sort(key=lambda p: -p.value)

        if len(linear_dims) >= 2:
            largest = linear_dims[0]
            second = linear_dims[1]

            if largest.value > second.value:
                largest.name = f"总长度({largest.value}mm)"
                largest.aliases.extend(["总长", "长度", "L", "length", "最长边"])
                second.name = f"总宽度({second.value}mm)"
                second.aliases.extend(["总宽", "宽度", "W", "width", "次长边"])
            else:
                largest.name = f"高度({largest.value}mm)"
                largest.aliases.extend(["高", "H", "height"])
                second.name = f"宽度({second.value}mm)"
                second.aliases.extend(["宽", "W", "width"])

        third_group = [p for p in linear_dims if p.value < 200 and p.value > 20]
        third_group.sort(key=lambda p: -p.value)
        for i, p in enumerate(third_group[:3]):
            if not p.name.startswith(("总长", "总宽", "高度", "宽度")):
                p.aliases.extend([f"内部尺寸{i+1}"])

    @staticmethod
    def _normalize_name(raw: str) -> tuple[str, List[str]]:
        return _normalize_name(raw)


def _build_name_from_type(dim: Dimension) -> str:
    type_names = {
        "linear": "线性尺寸",
        "aligned": "对齐尺寸",
        "diameter": "直径",
        "radius": "半径",
        "angular": "角度",
    }
    return f"{type_names.get(dim.dim_type, '尺寸')}_{dim.id}"


def _build_aliases(dim: Dimension) -> List[str]:
    aliases = [dim.id]
    if dim.text:
        cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z]", "", dim.text)
        if cleaned:
            aliases.append(cleaned)
    return aliases


def _normalize_name(raw: str) -> tuple[str, List[str]]:
    name_map = {
        "高度": ("高度", ["高", "H", "height"]),
        "宽度": ("宽度", ["宽", "W", "width"]),
        "长度": ("长度", ["长", "L", "length"]),
        "直径": ("直径", ["孔径", "D", "diameter"]),
        "半径": ("半径", ["R", "radius"]),
        "厚度": ("厚度", ["厚", "T", "thickness"]),
        "间距": ("间距", ["间隔", "gap", "spacing"]),
        "孔径": ("孔径", ["孔直径", "mesh size", "diameter"]),
    }
    for cn, (name, aliases) in name_map.items():
        if cn in raw:
            return name, aliases

    return raw, [raw]
