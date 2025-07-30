from dataclasses import dataclass, field
from typing import Dict, Optional, List
from the_judge.domain.tracking.model import Visitor, VisitorCollection, Composite, VisitorState
from the_judge.common.datetime_utils import now


@dataclass
class VisitorRegistry:
    active_visitors: Dict[str, Visitor] = field(default_factory=dict)
    current_collection: Optional[VisitorCollection] = None

    def get_or_create_collection(self, collection_id: str) -> VisitorCollection:
        if not self.current_collection or self.current_collection.id != collection_id:
            self.current_collection = VisitorCollection(
                id=collection_id,
                created_at=now()
            )
        return self.current_collection

    def add_visitor_with_composite(self, visitor: Visitor, composite: Composite) -> bool:
        self.active_visitors[visitor.id] = visitor
        if self.current_collection:
            is_new = visitor.id not in self.current_collection.composites
            self.current_collection.composites[visitor.id] = composite
            return is_new
        return False

    def get_visitor(self, visitor_id: str) -> Optional[Visitor]:
        return self.active_visitors.get(visitor_id)

    def get_all_visitors(self) -> List[Visitor]:
        return list(self.active_visitors.values())

    def remove_visitor(self, visitor_id: str) -> Optional[Visitor]:
        if self.current_collection:
            self.current_collection.composites.pop(visitor_id, None)
        return self.active_visitors.pop(visitor_id, None)

    def update_all_states(self) -> tuple[List[Visitor], List[Visitor]]:
        current_time = now()
        expired_visitors = []
        state_changed_visitors = []
        
        for visitor in self.active_visitors.values():
            old_state = visitor.state
            visitor.update_state(current_time)
            
            if visitor.state != old_state:
                state_changed_visitors.append(visitor)
                
            if visitor.should_be_removed:
                expired_visitors.append(visitor)
        
        for visitor in expired_visitors:
            visitor.expire()
            self.remove_visitor(visitor.id)
            
        return expired_visitors, state_changed_visitors
