import numpy as np
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator


class NumpyArray(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.tobytes()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return np.frombuffer(value, dtype=np.float32)
        return value
