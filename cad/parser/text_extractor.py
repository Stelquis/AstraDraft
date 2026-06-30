from __future__ import annotations

import logging
from typing import List

from cad.parser.models import TextAnnotation

logger = logging.getLogger(__name__)


class TextExtractor:
    def __init__(self, doc):
        self._doc = doc

    def extract(self) -> List[TextAnnotation]:
        dxf_doc = getattr(self._doc, "_dxf_doc", None)
        if dxf_doc is None:
            return []

        annotations = []
        msp = dxf_doc.modelspace()

        for idx, entity in enumerate(msp.query("TEXT")):
            ann = self._parse_text(entity, idx)
            if ann:
                annotations.append(ann)

        for idx, entity in enumerate(msp.query("MTEXT")):
            ann = self._parse_mtext(entity, idx + len(annotations))
            if ann:
                annotations.append(ann)

        logger.info("Extracted %d text annotations", len(annotations))
        return annotations

    @staticmethod
    def _parse_text(entity, idx: int) -> TextAnnotation | None:
        try:
            text = entity.dxf.text if hasattr(entity.dxf, "text") else ""
            if not text.strip():
                return None

            position = {}
            insert = getattr(entity.dxf, "insert", None)
            if insert is not None:
                position = {"x": insert[0], "y": insert[1]}

            return TextAnnotation(
                id=f"text_{idx:04d}",
                layer=entity.dxf.layer if hasattr(entity.dxf, "layer") else "",
                text=text.strip(),
                position=position,
                height=getattr(entity.dxf, "height", 0.0),
                rotation=getattr(entity.dxf, "rotation", 0.0),
            )
        except Exception as e:
            logger.debug("Text parse failed (idx=%d): %s", idx, e)
            return None

    @staticmethod
    def _parse_mtext(entity, idx: int) -> TextAnnotation | None:
        try:
            text = entity.plain_text() if hasattr(entity, "plain_text") else ""
            if not text.strip():
                return None

            position = {}
            insert = getattr(entity.dxf, "insert", None)
            if insert is not None:
                position = {"x": insert[0], "y": insert[1]}

            return TextAnnotation(
                id=f"mtext_{idx:04d}",
                layer=entity.dxf.layer if hasattr(entity.dxf, "layer") else "",
                text=text.strip(),
                position=position,
                height=getattr(entity.dxf, "char_height", 0.0),
                rotation=getattr(entity.dxf, "rotation", 0.0),
            )
        except Exception as e:
            logger.debug("MText parse failed (idx=%d): %s", idx, e)
            return None
