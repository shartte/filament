from typing import Union, Set, Tuple

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
    PrimitiveTypeKind.QUATERNION_FLOAT
}


def _needs_return_value_transform(return_type: ApiTypeRef) -> bool:
    if isinstance(return_type, ApiPrimitiveType):
        return return_type.kind not in _trivial_primitives
    elif isinstance(return_type, ApiValueTypeRef):
        return True
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

    def _generate_header(self, output_dir: Path, method_decls: List[str]):
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
                fh.write(f"typedef struct _{name}* {name};\n")
            fh.write("\n")

            # Predeclare all entity instance reference types
            for owner_name in self._collect_all_entity_instances():
                name = self._get_entity_instance_type_name(owner_name)
                fh.write(f"typedef uint32_t {name};\n")
            fh.write("\n")

            # Predeclare all enums
            for api_enum in self.model.enums:
                name = _mangle_name(api_enum.qualified_name)
                base_type = _primitive_type_names[api_enum.base_type]
                fh.write(f"typedef enum _{name} : {base_type} {{\n")
                for constant in api_enum.constants:
                    fh.write(f"   {name}_{constant.name} = {constant.value},\n")
                fh.write(f"}} {name};\n\n")
            fh.write("\n")

            # Predeclare all value types
            for value_type in self.model.value_types:
                name = _mangle_name(value_type.qualified_name)
                fh.write(f"typedef struct _{name} {{\n")
                for field in value_type.fields:
                    field_type = field.type
                    field_name = field.name
                    if isinstance(field_type, ApiConstantArray):
                        element_count = field_type.element_count
                        field_name += f"[{element_count}]"
                        field_type = field_type.element_type
                    fh.write(f"{self._get_type_repr(field_type)} {field_name};\n")
                fh.write(f"}} {name};\n\n")

            # Declare all callback types
            for callback in self.model.callbacks:
                fh.write("typedef ")
                decl = self._get_function_pointer_decl(
                    _mangle_name(callback.qualified_name),
                    callback.return_type,
                    callback.parameters
                )
                fh.write(decl)
                fh.write(";\n")

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

            fh.writelines(method_decls)

            fh.write("#endif\n")

    def _convert_in(self, expression: str, type: ApiTypeRef) -> str:
        # Return the expression converted from the API surface type
        # to the filament API type

        # Return the expression converted to the API surface type
        # from the filament API type
        # Convert ref->pointer
        underlying_type = type
        expression_is_const = False
        expression_is_ptr = False
        if isinstance(type, ApiPassByRef):
            if type.ref_type == ApiPassByRefType.LVALUE_REF:
                expression = "*" + expression
            elif type.ref_type == ApiPassByRefType.POINTER:
                expression_is_ptr = True
            underlying_type = type.pointee
            expression_is_const = type.const

        # Convert if the underlying type is one of the math types
        if isinstance(underlying_type, ApiEnumRef):
            # Cast enums 1:1 because their constant values are the same
            expression = "(" + self._get_type_repr(underlying_type, False) + ")" + expression
        elif isinstance(underlying_type, ApiPrimitiveType):
            if underlying_type.kind in _force_cast_primitive_kinds:
                return "convertIn(" + expression + ")"

        return expression

    def _convert_out(self, expression: str, type: ApiTypeRef) -> str:
        # Return the expression converted to the API surface type
        # from the filament API type
        # Convert ref->pointer
        underlying_type = type
        if isinstance(type, ApiPassByRef):
            if type.ref_type == ApiPassByRefType.LVALUE_REF:
                expression = "&" + expression
            underlying_type = type.pointee

        # Convert if the underlying type is one of the math types
        if isinstance(underlying_type, ApiEnumRef):
            # Cast enums 1:1 because their constant values are the same
            expression = "(" + self._get_type_repr(underlying_type) + ")" + expression
        elif isinstance(underlying_type, ApiPrimitiveType):
            if underlying_type.kind in _force_cast_primitive_kinds:
                return "convertOut(" + expression + ")"

        return expression

    def _generate_methods(self) -> Tuple[List[str], List[str]]:

        decls = []
        impls = []

        # Add includes for all C++ classes at the top
        impls += [f"#include <{c.header}>\n" for c in self.model.classes]
        impls += ["\n"]

        for api_class in self.model.classes:

            decls += ["//\n",
                      f"// {api_class.qualified_name}\n",
                      "//\n",
                      "\n"]

            # Create a reusable parameter to pass the object pointer as the first method parameter
            this_param = ApiParameterModel(
                "self", ApiPassByRef(False, ApiPassByRefType.POINTER, ApiClassRef(api_class.qualified_name))
            )

            for method in api_class.methods:
                # add the thiscall parameter as the first parameter
                method_parameters = method.parameters[:]
                method_parameters.insert(0, this_param)

                method_header, trailing_return_value = self._create_method_header(api_class, method, method_parameters)
                decls += [method_header + ";\n"]

                # Insert the actual call to the C++ method
                args = ", ".join([self._convert_in(p.name, p.type) for p in method.parameters])
                call_expression = f"_self->{method.name}({args})"

                # Insert a return if the method return type is not void
                return_type = method.return_type
                if return_type is not None:
                    if trailing_return_value:
                        return_stmt = "*result = "
                    else:
                        return_stmt = "return "
                    call_expression = return_stmt + self._convert_out(call_expression, return_type)

                impls += [
                    method_header, "\n",
                    "{\n",
                    # Cast the self-parameter to the C++ this pointer
                    f"    auto _self = ({api_class.qualified_name}*){this_param.name};\n"
                    "    ",
                    call_expression,
                    ";\n",
                    "}\n\n",
                ]

            for method in api_class.static_methods:
                method_header, trailing_return_value = self._create_method_header(api_class, method, method.parameters)
                decls += [method_header + ";\n"]

            decls += ["\n"]

        return decls, impls

    def _generate_conversion_methods(self) -> Tuple[List[str], List[str]]:
        """
        Generate conversion methods for value types.
        """
        decls = ["#include \"cfilament.h\"\n"]
        impls = []

        # Add the needed include files at the top
        decls += {f"#include <{x.rel_header_path}>\n" for x in self.model.value_types}

        # Add built-in conversions for the math types using memcpy
        for type in _force_cast_primitive_kinds:
            filament_name = _primitive_type_names_filament[type]
            wrapper_name = _primitive_type_names[type]
            decls.append(f"{wrapper_name} convertOut({filament_name});\n")
            decls.append(f"{filament_name} convertIn({wrapper_name});\n")
            impls.append(f"""
inline {wrapper_name} convertOut({filament_name} input) {{
    {wrapper_name} r;
    static_assert(sizeof(r) == sizeof(input), "{wrapper_name} size doesnt match {filament_name}'s");
    memcpy(&r, &input, sizeof(input));
    return r;
}}

// Directly cast const pointers
inline const {wrapper_name}* convertOut(const {filament_name}* input) {{
    return reinterpret_cast<const {wrapper_name}*>(input);
}}

// Directly cast non-const pointers when write-only arguments are passed
inline {filament_name}* convertIn({wrapper_name}* input) {{
    return reinterpret_cast<{filament_name}*>(input);
}}
""")

        for value_type in self.model.value_types:
            # Convert from C++ value type to C repr
            filament_name = value_type.qualified_name
            wrapper_name = _mangle_name(value_type.qualified_name)
            decls.append(f"{wrapper_name} convertOut({filament_name});\n")
            impls.append(f"inline {wrapper_name} convertOut({filament_name} input) {{\n")
            impls.append(f"    {wrapper_name} result;\n")

            for field in value_type.fields:

                # Arrays need to be considered
                if isinstance(field.type, ApiConstantArray):
                    for i in range(0, field.type.element_count):
                        expression = self._convert_out(f"input.{field.name}[{i}]", field.type.element_type)
                        impls.append(f"    result.{field.name}[{i}] = {expression};\n")
                else:
                    expression = self._convert_out("input." + field.name, field.type)
                    impls.append(f"    result.{field.name} = {expression};\n")

            impls.append("    return result;\n")
            impls.append("}\n\n")

        return decls, impls

    def generate(self, output_dir: Path):
        if not output_dir.is_dir():
            output_dir.mkdir()

        # Convert stuff
        (conversion_decls, conversion_impls) = self._generate_conversion_methods()
        with output_dir.joinpath("conversions.h").open("wt", buffering=4096) as fh:
            fh.writelines(conversion_decls)
            fh.writelines(conversion_impls)

        (method_decls, method_impls) = self._generate_methods()
        self._generate_header(output_dir, method_decls)
        with output_dir.joinpath("cfilament.cpp").open("wt", buffering=4096) as fh:
            fh.write("""extern "C" {\n""")
            fh.write("#include \"cfilament.h\"\n")
            fh.write("""};\n\n""")
            fh.write("#include \"conversions.h\"\n")

            fh.writelines(method_impls)

    def _get_entity_instance_type_name(self, owner: str):
        return _mangle_name(owner) + "_Instance"

    def _collect_all_entity_instances(self) -> Set[str]:
        """
        Seek through the entire API collecting unique Entity Instance types.
        """
        result = set()

        for api_class in self.model.classes:
            for method in api_class.methods + api_class.static_methods:
                if isinstance(method.return_type, ApiEntityInstance):
                    result.add(method.return_type.owner_qualified_name)
                for p in method.parameters:
                    if isinstance(p.type, ApiEntityInstance):
                        result.add(p.type.owner_qualified_name)

        return result

    def _get_type_repr(self, type_ref: Optional[ApiTypeRef], api_surface: bool = True) -> str:
        """
        :param type_ref:
        :param api_surface: Get the type used on the external C API surface or one used on the filament API.
        :return:
        """

        if type_ref is None:
            return "void"

        if isinstance(type_ref, ApiPassByRef):
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
                return _mangle_name(type_ref.qualified_name)
            else:
                return type_ref.qualified_name

        elif isinstance(type_ref, ApiCallbackRef):
            if api_surface:
                return _mangle_name(type_ref.qualified_name)
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
                return self._get_entity_instance_type_name(type_ref.owner_qualified_name)
            else:
                return "utils::EntityInstance<" + type_ref.owner_qualified_name + ">"

        elif isinstance(type_ref, ApiStringType):
            return "const char*"

        return type_ref.to_dict().__repr__()

    def _create_method_header(self, parent_class: Union[ApiClass, ApiInterface],
                              method: ApiMethod,
                              method_parameters: List[ApiParameterModel]):
        method_name = self._get_exported_method_name(parent_class, method)

        result = ""

        # Handle the special case where a method needs to be reformed because the return type
        # is non-trivial
        trailing_return_value = _needs_return_value_transform(method.return_type)
        if trailing_return_value:
            result += "void"
            method_parameters.append(ApiParameterModel(
                "result",
                ApiPassByRef(False, ApiPassByRefType.POINTER, method.return_type)
            ))
        else:
            result += self._get_type_repr(method.return_type)
        result += f" {method_name}("

        # Write method parameters
        for i in range(0, len(method_parameters)):
            param = method_parameters[i]
            if i > 0:
                result += ", "
            result += self._get_type_repr(param.type)
            result += " "
            result += param.name

        result += ")"

        return result, trailing_return_value

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
