from __future__ import annotations

import logging
from typing import List

from cad_parser.models import LayerInfo

logger = logging.getLogger(__name__)


class LayerManager:
    def __init__(self, doc):
        self._doc = doc

    def get_all(self) -> List[LayerInfo]:
        dxf_doc = getattr(self._doc, "_dxf_doc", None)
        if dxf_doc is None:
            return []

        layers = []
        for layer in dxf_doc.layers:
            layers.append(LayerInfo(
                name=layer.dxf.name,
                color=getattr(layer.dxf, "color", 0),
                linetype=getattr(layer.dxf, "linetype", ""),
                on=layer.is_on(),
            ))

        if dxf_doc is not None:
            msp = dxf_doc.modelspace()
            layer_counts: dict[str, int] = {}
            for entity in msp:
                lname = getattr(entity.dxf, "layer", "")
                layer_counts[lname] = layer_counts.get(lname, 0) + 1
            for li in layers:
                li.entity_count = layer_counts.get(li.name, 0)

        logger.info("Found %d layers", len(layers))
        return layers

    def get_by_name(self, name: str) -> LayerInfo | None:
        for layer in self.get_all():
            if layer.name == name:
                return layer
        return None
