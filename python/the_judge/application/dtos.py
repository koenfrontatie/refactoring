from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from the_judge.domain.tracking.model import Face, FaceEmbedding, Body, Visitor


@dataclass
class Composite:
    face: Face
    embedding: FaceEmbedding
    body: Optional[Body] = None
    visitor: Optional[Visitor] = None


@dataclass
class VisitorCollection:
    id: str
    created_at: datetime
    composites: List[Composite] = field(default_factory=list)
