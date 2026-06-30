from __future__ import annotations

import logging
from typing import List

from cad.parser.models import BoundingBox, Entity

logger = logging.getLogger(__name__)

ENTITY_TYPES = {
    "LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "SPLINE",
    "ELLIPSE", "POINT", "INSERT", "HATCH", "SOLID", "3DFACE",
    "ATTRIB", "ATTDEF",
}


class EntityExtractor:
    def __init__(self, doc):
        self._doc = doc

    def extract(self) -> List[Entity]:
        dxf_doc = getattr(self._doc, "_dxf_doc", None)
        if dxf_doc is None:
            return []

        entities = []
        msp = dxf_doc.modelspace()

        for idx, entity in enumerate(msp):
            etype = entity.dxftype()
            if etype not in ENTITY_TYPES:
                continue

            geo = self._extract_geometry(entity)
            bbox = self._compute_bbox(entity)

            entities.append(Entity(
                id=f"ent_{idx:04d}",
                layer=entity.dxf.layer if hasattr(entity.dxf, "layer") else "",
                type=etype,
                geometry=geo,
                bounding_box=bbox,
            ))

        logger.info("Extracted %d entities", len(entities))
        return entities

    @staticmethod
    def _extract_geometry(entity) -> dict:
        etype = entity.dxftype()
        geo = {}
        try:
            if etype == "LINE":
                geo = {
                    "start": list(entity.dxf.start)[:2],
                    "end": list(entity.dxf.end)[:2],
                }
            elif etype == "CIRCLE":
                geo = {
                    "center": list(entity.dxf.center)[:2],
                    "radius": entity.dxf.radius,
                }
            elif etype == "ARC":
                geo = {
                    "center": list(entity.dxf.center)[:2],
                    "radius": entity.dxf.radius,
                    "start_angle": entity.dxf.start_angle,
                    "end_angle": entity.dxf.end_angle,
                }
            elif etype in ("LWPOLYLINE", "POLYLINE"):
                points = []
                for p in entity.get_points():
                    points.append(list(p)[:2])
                geo = {"points": points, "closed": entity.closed}
            elif etype == "SPLINE":
                geo = {
                    "degree": entity.dxf.degree,
                    "control_points": [list(p)[:2] for p in entity.control_points],
                }
            elif etype == "ELLIPSE":
                geo = {
                    "center": list(entity.dxf.center)[:2],
                    "major_axis": list(entity.dxf.major_axis)[:2],
                    "ratio": entity.dxf.ratio,
                }
            elif etype == "INSERT":
                geo = {
                    "name": entity.dxf.name,
                    "insert_point": list(entity.dxf.insert)[:2],
                    "xscale": getattr(entity.dxf, "xscale", 1.0),
                    "yscale": getattr(entity.dxf, "yscale", 1.0),
                    "rotation": getattr(entity.dxf, "rotation", 0.0),
                }
        except Exception as e:
            logger.debug("Geometry extraction failed for %s: %s", etype, e)

        return geo

    @staticmethod
    def _compute_bbox(entity) -> BoundingBox | None:
        try:
            bbox = entity.dxf.extmin if hasattr(entity.dxf, "extmin") else None
            if bbox:
                return BoundingBox(
                    xmin=bbox[0], ymin=bbox[1],
                    xmax=entity.dxf.extmax[0], ymax=entity.dxf.extmax[1],
                )
        except Exception:
            pass
        return None
