from __future__ import annotations

import logging
from typing import Optional

from cad_parser.models import CADDocument

logger = logging.getLogger(__name__)

UNIT_MAP = {
    0: "unitless",
    1: "inches",
    2: "feet",
    3: "miles",
    4: "mm",
    5: "cm",
    6: "m",
    7: "km",
}


class ScaleInferencer:
    def __init__(self):
        self._unit = "mm"
        self._scale = 1.0

    def infer(self, doc: CADDocument) -> str:
        insunits = doc.metadata.get("insunits", 0)
        unit = UNIT_MAP.get(insunits, "mm")

        measurement = doc.metadata.get("measurement", "")
        if measurement == "1":
            unit = "mm"
        elif insunits == 0:
            unit = "mm"

        self._unit = unit
        logger.info("Inferred unit: %s (insunits=%s, measurement=%s)", unit, insunits, measurement)
        return unit

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def scale(self) -> float:
        return self._scale
