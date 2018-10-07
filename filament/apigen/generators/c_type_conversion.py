from typing import Optional

from model import ApiOpaqueRef
from model.types import ApiTypeRef, ApiClassRef, ApiPassByRefType, ApiPassByRef, ApiPrimitiveType, ApiValueTypeRef, \
    PrimitiveTypeKind, ApiEnumRef, ApiCallbackRef, ApiBitsetType, ApiEntityInstance, ApiStringType
from .c_name_mangling import mangle_name

_primitive_type_names = {
    PrimitiveTypeKind.BOOL: "FBOOL",
    PrimitiveTypeKind.UINT8: "uint8_t",
    PrimitiveTypeKind.INT8: "int8_t",
    PrimitiveTypeKind.UINT16: "uint16_t",
    PrimitiveTypeKind.INT16: "int16_t",
    PrimitiveTypeKind.UINT32: "uint32_t",
    PrimitiveTypeKind.INT32: "int32_t",
    PrimitiveTypeKind.UINT64: "uint64_t",
    PrimitiveTypeKind.INT64: "int64_t",
    PrimitiveTypeKind.SIZE_T: "size_t",
    PrimitiveTypeKind.FLOAT: "float",
    PrimitiveTypeKind.DOUBLE: "double",

    PrimitiveTypeKind.ENTITY: "FENTITY",

    PrimitiveTypeKind.SAMPLER_PARAMS: "FSAMPLER_PARAMS",

    # Special math types for which we leave it up to the client what to do
    # We just specify the memory layout
    PrimitiveTypeKind.LINEAR_COLOR: "FLINEAR_COLOR",
    PrimitiveTypeKind.LINEAR_COLOR_A: "FLINEAR_COLOR_A",
    PrimitiveTypeKind.MAT33_DOUBLE: "FMAT33_DOUBLE",
    PrimitiveTypeKind.MAT33_FLOAT: "FMAT33_FLOAT",
    PrimitiveTypeKind.MAT44_DOUBLE: "FMAT44_DOUBLE",
    PrimitiveTypeKind.MAT44_FLOAT: "FMAT44_FLOAT",
    PrimitiveTypeKind.VEC2_DOUBLE: "FVEC2_DOUBLE",
    PrimitiveTypeKind.VEC2_FLOAT: "FVEC2_FLOAT",
    PrimitiveTypeKind.VEC3_DOUBLE: "FVEC3_DOUBLE",
    PrimitiveTypeKind.VEC3_FLOAT: "FVEC3_FLOAT",
    PrimitiveTypeKind.VEC4_DOUBLE: "FVEC4_DOUBLE",
    PrimitiveTypeKind.VEC4_FLOAT: "FVEC4_FLOAT",

    PrimitiveTypeKind.QUATERNION_FLOAT: "FQUATERNION_FLOAT",

    PrimitiveTypeKind.FRUSTUM: "FFRUSTUM"
}

