from typing import List

from model import ApiTypeRef
from .classes import ApiParameterModel


class ApiCallback:

    def __init__(self, qualified_name: str, return_type: ApiTypeRef, parameters: List[ApiParameterModel]):
        super().__init__()
        self.qualified_name = qualified_name
        self.return_type = return_type
        self.parameters = parameters

    def to_dict(self) -> dict:
        return {
            "qualified_name": self.qualified_name,
            "return_type": self.return_type.to_dict() if self.return_type else None,
            "parameters": [p.to_dict() for p in self.parameters]
        }
