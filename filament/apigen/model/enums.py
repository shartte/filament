from typing import List
from .types import PrimitiveTypeKind


class ApiEnumConstant:
    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value
        }


class ApiEnum:

    def __init__(self,
                 qualified_name: str,
                 name: str,
                 base_type: PrimitiveTypeKind,
                 constants: List[ApiEnumConstant]):
        self.qualified_name = qualified_name
        self.name = name
        self.base_type = base_type
        self.constants = constants

    def to_dict(self) -> dict:
        return {
            "qualified_name": self.qualified_name,
            "name": self.name,
            "base_type": self.base_type.name,
            "constants": [x.to_dict() for x in self.constants]
        }
