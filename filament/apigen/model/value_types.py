from typing import List

from .types import ApiTypeRef


class ApiValueTypeField:
    def __init__(self, name: str, type: ApiTypeRef):
        self.name = name
        self.type = type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type
        }


class ApiValueType:
    """
    Value types represent data structure for which the data layout is exposed, but without exposing any methods.
    """

    def __init__(self,
                 qualified_name: str,
                 name: str,
                 fields: List[ApiValueTypeField]
                 ):
        """
        :param qualified_name: The qualified name of the struct (i.e. filament::Frustum)
        :param name: The plain name of the class (i.e. Frustum) without namespace and enclosing classes.
        """
        self.qualified_name = qualified_name
        self.name = name
        self.fields = fields

    def to_dict(self) -> dict:
        return {
            "qualified_name": self.qualified_name,
            "name": self.name,
            "fields": [x.to_dict() for x in self.fields]
        }