_primitive_type_names_filament = {
    PrimitiveTypeKind.BOOL: "bool",
    PrimitiveTypeKind.UINT8: "uint8_t",
    PrimitiveTypeKind.INT8: "int8_t",
    PrimitiveTypeKind.UINT16: "uint16_t",
    PrimitiveTypeKind.INT16: "int16_t",
    PrimitiveTypeKind.UINT32: "uint32_t",
    PrimitiveTypeKind.INT32: "int32_t",
    PrimitiveTypeKind.UINT64: "uint64_t",
    PrimitiveTypeKind.INT64: "int64_t",
    PrimitiveTypeKind.SIZE_T: "size_t",
    PrimitiveTypeKind.FLOAT: "float",
    PrimitiveTypeKind.DOUBLE: "double",

    PrimitiveTypeKind.ENTITY: "utils::Entity",

    PrimitiveTypeKind.SAMPLER_PARAMS: "filament::driver::SamplerParams",

    # Special math types for which we leave it up to the client what to do
    # We just specify the memory layout
    PrimitiveTypeKind.LINEAR_COLOR: "filament::LinearColor",
    PrimitiveTypeKind.LINEAR_COLOR_A: "filament::LinearColorA",
    PrimitiveTypeKind.MAT33_DOUBLE: "math::mat3",
    PrimitiveTypeKind.MAT33_FLOAT: "math::mat3f",
    PrimitiveTypeKind.MAT44_DOUBLE: "math::mat4",
    PrimitiveTypeKind.MAT44_FLOAT: "math::mat4f",
    PrimitiveTypeKind.VEC2_DOUBLE: "math::double2",
    PrimitiveTypeKind.VEC2_FLOAT: "math::float2",
    PrimitiveTypeKind.VEC3_DOUBLE: "math::double3",
    PrimitiveTypeKind.VEC3_FLOAT: "math::float3",
    PrimitiveTypeKind.VEC4_DOUBLE: "math::double4",
    PrimitiveTypeKind.VEC4_FLOAT: "math::float4",

    PrimitiveTypeKind.QUATERNION_FLOAT: "math::quatf",

    PrimitiveTypeKind.FRUSTUM: "filament::Frustum"
}

#
# The fake primitives in this list are in reality value types that are:
# - trivially copyable
# - have the same memory layout on both the wrapper API and filament API definitions
#
_force_cast_primitive_kinds = {
    PrimitiveTypeKind.FRUSTUM,
    PrimitiveTypeKind.ENTITY,
    PrimitiveTypeKind.MAT33_DOUBLE,
    PrimitiveTypeKind.MAT33_FLOAT,
    PrimitiveTypeKind.MAT44_DOUBLE,
    PrimitiveTypeKind.MAT44_FLOAT,
    PrimitiveTypeKind.VEC2_DOUBLE,
    PrimitiveTypeKind.VEC2_FLOAT,
    PrimitiveTypeKind.VEC3_DOUBLE,
    PrimitiveTypeKind.VEC3_FLOAT,
    PrimitiveTypeKind.VEC4_DOUBLE,
    PrimitiveTypeKind.VEC4_FLOAT,
    PrimitiveTypeKind.LINEAR_COLOR,
    PrimitiveTypeKind.LINEAR_COLOR_A,
    PrimitiveTypeKind.QUATERNION_FLOAT,
    PrimitiveTypeKind.SAMPLER_PARAMS
}

# Primitive types that can be returned as values rather than through pointers
_acceptable_value_return_types = {
    PrimitiveTypeKind.BOOL,
    PrimitiveTypeKind.UINT8,
    PrimitiveTypeKind.INT8,
    PrimitiveTypeKind.UINT16,
    PrimitiveTypeKind.INT16,
    PrimitiveTypeKind.UINT32,
    PrimitiveTypeKind.INT32,
    PrimitiveTypeKind.UINT64,
    PrimitiveTypeKind.INT64,
    PrimitiveTypeKind.SIZE_T,
    PrimitiveTypeKind.FLOAT,
    PrimitiveTypeKind.DOUBLE
}


