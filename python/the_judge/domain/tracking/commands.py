from the_judge.common import datetime_utils
from typing import Optional
from dataclasses import dataclass

class Command:
    pass

@dataclass
class CollectFrames(Command):
    id: str


