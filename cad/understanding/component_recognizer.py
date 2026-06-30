from __future__ import annotations

import logging
from typing import List

from cad.parser.models import CADDocument, Entity
from cad.understanding.models import Component

logger = logging.getLogger(__name__)


class ComponentRecognizer:
    def __init__(self):
        pass

    def recognize(self, doc: CADDocument) -> List[Component]:
        layer_groups: dict[str, list[Entity]] = {}
        for ent in doc.entities:
            layer_groups.setdefault(ent.layer, []).append(ent)

        components = []
        for layer_name, ents in layer_groups.items():
            if not ents:
                continue

            bboxes = [e.bounding_box for e in ents if e.bounding_box]
            if not bboxes:
                components.append(Component(
                    name=layer_name or "默认",
                    layer=layer_name,
                ))
                continue

            xmin = min(b.xmin for b in bboxes)
            ymin = min(b.ymin for b in bboxes)
            xmax = max(b.xmax for b in bboxes)
            ymax = max(b.ymax for b in bboxes)

            components.append(Component(
                name=layer_name or "默认",
                bounding_box={"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
                layer=layer_name,
            ))

        logger.info("Recognized %d components", len(components))
        return components
