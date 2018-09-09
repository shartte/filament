from model import *
from pathlib import Path

# Primitives that are usable as return-types directly
_trivial_primitives = {
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

    PrimitiveTypeKind.ENTITY: "uint32_t",

    PrimitiveTypeKind.LIGHT_INSTANCE: "uint32_t",
    PrimitiveTypeKind.TRANSFORM_INSTANCE: "uint32_t",

    # Special math types for which we leave it up to the client what to do
    # We just specify the memory layout
    PrimitiveTypeKind.MAT44_DOUBLE: "FMAT44_DOUBLE",
    PrimitiveTypeKind.MAT44_FLOAT: "FMAT44_FLOAT",
    PrimitiveTypeKind.VEC2_DOUBLE: "VEC2_DOUBLE",
    PrimitiveTypeKind.VEC2_FLOAT: "VEC2_FLOAT",
    PrimitiveTypeKind.VEC3_DOUBLE: "VEC3_DOUBLE",
    PrimitiveTypeKind.VEC3_FLOAT: "VEC3_FLOAT",
    PrimitiveTypeKind.VEC4_DOUBLE: "VEC4_DOUBLE",
    PrimitiveTypeKind.VEC4_FLOAT: "VEC4_FLOAT"
}


def _needs_return_value_transform(method: ApiMethod) -> bool:
    return_type = method.return_type
    if isinstance(return_type, ApiPrimitiveType):
        return return_type.kind not in _trivial_primitives
    return False  # Might still apply for R value references


def _mangle_name(name: str) -> str:
    return name.replace("::", "_")


class CGenerator:

    def __init__(self, model: ApiModel):
        self.model = model

    def _generate_header(self, output_dir: Path):
        with output_dir.joinpath("cfilament.h").open("wt", buffering=4096) as fh:
            fh.write("#include <stdint.h>\n")

            for api_class in self.model.classes:

                fh.write("//\n")
                fh.write(f"// {api_class.qualified_name}\n")
                fh.write("//\n")
                fh.write("\n")

                name_prefix = _mangle_name(api_class.qualified_name) + "_"

                # Create a reusable parameter to pass the object pointer as the first method parameter
                this_param = ApiParameterModel(
                    "self", ApiPassByRef(False, ApiPassByRefType.POINTER, ApiClassRef(api_class.qualified_name))
                )

                for method in api_class.methods:
                    method_name = name_prefix + method.name

                    # Handle the special case where a method needs to be reformed
                    trailing_return_value = _needs_return_value_transform(method)
                    if trailing_return_value:
                        fh.write("void")
                    else:
                        fh.write(self._get_type_repr(method.return_type))
                    fh.write(" ")
                    fh.write(method_name)
                    fh.write("(")

                    # add the thiscall parameter as the first parameter
                    method_parameters = method.parameters[:]
                    method_parameters.insert(0, this_param)

                    # Write method parameters
                    for i in range(0, len(method_parameters)):
                        param = method_parameters[i]
                        if i > 0:
                            fh.write(", ")
                        fh.write(self._get_type_repr(param.type))
                        fh.write(" ")
                        fh.write(param.name)

                    # Return-value as pointer
                    if trailing_return_value:
                        fh.write(self._get_type_repr(method.return_type))
                        fh.write("* result")
                    fh.write(");\n")

                fh.write("\n")

    def generate(self, output_dir: Path):
        if not output_dir.is_dir():
            output_dir.mkdir()

        self._generate_header(output_dir)

    def _get_type_repr(self, type_ref: Optional[ApiTypeRef]) -> str:
        if type_ref is None:
            return "void"

        if isinstance(type_ref, ApiPassByRef):
            result = ""
            if type_ref.const:
                result = "const "
            result += self._get_type_repr(type_ref.pointee)
            result += "*"
            return result

        if isinstance(type_ref, ApiPrimitiveType):
            if type_ref.kind == PrimitiveTypeKind.UNEXPOSED:
                return "void*"

            return _primitive_type_names[type_ref.kind]

        if isinstance(type_ref, ApiClassRef) or isinstance(type_ref, ApiEnumRef):
            return _mangle_name(type_ref.qualified_name)

        return type_ref.to_dict().__repr__()
