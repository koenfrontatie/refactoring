from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Union, Optional

from the_judge.common.logger import setup_logger

logger = setup_logger('DateTimeUtils')

LOCAL_TZ = ZoneInfo('Europe/Amsterdam')

def now() -> datetime:
    """Get current local datetime object."""
    return datetime.now(LOCAL_TZ)


def to_db_string(dt: datetime = None) -> str:
    """Convert datetime to database format string."""
    if dt is None:
        dt = now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def time_diff_minutes(start: Union[str, datetime, None], 
                     end: Union[str, datetime, None] = None) -> float:
    """Calculate time difference in minutes between two timestamps."""
    try:
        if start is None:
            return 0.0
            
        if isinstance(start, str):
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=LOCAL_TZ)
        else:
            start_dt = start
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=LOCAL_TZ)
        
        if end is None:
            end_dt = now()
        elif isinstance(end, str):
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=LOCAL_TZ)
        else:
            end_dt = end
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=LOCAL_TZ)
        
        diff_seconds = (end_dt - start_dt).total_seconds()
        return diff_seconds / 60.0
        
    except Exception as e:
        logger.warning(f"Error calculating time difference: {e}")
        return 0.0
