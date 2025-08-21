from dataclasses import dataclass, field
from typing import Dict, Optional, List
from the_judge.domain.tracking.model import Visitor, VisitorState
from the_judge.application.dtos import Composite, VisitorCollection
from the_judge.common.datetime_utils import now


@dataclass
class CollectionBuffer:    
    # Visitor composites from all cameras in latest collection.
    current_collection: Optional[VisitorCollection] = None

    def get_or_create_collection(self, collection_id: str) -> VisitorCollection:
        if not self.current_collection or self.current_collection.id != collection_id:
            self.current_collection = VisitorCollection(
                id=collection_id,
                created_at=now()
            )
        return self.current_collection

    def add_composite(self, composite: Composite) -> bool:
        visitor = composite.visitor        
        # Check if new in current collection
        if self.current_collection:
            is_new = not any(c.visitor.id == visitor.id for c in self.current_collection.composites)
            self.current_collection.composites.append(composite)
            return is_new
        return False
        