from typing import Optional, List
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

    # Structs that consist of sub-byte-size fields are a hassle on APIs
    SAMPLER_PARAMS = auto() # filament::driver::SamplerParams

    # Various color types
    LINEAR_COLOR = auto()  # underlying type: VEC3_FLOAT
    LINEAR_COLOR_A = auto()  # underlying type: VEC4_FLOAT

    # Special math types for which we leave it up to the client what to do
    # We just specify the memory layout
    MAT33_DOUBLE = auto()  # math::details::TMat33<double>
    MAT33_FLOAT = auto()  # math::details::TMat33<float>
    MAT44_DOUBLE = auto()  # math::details::TMat44<double>
    MAT44_FLOAT = auto()  # math::details::TMat44<float>
    VEC2_DOUBLE = auto()  # math::details::TVec2<double>
    VEC2_FLOAT = auto()  # math::details::TVec2<float>
    VEC3_DOUBLE = auto()  # math::details::TVec3<double>
    VEC3_FLOAT = auto()  # math::details::TVec3<float>
    VEC4_DOUBLE = auto()  # math::details::TVec4<double>
    VEC4_FLOAT = auto()  # math::details::TVec4<float>

    QUATERNION_FLOAT = auto()  # math::details::TQuaternion<float>


class ApiPrimitiveType(ApiTypeRef):

    def __init__(self, kind: PrimitiveTypeKind):
        super().__init__()
        self.kind = kind

    def to_dict(self) -> dict:
        return {
            "type": "primitive",
            "kind": self.kind.name
        }


class ApiCallbackRef(ApiTypeRef):

    def __init__(self, qualified_name: str):
        super().__init__()
        self.qualified_name = qualified_name

    def to_dict(self) -> dict:
        return {
            "type": "callback",
            "qualified_name": self.qualified_name
        }


class ApiBitsetType(ApiTypeRef):
    """
    Represents the utils::bitset class template.
    """

    def __init__(self, element_type: PrimitiveTypeKind, element_count: int):
        super().__init__()
        self.element_type = element_type
        self.element_count = element_count

    def to_dict(self) -> dict:
        return {
            "type": "bitset",
            "element_type": self.element_type.name,
            "element_count": self.element_count
        }


class ApiEntityInstance(ApiTypeRef):
    """
    Models an EntityInstance and contains a reference to the actual owner of the instance.
    """

    def __init__(self, owner_qualified_name: str):
        super().__init__()
        self.owner_qualified_name = owner_qualified_name

    def to_dict(self) -> dict:
        return {
            "type": "entity_instance",
            "owner_qualified_name": self.owner_qualified_name
        }


class ApiAnonymousCallback(ApiTypeRef):
    """
    Specifies a C function pointer that was not declared using a typedef and thus has no usable name.
    """

    def __init__(self, return_type: ApiTypeRef, parameters: List[ApiTypeRef], signature: str):
        super().__init__()
        self.return_type = return_type
        self.parameters = parameters
        self.signature = signature

    def to_dict(self) -> dict:
        return {
            "type": "anonymous_callback",
            "return_type": self.return_type.to_dict() if self.return_type else None,
            "parameters": [p.to_dict() for p in self.parameters],
            "signature": self.signature
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


class ApiConstantArray(ApiTypeRef):
    """
    A constant-sized array. Only used for fields or pointee.
    """

    def __init__(self, element_type: ApiTypeRef, element_count: int):
        super().__init__()
        self.element_type = element_type
        self.element_count = element_count

    def to_dict(self) -> dict:
        return {
            "type": "constant_array",
            "element_type": self.element_type.to_dict(),
            "element_count": self.element_count
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
