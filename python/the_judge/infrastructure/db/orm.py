from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, LargeBinary, Float, JSON, Enum
from sqlalchemy.orm import registry
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Visitor, FaceEmbedding, VisitorState, VisitorSession
from the_judge.infrastructure.db.types.numpy_array import NumpyArray
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
    Column('embedding_id', String(36), nullable=False, index=True),
    Column('embedding_norm', Float),
    Column('det_score', Float),
    Column('quality_score', Float),
    Column('pose', String(50)),
    Column('age', Integer),
    Column('sex', String(1)),
    Column('captured_at', DateTime)
)

face_embeddings = Table(
    'face_embeddings', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('embedding', NumpyArray),
    Column('normed_embedding', NumpyArray)
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
    Column('face_id', String(36), nullable=False, index=True),
    Column('embedding_id', String(36), nullable=False, index=True), 
    Column('body_id', String(36), index=True),
    Column('visitor_id', String(36), nullable=False, index=True),
    Column('captured_at', DateTime)
)

# Updated visitors table - live state view only
visitors = Table(
    'visitors', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('name', String(100)),
    Column('state', Enum(VisitorState)),
    Column('seen_count', Integer, default=0),
    Column('current_session_id', String(36), index=True),
    Column('last_seen', DateTime),
    Column('created_at', DateTime)
)

# New sessions table
sessions = Table(
    'sessions', metadata,
    Column('pk', Integer, primary_key=True),
    Column('id', String(36), unique=True, nullable=False, index=True),
    Column('visitor_id', String(36), nullable=False, index=True),
    Column('start_frame_id', String(36), nullable=False, index=True),
    Column('end_frame_id', String(36), nullable=True, index=True),
    Column('started_at', DateTime, nullable=False),
    Column('ended_at', DateTime, nullable=True),
    Column('captured_at', DateTime, nullable=False),
    Column('frame_count', Integer, default=1)
)

def start_mappers():
    mapper_registry.map_imperatively(Frame, frames)
    mapper_registry.map_imperatively(Face, faces)
    mapper_registry.map_imperatively(FaceEmbedding, face_embeddings)
    mapper_registry.map_imperatively(Body, bodies)
    mapper_registry.map_imperatively(Detection, detections)
    mapper_registry.map_imperatively(Visitor, visitors)
    mapper_registry.map_imperatively(VisitorSession, sessions)
