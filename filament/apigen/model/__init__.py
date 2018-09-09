from .classes import *
from .enums import *
from .types import *


class ApiModel:
    def __init__(self):
        self.classes: List[ApiClass] = []
        self.enums: List[ApiEnum] = []

    def to_dict(self) -> dict:
        return {
            "classes": [x.to_dict() for x in self.classes],
            "enums": [x.to_dict() for x in self.enums]
        }
