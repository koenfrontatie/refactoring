from dataclasses import dataclass, field
from typing import Dict, Optional, List
from the_judge.domain.tracking.model import Visitor, VisitorCollection, Composite, VisitorState
from the_judge.common.datetime_utils import now


@dataclass
class VisitorRegistry:
    # Tracks global visitor state.
    active_visitors: Dict[str, Visitor] = field(default_factory=dict)
    
    # Visitor composites from all cameras in latest collection timeframe.
    current_collection: Optional[VisitorCollection] = None

    def get_or_create_collection(self, collection_id: str) -> VisitorCollection:
        if not self.current_collection or self.current_collection.id != collection_id:
            self.current_collection = VisitorCollection(
                id=collection_id,
                created_at=now()
            )
        return self.current_collection

    def add_composite(self, composite: Composite) -> bool:
        # Update global visitor state
        visitor = composite.visitor
        self.active_visitors[visitor.id] = visitor
        
        # Check if new in current collection
        if self.current_collection:
            is_new = not any(c.visitor.id == visitor.id for c in self.current_collection.composites)
            self.current_collection.composites.append(composite)
            return is_new
        return False

    def get_visitor(self, visitor_id: str) -> Optional[Visitor]:
        return self.active_visitors.get(visitor_id)

    def get_all_visitors(self) -> List[Visitor]:
        return list(self.active_visitors.values())

    def remove_visitor(self, visitor_id: str) -> Optional[Visitor]:
        if self.current_collection:
            self.current_collection.composites = [c for c in self.current_collection.composites if c.visitor.id != visitor_id]
        return self.active_visitors.pop(visitor_id, None)

    def check_visitor_timeouts(self, recognized_composites: List[Composite] = None) -> tuple[List[Visitor], List[Visitor]]:
        current_time = now()
        expired_visitors = []
        missing_visitors = []
        detected_ids = {c.visitor.id for c in (recognized_composites or []) if c.visitor}
        
        for visitor in list(self.active_visitors.values()):
            visitor.update_state(current_time)
            if visitor.id in detected_ids:
                continue
                
            if visitor._should_be_removed(current_time):
                expired_visitors.append(visitor)
                self.remove_visitor(visitor.id)
            elif visitor._should_go_missing(current_time):
                missing_visitors.append(visitor)
                self.remove_visitor(visitor.id)

        return expired_visitors, missing_visitors
        