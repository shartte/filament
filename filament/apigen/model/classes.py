from .types import ApiTypeRef
from typing import List, Optional


class ApiParameterModel:
    def __init__(self, name: str, type: ApiTypeRef):
        self.name = name
        self.type = type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.to_dict()
        }


class ApiConstructor:
    def __init__(self, parameters: List[ApiParameterModel]):
        self.parameters = parameters

    def to_dict(self) -> dict:
        return {
            "parameters": [x.to_dict() for x in self.parameters]
        }


class ApiMethod:
    def __init__(self, name: str, return_type: Optional[ApiTypeRef], parameters: List[ApiParameterModel]):
        self.name = name
        self.parameters = parameters
        self.return_type = return_type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "return_type": self.return_type.to_dict() if self.return_type else None,
            "parameters": [x.to_dict() for x in self.parameters]
        }


class ApiClass:
    def __init__(self,
                 header: str,
                 qualified_name: str,
                 name: str,
                 destructible: bool,
                 constructors: List[ApiConstructor],
                 methods: List[ApiMethod],
                 static_methods: List[ApiMethod]
                 ):
        """
        :param qualified_name: The qualified name of the class (i.e. filament::Camera)
        :param name: The plain name of the class (i.e. Camera) without namespace and enclosing classes.
        """
        self.header = header  # i.e. filament/camera.h
        self.qualified_name = qualified_name
        self.name = name
        self.constructors = constructors
        self.methods = methods
        self.static_methods = static_methods
        self.destructible = destructible

    def __repr__(self) -> str:
        return self.qualified_name

    def to_dict(self) -> dict:
        return {
            "header": self.header,
            "qualified_name": self.qualified_name,
            "name": self.name,
            "destructible": self.destructible,
            "constructors": [x.to_dict() for x in self.constructors],
            "methods": [x.to_dict() for x in self.methods],
            "static_methods": [x.to_dict() for x in self.static_methods],
        }
