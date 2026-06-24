from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Parameter(BaseModel):
    name: str
    value: float
    unit: str = "mm"
    source_dim_id: str = ""
    aliases: List[str] = Field(default_factory=list)
    layer: str = ""
    raw_text: str = ""


class Component(BaseModel):
    name: str
    bounding_box: Dict = Field(default_factory=dict)
    parameters: List[str] = Field(default_factory=list)
    layer: str = ""


class ParameterIndexData(BaseModel):
    document: str = ""
    parameters: List[Parameter] = Field(default_factory=list)
    components: List[Component] = Field(default_factory=list)
