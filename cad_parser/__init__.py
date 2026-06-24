from cad_parser.reader import CADReader
from cad_parser.entities import EntityExtractor
from cad_parser.dimensions import DimensionExtractor
from cad_parser.text_extractor import TextExtractor
from cad_parser.layer_manager import LayerManager


class CADParser:
    def __init__(self, file_path: str):
        self._reader = CADReader(file_path)

    def parse(self):
        doc = self._reader.read()
        layer_mgr = LayerManager(doc)
        doc.entities = EntityExtractor(doc).extract()
        doc.dimensions = DimensionExtractor(doc).extract()
        doc.text_annotations = TextExtractor(doc).extract()
        doc.layers = layer_mgr.get_all()
        return doc
