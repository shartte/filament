from model.interfaces import ApiInterface
from model.value_types import ApiValueType
from .classes import *
from .enums import *
from .types import *
from .callbacks import *


class ApiModel:
    def __init__(self):
        self.classes: List[ApiClass] = []
        self.enums: List[ApiEnum] = []
        self.value_types: List[ApiValueType] = []
        self.interfaces: List[ApiInterface] = []
        self.callbacks: List[ApiCallback] = []

    def to_dict(self) -> dict:
        return {
            "classes": [x.to_dict() for x in self.classes],
            "enums": [x.to_dict() for x in self.enums],
            "value_types": [x.to_dict() for x in self.value_types],
            "interfaces": [x.to_dict() for x in self.interfaces],
            "callbacks": [x.to_dict() for x in self.callbacks]
        }