class ExpressionTypeConverter:

    def get_filament_type(self, type_ref: Optional[ApiTypeRef]) -> str:
        """
        Returns the type declaration for a type in the filament API.
        """
        return self._get_type_repr(type_ref, False)

    def get_wrapper_type(self, type_ref: Optional[ApiTypeRef]) -> str:
        """
        Returns the type declaration for a type in the filament API.
        """
        return self._get_type_repr(type_ref, True)

    def can_be_returned(self, return_type: ApiTypeRef) -> bool:
        if isinstance(return_type, ApiPrimitiveType):
            return return_type.kind in _acceptable_value_return_types
        elif isinstance(return_type, ApiValueTypeRef):
            return False
        return True  # Might still apply for R value references

    def _get_type_repr(self, type_ref: Optional[ApiTypeRef], api_surface: bool = True) -> str:
        """
        :param type_ref:
        :param api_surface: Get the type used on the external C API surface or one used on the filament API.
        :return:
        """

        if type_ref is None:
            return "void"

        if isinstance(type_ref, ApiPassByRef):
            # Detect opaque handle and use the typedef name (which already is a pointer)
            if isinstance(type_ref.pointee, ApiClassRef):
                return mangle_name(type_ref.pointee.qualified_name)

            result = ""
            if type_ref.const:
                result = "const "
            result += self._get_type_repr(type_ref.pointee)
            if api_surface or type_ref.ref_type == ApiPassByRefType.POINTER:
                result += "*"
            else:
                result += "&"
            return result

        elif isinstance(type_ref, ApiPrimitiveType):
            if type_ref.kind == PrimitiveTypeKind.UNEXPOSED:
                return "void*"

            if api_surface:
                return _primitive_type_names[type_ref.kind]
            else:
                return _primitive_type_names_filament[type_ref.kind]

        elif isinstance(type_ref, ApiClassRef) or isinstance(type_ref, ApiEnumRef) \
                or isinstance(type_ref, ApiValueTypeRef):
            if api_surface:
                return mangle_name(type_ref.qualified_name)
            else:
                return type_ref.qualified_name

        elif isinstance(type_ref, ApiCallbackRef):
            if api_surface:
                return mangle_name(type_ref.qualified_name)
            else:
                return type_ref.qualified_name

        elif isinstance(type_ref, ApiBitsetType):
            if type_ref.element_type == PrimitiveTypeKind.UINT32 and type_ref.element_count == 1:
                if api_surface:
                    return "uint32_t"  # Use uint32_t in lieu of bitset directlies
                else:
                    return "utils::bitset32"
            else:
                raise RuntimeError("Currently no support for extended bitsets")

        elif isinstance(type_ref, ApiEntityInstance):
            if api_surface:
                return mangle_name(type_ref.owner_qualified_name) + "_Instance"
            else:
                return "utils::EntityInstance<" + type_ref.owner_qualified_name + ">"

        elif isinstance(type_ref, ApiStringType):
            return "const char*"

        elif isinstance(type_ref, ApiOpaqueRef):
            return "void*"

        raise RuntimeError("Don't know how to represent type: " + repr(type_ref))

    def convert_in(self, expression: str, type: ApiTypeRef) -> str:
        # Return the expression converted from the API surface type
        # to the filament API type

        # Return the expression converted to the API surface type
        # from the filament API type
        # Convert ref->pointer
        underlying_type = type
        expression_is_ptr = False
        if isinstance(type, ApiPassByRef):
            if type.ref_type == ApiPassByRefType.LVALUE_REF:
                expression = "*" + expression
            elif type.ref_type == ApiPassByRefType.POINTER:
                expression_is_ptr = True
            underlying_type = type.pointee

        # Convert if the underlying type is one of the math types
        if isinstance(underlying_type, ApiEnumRef):
            # Cast enums 1:1 because their constant values are the same
            return "(" + underlying_type.qualified_name + ")" + expression
        elif isinstance(underlying_type, ApiPrimitiveType):
            if underlying_type.kind in _force_cast_primitive_kinds:
                return "convertIn" + _primitive_type_names[underlying_type.kind] + "(" + expression + ")"
            elif isinstance(underlying_type, ApiPrimitiveType):
                # Basic primitive types will need no conversion
                if underlying_type.kind in _acceptable_value_return_types:
                    return expression

        elif isinstance(underlying_type, ApiClassRef) and isinstance(type, ApiPassByRef):
            # For opaque handles, the typedef on the API surface is already to a pointer
            if type.ref_type == ApiPassByRefType.POINTER:
                return "(" + underlying_type.qualified_name + "*)(" + expression + ")"
            elif type.ref_type == ApiPassByRefType.LVALUE_REF:
                return "(" + underlying_type.qualified_name + "&)(" + expression + ")"
            elif type.ref_type == ApiPassByRefType.RVALUE_REF:
                return "std::move((" + underlying_type.qualified_name + "&&)(" + expression + "))"
        elif isinstance(underlying_type, ApiValueTypeRef):
            return "convertIn(" + expression + ")"
        elif isinstance(type, ApiEntityInstance):
            return "convertInEntityInstance<" + type.owner_qualified_name + ">(" + expression + ")"
        elif isinstance(underlying_type, ApiBitsetType):
            return "convertInBitset(" + expression + ")"
        elif isinstance(type, ApiStringType):
            # We perform no conversion for strings
            return expression
        elif underlying_type is None and expression_is_ptr:
            # void* is usually an untyped handle
            return expression
        elif isinstance(underlying_type, ApiPassByRef) and isinstance(type, ApiPassByRef) \
                and isinstance(underlying_type.pointee, ApiClassRef):
            # This means the original expression was pointer-to-pointer, same conversion rules
            # We only allow for actual pointers here, no lvalue/rvalue refs
            if type.ref_type == ApiPassByRefType.POINTER and underlying_type.ref_type == ApiPassByRefType.POINTER:
                return "(" + underlying_type.pointee.qualified_name + "**)(" + expression + ")"
        elif isinstance(type, ApiCallbackRef):
            # Like enums, we treat C callbacks as functionally equivalent to their C++ counterparts
            return "(" + type.qualified_name + ")" + expression
        elif isinstance(type, ApiOpaqueRef):
            # Opaque references also need to be converted as-is, since we expect them to point
            # to an object of the correct type, and we have no way of checking that
            return "(" + type.qualified_name + "*)" + expression

        raise RuntimeError("Don't know how to convert wrapper->filament: " + repr(type.to_dict()))

    def convert_out(self, expression: str, type: ApiTypeRef) -> str:
        # Return the expression converted to the API surface type
        # from the filament API type
        # Convert ref->pointer
        underlying_type = type
        expression_is_const = False
        if isinstance(type, ApiPassByRef):
            if type.ref_type == ApiPassByRefType.LVALUE_REF:
                expression = "&" + expression
            underlying_type = type.pointee
            expression_is_const = type.const

        # Convert if the underlying type is one of the math types
        if isinstance(underlying_type, ApiEnumRef):
            # Cast enums 1:1 because their constant values are the same
            return "(" + self._get_type_repr(underlying_type) + ")" + expression
        elif isinstance(underlying_type, ApiPrimitiveType):
            if underlying_type.kind in _force_cast_primitive_kinds:
                return "convertOut" + _primitive_type_names[underlying_type.kind] + "(" + expression + ")"
            elif isinstance(underlying_type, ApiPrimitiveType):
                # Basic primitive types will need no conversion
                if underlying_type.kind in _acceptable_value_return_types:
                    return expression

        elif isinstance(underlying_type, ApiClassRef) and isinstance(type, ApiPassByRef):
            # For opaque handles, the typedef on the API surface is already to a pointer
            return "(" + mangle_name(underlying_type.qualified_name) + ")(" + expression + ")"
        elif isinstance(underlying_type, ApiBitsetType):
            return "convertOutBitset(" + expression + ")"
        elif isinstance(underlying_type, ApiValueTypeRef):
            return "convertOut(" + expression + ")"
        elif isinstance(type, ApiStringType):
            # We perform no conversion for strings
            return expression
        elif isinstance(type, ApiPassByRef) and underlying_type is None:
            # Opaque data pointer (void*)
            return expression
        elif isinstance(type, ApiCallbackRef):
            # Like enums, we treat C callbacks as functionally equivalent to their C++ counterparts
            return "(" + self._get_type_repr(type) + ")" + expression
        elif isinstance(underlying_type, ApiOpaqueRef):
            return expression  # Shouldn't need to be cast to void*
        elif isinstance(underlying_type, ApiEntityInstance):
            return "convertOutEntityInstance(" + expression + ")"

        raise RuntimeError("Don't know how to convert filament->wrapper: " + repr(type.to_dict()))
