from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, LargeBinary, Float, JSON
from sqlalchemy.orm import registry
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Visitor
import uuid

metadata = MetaData()
mapper_registry = registry()

frames = Table(
    'frames', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('camera_name', String(100), nullable=False),
    Column('captured_at', DateTime, nullable=False),
    Column('collection_id', String(50))
)

faces = Table(
    'faces', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('frame_id', String(36), nullable=False, index=True),
    Column('bbox', JSON),
    Column('embedding', LargeBinary),
    Column('normed_embedding', LargeBinary),
    Column('embedding_norm', Float),
    Column('det_score', Float),
    Column('quality_score', Float),
    Column('pose', String(50)),
    Column('age', Integer),
    Column('sex', String(1)),
    Column('captured_at', DateTime)
)

bodies = Table(
    'bodies', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('frame_id', String(36), nullable=False, index=True),
    Column('bbox', JSON),
    Column('captured_at', DateTime)
)

detections = Table(
    'detections', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('frame_id', String(36), nullable=False, index=True),
    Column('face_id', String(36), index=True),
    Column('body_id', String(36), index=True),
    Column('visitor_record', JSON),
    Column('captured_at', DateTime)
)

visitors = Table(
    'visitors', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('name', String(100)),
    Column('state', String(50)),
    Column('face_id', String(36), index=True),
    Column('body_id', String(36), index=True),
    Column('captured_at', DateTime),
    Column('created_at', DateTime)
)

def start_mappers():
    mapper_registry.map_imperatively(Frame, frames)
    mapper_registry.map_imperatively(Face, faces)
    mapper_registry.map_imperatively(Body, bodies)
    mapper_registry.map_imperatively(Detection, detections)
    mapper_registry.map_imperatively(Visitor, visitors)
