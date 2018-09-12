from typing import Union

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


def _needs_return_value_transform(return_type: ApiTypeRef) -> bool:
    if isinstance(return_type, ApiPrimitiveType):
        return return_type.kind not in _trivial_primitives
    return False  # Might still apply for R value references


def _mangle_name(name: str) -> str:
    return name.replace("::", "_")


class CGenerator:

    def __init__(self, model: ApiModel):
        self.model = model

    @staticmethod
    def _get_exported_method_name(class_model: Union[ApiClass, ApiInterface], method_model: ApiMethod) -> str:
        """
        Gets the name for an exported method, considering method overloading.
        """
        name_prefix = _mangle_name(class_model.qualified_name) + "_"

        # Are there other models in the class with the same name?
        conflicts = []
        if isinstance(class_model, ApiClass):
            other_methods = class_model.methods + class_model.static_methods
        else:
            other_methods = class_model.methods
        for other_method in other_methods:
            if other_method.name == method_model.name:
                conflicts.append(other_method)

        if len(conflicts) == 0 or (len(conflicts) == 1 and conflicts[0] == method_model):
            return name_prefix + method_model.name

        index_of_method = conflicts.index(method_model) + 1

        return name_prefix + method_model.name + str(index_of_method)

    def _generate_header(self, output_dir: Path):
        with output_dir.joinpath("cfilament.h").open("wt", buffering=4096) as fh:
            fh.write("#ifndef __CFILAMENT_H__\n")
            fh.write("#define __CFILAMENT_H__\n\n")
            fh.write("#include <stdint.h>\n")

            # Include standard types
            type_file_content = Path(__file__).parent.joinpath("c_valuetypes.h").read_text()
            fh.write("\n")
            fh.write(type_file_content)
            fh.write("\n")

            # Predeclare all opaque classes
            for api_class in self.model.classes:
                name = _mangle_name(api_class.qualified_name)
                fh.write(f"typedef struct {name}* {name};\n")
            fh.write("\n")

            # Predeclare all enums
            for api_enum in self.model.enums:
                name = _mangle_name(api_enum.qualified_name)
                base_type = _primitive_type_names[api_enum.base_type]
                fh.write(f"typedef enum {name} : {base_type} {{\n")
                for constant in api_enum.constants:
                    fh.write(f"   {name}_{constant.name} = {constant.value},\n")
                fh.write(f"}} {name};\n\n")
            fh.write("\n")

            # Predeclare all value types
            for value_type in self.model.value_types:
                name = _mangle_name(value_type.qualified_name)
                fh.write(f"typedef struct {name} {{\n")
                # TODO: Fields
                fh.write(f"}} {name};\n\n")

            # Declare a struct for all interfaces and add a destructor callback
            for interface in self.model.interfaces:
                name = _mangle_name(interface.qualified_name)

                # Convert from methods to fields with an appropriate function pointer type
                # This form does not supported overloaded methods on interfaces
                fields = []
                interface_methods = interface.methods[:]

                # Add a "destructor" callback
                interface_methods.append(ApiMethod("free", None, []))

                for method in interface_methods:
                    method_name = self._get_exported_method_name(interface, method)
                    method_parameters = method.parameters[:]
                    # Add a user arg to all callbacks
                    method_parameters.append(ApiPassByRef(False, ApiPassByRefType.POINTER, None))  # void*
                    fh.write("typedef ")
                    fh.write(self._get_function_pointer_decl(method_name, method.return_type, method.parameters))
                    fh.write(";\n")
                    fields += f"    {method_name} {method.name};\n"
                fields += f"    void* user;\n"
                fh.write("\n")

                fh.write(f"typedef struct {name} {{\n")
                fh.writelines(fields)
                fh.write(f"}} {name};\n\n")

            for api_class in self.model.classes:

                fh.write("//\n")
                fh.write(f"// {api_class.qualified_name}\n")
                fh.write("//\n")
                fh.write("\n")

                # Create a reusable parameter to pass the object pointer as the first method parameter
                this_param = ApiParameterModel(
                    "self", ApiPassByRef(False, ApiPassByRefType.POINTER, ApiClassRef(api_class.qualified_name))
                )

                for method in api_class.methods:
                    # add the thiscall parameter as the first parameter
                    method_parameters = method.parameters[:]
                    method_parameters.insert(0, this_param)

                    self._write_method(fh, api_class, method, method.parameters)

                for method in api_class.static_methods:
                    self._write_method(fh, api_class, method, method.parameters)

                fh.write("\n")

            fh.write("#endif\n")

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

    def _write_method(self, fh, parent_class: Union[ApiClass, ApiInterface],
                      method: ApiMethod,
                      method_parameters: List[ApiParameterModel]):
        method_name = self._get_exported_method_name(parent_class, method)

        # Handle the special case where a method needs to be reformed because the return type
        # is non-trivial
        trailing_return_value = _needs_return_value_transform(method.return_type)
        if trailing_return_value:
            fh.write("void")
            method_parameters.append(ApiParameterModel(
                "result",
                ApiPassByRef(False, ApiPassByRefType.POINTER, method.return_type)
            ))
        else:
            fh.write(self._get_type_repr(method.return_type))
        fh.write(" ")
        fh.write(method_name)
        fh.write("(")

        # Write method parameters
        for i in range(0, len(method_parameters)):
            param = method_parameters[i]
            if i > 0:
                fh.write(", ")
            fh.write(self._get_type_repr(param.type))
            fh.write(" ")
            fh.write(param.name)

        fh.write(");\n")

    def _get_function_pointer_decl(self,
                                   name: str,
                                   return_type: Optional[ApiTypeRef],
                                   method_parameters: List[ApiParameterModel]) -> str:

        result = ""

        # Handle the special case where a method needs to be reformed because the return type
        # is non-trivial
        trailing_return_value = _needs_return_value_transform(return_type)
        if trailing_return_value:
            result = "void"
            method_parameters.append(ApiParameterModel(
                "result",
                ApiPassByRef(False, ApiPassByRefType.POINTER, return_type)
            ))
        else:
            result += self._get_type_repr(return_type)
        result += f"(*{name})("

        # Write method parameters
        for i in range(0, len(method_parameters)):
            param = method_parameters[i]
            if i > 0:
                result += ", "
            result += self._get_type_repr(param.type)
            result += " "
            result += param.name

        result += ")"
        return result
