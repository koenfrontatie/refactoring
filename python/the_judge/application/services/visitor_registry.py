from dataclasses import dataclass, field
from typing import Dict, Optional, List
from the_judge.domain.tracking.model import Visitor, VisitorCollection, Composite, VisitorState
from the_judge.common.datetime_utils import now


@dataclass
class VisitorRegistry:
    active_visitors: Dict[str, Visitor] = field(default_factory=dict)
    visitor_composites: Dict[str, Composite] = field(default_factory=dict)
    current_collection: Optional[VisitorCollection] = None

    def get_or_create_collection(self, collection_id: str) -> VisitorCollection:
        if not self.current_collection or self.current_collection.id != collection_id:
            self.current_collection = VisitorCollection(
                id=collection_id,
                created_at=now()
            )
            self.clear_collection_cache()
        return self.current_collection

    def add_visitor_with_composite(self, visitor: Visitor, composite: Composite) -> None:
        self.active_visitors[visitor.id] = visitor
        self.visitor_composites[visitor.id] = composite

    def get_visitor_and_composite(self, visitor_id: str) -> tuple[Optional[Visitor], Optional[Composite]]:
        visitor = self.active_visitors.get(visitor_id)
        composite = self.visitor_composites.get(visitor_id)
        return visitor, composite

    def get_collection_composites(self) -> List[Composite]:
        return list(self.visitor_composites.values())

    def get_visitor(self, visitor_id: str) -> Optional[Visitor]:
        return self.active_visitors.get(visitor_id)

    def get_all_visitors(self) -> List[Visitor]:
        return list(self.active_visitors.values())
    
    def is_visitor_present(self, visitor_id: str) -> bool:
        visitor = self.active_visitors.get(visitor_id)
        return visitor is not None and visitor.state != VisitorState.MISSING
    
    def get_present_visitors(self) -> List[Visitor]:
        return [v for v in self.active_visitors.values() 
                if v.state != VisitorState.MISSING]

    def remove_visitor(self, visitor_id: str) -> Optional[Visitor]:
        self.visitor_composites.pop(visitor_id, None)
        return self.active_visitors.pop(visitor_id, None)
    
    def clear_collection_cache(self):
        self.visitor_composites.clear()

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
