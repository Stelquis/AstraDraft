from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr


class BoundingBox(BaseModel):
    xmin: float = 0.0
    ymin: float = 0.0
    xmax: float = 0.0
    ymax: float = 0.0

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin


class Entity(BaseModel):
    id: str
    layer: str = ""
    type: str = ""
    geometry: Dict = Field(default_factory=dict)
    bounding_box: Optional[BoundingBox] = None


class Dimension(BaseModel):
    id: str
    layer: str = ""
    dim_type: str = ""
    measurement: Optional[float] = None
    text: str = ""
    points: Dict = Field(default_factory=dict)
    precision: int = 2


class TextAnnotation(BaseModel):
    id: str
    layer: str = ""
    text: str = ""
    position: Dict = Field(default_factory=dict)
    height: float = 0.0
    rotation: float = 0.0


class LayerInfo(BaseModel):
    name: str
    color: int = 0
    linetype: str = ""
    on: bool = True
    entity_count: int = 0


class BlockDef(BaseModel):
    name: str
    entity_count: int = 0
    entities: List[Entity] = Field(default_factory=list)


class CADDocument(BaseModel):
    file_path: str
    file_format: str = "dxf"
    entities: List[Entity] = Field(default_factory=list)
    dimensions: List[Dimension] = Field(default_factory=list)
    text_annotations: List[TextAnnotation] = Field(default_factory=list)
    layers: List[LayerInfo] = Field(default_factory=list)
    blocks: List[BlockDef] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    bounding_box: Optional[BoundingBox] = None

    _dxf_doc: object = PrivateAttr(default=None)
