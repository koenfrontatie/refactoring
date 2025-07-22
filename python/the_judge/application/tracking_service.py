import asyncio
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from the_judge.application.messagebus import MessageBus
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.domain.events import FrameProcessed
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now

logger = setup_logger("TrackingService")

@dataclass
class CollectionBuffer:
    collection_id: str
    frame_ids: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=now)
    
    def add_frame(self, frame_id: str):
        self.frame_ids.append(frame_id)
        logger.debug(f"Added frame {frame_id} to collection {self.collection_id}. Total frames: {len(self.frame_ids)}")

class TrackingService:
    def __init__(
        self,
        face_recognizer,
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus,
        collection_timeout: float = 2.0
    ):
        self.face_recognizer = face_recognizer
        self.uow_factory = uow_factory
        self.bus = bus
        self.collection_timeout = collection_timeout
        
        # Simple single collection tracking
        self.current_collection: Optional[CollectionBuffer] = None
        self.timeout_task: Optional[asyncio.Task] = None
    
    async def handle_frame_processed(self, event: FrameProcessed):
        """Buffer frame results and manage collection timeout."""
        collection_id = event.collection_id
        
        # Check if this is a new collection
        if self.current_collection is None or self.current_collection.collection_id != collection_id:
            # New collection - cancel previous if exists
            await self._cancel_current_collection()
            
            # Start new collection
            self.current_collection = CollectionBuffer(collection_id)
            logger.info(f"Started tracking new collection: {collection_id}")
        
        # Add frame to current collection
        self.current_collection.add_frame(event.frame_id)
        
        # Reset timeout
        await self._reset_timeout()
    
    async def _cancel_current_collection(self):
        """Cancel current collection processing without completing it."""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
            logger.info(f"Cancelled collection {self.current_collection.collection_id if self.current_collection else 'unknown'}")
        
        self.timeout_task = None
    
    async def _reset_timeout(self):
        """Reset the collection timeout."""
        # Cancel existing timeout
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        
        # Start new timeout
        self.timeout_task = asyncio.create_task(self._timeout_handler())
        logger.debug(f"Reset timeout for collection {self.current_collection.collection_id}")
    
    async def _timeout_handler(self):
        """Wait for timeout, then process collection."""
        try:
            await asyncio.sleep(self.collection_timeout)
            
            if self.current_collection:
                collection_id = self.current_collection.collection_id
                frame_count = len(self.current_collection.frame_ids)
                
                logger.info(f"Collection {collection_id} timeout reached. Processing {frame_count} frames.")
                
                # Process the collection
                await self.process_collection()
                
                # Cleanup
                self.current_collection = None
                self.timeout_task = None
                
                logger.info(f"Completed processing collection {collection_id}")
                
        except asyncio.CancelledError:
            logger.debug("Collection timeout cancelled")
    
    async def process_collection(self):
        """Process the current collection as batch."""
        if not self.current_collection:
            logger.warning("No current collection to process")
            return
        
        collection_id = self.current_collection.collection_id
        frame_ids = self.current_collection.frame_ids
        
        try:
            logger.info(f"Starting batch processing for collection {collection_id} with {len(frame_ids)} frames")
            
            # TODO: Implement the actual batch processing
            # 1. Get all faces from these frames
            # 2. Do batch face recognition  
            # 3. Handle known/new visitors
            # 4. Create detections
            
            # For now, just log what we would do
            with self.uow_factory() as uow:
                # faces = uow.repository.get_faces_by_frame_ids(frame_ids)
                # recognition_results = self.face_recognizer.recognize_faces(faces)
                # ... batch processing logic here
                
                logger.info(f"Would process faces from frames: {frame_ids}")
                # uow.commit()
                
        except Exception as e:
            logger.error(f"Error processing collection {collection_id}: {e}", exc_info=True)
