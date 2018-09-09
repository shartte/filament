from typing import Optional
from abc import ABCMeta, abstractmethod
from enum import Enum, auto


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
    UNEXPOSED = auto()

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
