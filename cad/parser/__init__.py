"""CAD 图纸解析 — DWG/DXF 读取、实体/标注/文本提取"""

from cad.parser.reader import CADReader
from cad.parser.models import CADDocument
from cad.parser.entities import EntityExtractor
from cad.parser.dimensions import DimensionExtractor
from cad.parser.text_extractor import TextExtractor
from cad.parser.layer_manager import LayerManager


class CADParser:
    """CAD 图纸解析器"""

    def __init__(self, file_path: str):
        self._reader = CADReader(file_path)

    def parse(self):
        doc = self._reader.read()
        doc.entities = EntityExtractor(doc).extract()
        doc.dimensions = DimensionExtractor(doc).extract()
        doc.text_annotations = TextExtractor(doc).extract()
        doc.layers = LayerManager(doc).get_all()
        return doc


__all__ = [
    "CADParser", "CADReader", "EntityExtractor",
    "DimensionExtractor", "TextExtractor", "LayerManager",
]
