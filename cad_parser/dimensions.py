from __future__ import annotations

import logging
from typing import List

from cad_parser.models import Dimension

logger = logging.getLogger(__name__)

DIM_TYPE_MAP = {
    0: "linear",
    1: "aligned",
    2: "angular",
    3: "diameter",
    4: "radius",
    5: "angular_3point",
    6: "ordinate",
}


def _decode_dimtype(raw: int | None) -> str:
    if raw is None:
        return "unknown"
    base_type = raw & 0x0F
    return DIM_TYPE_MAP.get(base_type, f"unknown_{base_type}")


class DimensionExtractor:
    def __init__(self, doc):
        self._doc = doc

    def extract(self) -> List[Dimension]:
        dxf_doc = getattr(self._doc, "_dxf_doc", None)
        if dxf_doc is None:
            return []

        dimensions = []
        msp = dxf_doc.modelspace()

        for idx, entity in enumerate(msp.query("DIMENSION")):
            dim = self._parse_dimension(entity, idx)
            if dim:
                dimensions.append(dim)

        logger.info("Extracted %d dimensions", len(dimensions))
        return dimensions

    @staticmethod
    def _parse_dimension(entity, idx: int) -> Dimension | None:
        try:
            dimtype_raw = getattr(entity.dxf, "dimtype", None)
            dim_type = _decode_dimtype(dimtype_raw)

            measurement = None
            if hasattr(entity.dxf, "actual_measurement"):
                measurement = entity.dxf.actual_measurement
            elif hasattr(entity, "get_measurement"):
                try:
                    measurement = entity.get_measurement()
                except Exception:
                    pass

            text = ""
            if hasattr(entity.dxf, "text"):
                text = entity.dxf.text
            if not text and measurement is not None:
                text = f"{measurement:.2f}"

            points = {}
            for attr in ("defpoint", "defpoint2", "defpoint3", "defpoint4", "defpoint5"):
                val = getattr(entity.dxf, attr, None)
                if val is not None:
                    points[attr] = list(val)[:2]

            text_midpoint = getattr(entity.dxf, "text_midpoint", None)
            if text_midpoint is not None:
                points["text_midpoint"] = list(text_midpoint)[:2]

            return Dimension(
                id=f"dim_{idx:04d}",
                layer=entity.dxf.layer if hasattr(entity.dxf, "layer") else "",
                dim_type=dim_type,
                measurement=measurement,
                text=text,
                points=points,
            )
        except Exception as e:
            logger.debug("Dimension parse failed (idx=%d): %s", idx, e)
            return None
