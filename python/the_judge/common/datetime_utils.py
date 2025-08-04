from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Union, Optional

from the_judge.common.logger import setup_logger

logger = setup_logger('DateTimeUtils')

LOCAL_TZ = ZoneInfo('Europe/Amsterdam')

def now() -> datetime:
    """Get current local datetime object."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def to_formatted_string(dt: datetime = None) -> str:
    """Convert datetime to database format string."""
    if dt is None:
        dt = now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def from_formatted_string(db_string: str) -> datetime:
    """Convert database format string to timezone-aware datetime."""
    if not db_string:
        return now()
    
    try:
        dt = datetime.strptime(db_string, '%Y-%m-%d %H:%M:%S')
        return dt.replace(tzinfo=LOCAL_TZ) 
    except ValueError as e:
        logger.warning(f"Failed to parse DB string '{db_string}': {e}")
        return now()

def time_since(start_time: Union[str, datetime, None]) -> timedelta:
    """Calculate time elapsed since start_time. Returns timedelta(0) on error."""
    try:
        if start_time is None:
            return timedelta(0)
        
        if isinstance(start_time, str):
            start_dt = from_formatted_string(start_time) 
        else:
            start_dt = start_time
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=LOCAL_TZ)
        
        return now() - start_dt
        
    except Exception as e:
        logger.warning(f"Error calculating time since: {e}")
        return timedelta(0)