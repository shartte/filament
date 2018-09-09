from typing import List, Any, Optional
from enum import Enum, auto
from abc import ABCMeta, abstractmethod


class ApiTypeRef(metaclass=ABCMeta):
    """
    A type reference, used for example to specify return and parameter types.
    """

    def __init__(self):
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        raise NotImplementedError()


class PrimitiveTypeKind(Enum):
    BOOL = auto()
    UINT8 = auto()
    INT8 = auto()
    UINT16 = auto()
    INT16 = auto()
    UINT32 = auto()
    INT32 = auto()
    UINT64 = auto()
    INT64 = auto()
    SIZE_T = auto()
    FLOAT = auto()
    DOUBLE = auto()
    STD_STRING = auto()

    # We specify entities as a primitive value type represented as int32
    ENTITY = auto()

    # Various EntityInstances
    LIGHT_INSTANCE = auto()
    TRANSFORM_INSTANCE = auto()

    # Special math types for which we leave it up to the client what to do
    # We just specify the memory layout
    MAT44_DOUBLE = auto()  # math::details::TMat44<double>
    MAT44_FLOAT = auto()  # math::details::TMat44<float>
    VEC2_DOUBLE = auto()  # math::details::TVec2<double>
    VEC2_FLOAT = auto()  # math::details::TVec2<float>
    VEC3_DOUBLE = auto()  # math::details::TVec3<double>
    VEC3_FLOAT = auto()  # math::details::TVec3<float>
    VEC4_DOUBLE = auto()  # math::details::TVec4<double>
    VEC4_FLOAT = auto()  # math::details::TVec4<float>


class ApiPrimitiveType(ApiTypeRef):

    def __init__(self, kind: PrimitiveTypeKind):
        super().__init__()
        self.kind = kind

    def to_dict(self) -> dict:
        return {
            "type": "primitive",
            "kind": self.kind.name
        }


class ApiEnumRef(ApiTypeRef):

    def __init__(self, qualified_name: str):
        super().__init__()
        self.qualified_name = qualified_name

    def to_dict(self) -> dict:
        return {
            "type": "enum",
            "qualified_name": self.qualified_name
        }


class ApiClassRef(ApiTypeRef):

    def __init__(self, qualified_name: str):
        super().__init__()
        self.qualified_name = qualified_name

    def to_dict(self) -> dict:
        return {
            "type": "class",
            "qualified_name": self.qualified_name
        }


class ApiPassByRefType(Enum):
    LVALUE_REF = auto()
    RVALUE_REF = auto()
    POINTER = auto()


class ApiPassByRef(ApiTypeRef):

    def __init__(self, const: bool, ref_type: ApiPassByRefType, pointee: Optional[ApiTypeRef]):
        super().__init__()
        self.const = const
        self.ref_type = ref_type
        self.pointee = pointee

    def to_dict(self) -> dict:
        return {
            "type": "byref",
            "const": self.const,
            "ref_type": self.ref_type.name,
            "pointee": self.pointee.to_dict() if self.pointee else None
        }


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
    def __init__(self, name: str, parameters: List[ApiParameterModel]):
        self.name = name
        self.parameters = parameters

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parameters": [x.to_dict() for x in self.parameters]
        }


class ApiClass:
    def __init__(self,
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
            "qualified_name": self.qualified_name,
            "name": self.name,
            "destructible": self.destructible,
            "constructors": [x.to_dict() for x in self.constructors],
            "methods": [x.to_dict() for x in self.methods],
            "static_methods": [x.to_dict() for x in self.static_methods],
        }


class ApiModel:
    def __init__(self):
        self.classes: List[ApiClass] = []
