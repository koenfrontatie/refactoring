# infrastructure/db/orm.py
from sqlalchemy import (
    Table, Column, Integer, String, DateTime, Float, 
    ForeignKey, MetaData, PickleType, JSON
)
from sqlalchemy.orm import mapper, relationship

from domain.tracking import model

metadata = MetaData()

# ====== Table Definitions ======

collections = Table(
    'collections',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('created_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

frames = Table(
    'frames',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('camera_name', String(255), nullable=False),
    Column('collection_id', Integer, ForeignKey('collections.id'), nullable=True),
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

faces = Table(
    'faces',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('bbox', JSON, nullable=False),
    Column('embedding', PickleType, nullable=False),
    Column('normed_embedding', PickleType, nullable=False),
    Column('embedding_norm', Float, nullable=False),
    Column('det_score', Float, nullable=False),
    Column('quality_score', Float, nullable=True),
    Column('pose', String(100), nullable=True),
    Column('age', Integer, nullable=True),
    Column('sex', String(10), nullable=True),
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

bodies = Table(
    'bodies',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('bbox', JSON, nullable=False),
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

detections = Table(
    'detections',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('frame_id', Integer, ForeignKey('frames.id'), nullable=False),
    Column('visitor_record', PickleType, nullable=False),
    Column('captured_at', DateTime, nullable=False),
    Column('uuid', String(36), nullable=False, unique=True),
)

# ====== Mapper Configuration ======

def start_mappers():
    """Configure SQLAlchemy mappers following Cosmic Python approach."""
    
    # Simple direct mapping - no relationships for now
    mapper(model.Collection, collections)
    mapper(model.Frame, frames)
    mapper(model.Face, faces)
    mapper(model.Body, bodies)
    mapper(model.Detection, detections)
