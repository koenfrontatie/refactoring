# infrastructure/db/orm.py
from sqlalchemy import (
    Table, Column, Integer, String, DateTime, Float, 
    ForeignKey, MetaData, PickleType, JSON
)
from sqlalchemy.orm import registry, relationship

# Domain model imports
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Collection

mapper_registry = registry()
metadata = MetaData()

# ====== Table Definitions ======

collections_table = Table(
    'collections',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('created_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

frames_table = Table(
    'frames',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('camera_name', String(255), nullable=False),  # String instead of FK
    Column('collection_id', Integer, ForeignKey('collections.id'), nullable=True),
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

faces_table = Table(
    'faces',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('bbox', JSON, nullable=False),  # tuple(x1, y1, x2, y2) ↔ JSON array
    Column('embedding', PickleType, nullable=False),  # np.ndarray as blob
    Column('normed_embedding', PickleType, nullable=False),  # np.ndarray as blob
    Column('embedding_norm', Float, nullable=False),
    Column('det_score', Float, nullable=False),
    Column('quality_score', Float, nullable=True),  # Optional
    Column('pose', String(100), nullable=True),  # Optional
    Column('age', Integer, nullable=True),  # Optional
    Column('sex', String(10), nullable=True),  # Optional
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

bodies_table = Table(
    'bodies',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('bbox', JSON, nullable=False),  # tuple(x1, y1, x2, y2) ↔ JSON array
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

detections_table = Table(
    'detections',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('visitor_record', PickleType, nullable=False),  # Visitor snapshot as dict
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

# ====== Mapper Configuration ======

def start_mappers():
    """Configure SQLAlchemy mappers between domain models and database tables."""
    
    # Collection mapper (Value Object)
    mapper_registry.map_imperatively(Collection, collections_table)
    
    # Frame mapper (Value Object)
    mapper_registry.map_imperatively(Frame, frames_table)
    
    # Face mapper (Value Object)
    mapper_registry.map_imperatively(Face, faces_table)
    
    # Body mapper (Value Object)
    mapper_registry.map_imperatively(Body, bodies_table)
    
    # Detection mapper (Value Object)
    mapper_registry.map_imperatively(Detection, detections_table)
