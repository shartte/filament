from typing import List

from .classes import ApiMethod


class ApiInterface:
    """
    Describes a fully virtual interface to be implemented by a client of the filament API.
    """

    def __init__(self, qualified_name: str, name: str, methods: List[ApiMethod]):
        self.qualified_name = qualified_name
        self.name = name
        self.methods = methods

    def to_dict(self) -> dict:
        return {
            "qualified_name": self.qualified_name,
            "name": self.name,
            "methods": [x.to_dict() for x in self.methods]
        }
