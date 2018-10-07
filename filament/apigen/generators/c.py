from pathlib import Path
from typing import Set, Tuple

from generators import c_type_conversion
from generators.c_delegates import DelegateFactory, CallForwardType
from generators.c_name_mangling import resolve_overloaded_name
from generators.c_type_conversion import ExpressionTypeConverter
from model import *
from .c_name_mangling import mangle_name


class CGenerator:

    def __init__(self, model: ApiModel):
        self.model = model
        self.type_converter = ExpressionTypeConverter()
        self.delegate_factory = DelegateFactory(self.type_converter)

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
                name = mangle_name(api_class.qualified_name)
                fh.write(f"typedef struct _{name}* {name};\n")
            fh.write("\n")

            # Predeclare all entity instance reference types
            for owner_name in self._collect_all_entity_instances():
                name = self.type_converter.get_wrapper_type(ApiEntityInstance(owner_name))
                fh.write(f"typedef uint32_t {name};\n")
            fh.write("\n")

            type_converter = self.type_converter

            # Predeclare all enums
            for api_enum in self.model.enums:
                name = mangle_name(api_enum.qualified_name)
                base_type = type_converter.get_wrapper_type(ApiPrimitiveType(api_enum.base_type))
                fh.write(f"typedef enum _{name} : {base_type} {{\n")
                unsigned_enum = api_enum.base_type in {PrimitiveTypeKind.UINT8, PrimitiveTypeKind.UINT16,
                                                       PrimitiveTypeKind.UINT32, PrimitiveTypeKind.UINT64}
                for constant in api_enum.constants:
                    if constant.value < 0 and unsigned_enum:
                        fh.write(f"   {name}_{constant.name} = ({base_type}){constant.value},\n")
                    else:
                        fh.write(f"   {name}_{constant.name} = {constant.value},\n")
                fh.write(f"}} {name};\n\n")
            fh.write("\n")

            # Predeclare all value types
            for value_type in self.model.value_types:
                name = mangle_name(value_type.qualified_name)
                fh.write(f"typedef struct _{name} {{\n")
                for field in value_type.fields:
                    field_type = field.type
                    field_name = field.name
                    if isinstance(field_type, ApiConstantArray):
                        element_count = field_type.element_count
                        field_name += f"[{element_count}]"
                        field_type = field_type.element_type
                    fh.write(f"{type_converter.get_wrapper_type(field_type)} {field_name};\n")
                fh.write(f"}} {name};\n\n")

            # Declare all callback types
            for callback in self.model.callbacks:
                fh.write("typedef ")
                decl = self._get_function_pointer_decl(
                    mangle_name(callback.qualified_name),
                    callback.return_type,
                    callback.parameters
                )
                fh.write(decl)
                fh.write(";\n")

            # Declare a struct for all interfaces and add a destructor callback
            for interface in self.model.interfaces:
                name = mangle_name(interface.qualified_name)

                # Convert from methods to fields with an appropriate function pointer type
                # This form does not supported overloaded methods on interfaces
                fields = []
                interface_methods = interface.methods[:]

                # Add a "destructor" callback
                interface_methods.append(ApiMethod("free", None, []))

                for method in interface_methods:
                    method_name = resolve_overloaded_name(interface, method.name, method.parameters)
                    method_parameters = method.parameters[:]
                    # Add a user arg to all callbacks
                    method_parameters.append(ApiPassByRef(False, ApiPassByRefType.POINTER, None))  # void*
                    fields += "    typedef "
                    fields += self._get_function_pointer_decl("fn_" + method_name, method.return_type,
                                                              method.parameters)
                    fields += ";\n"
                    fields += f"    fn_{method_name} {method.name};\n"
                fields += f"    void* user;\n"
                fh.write("\n")

                fh.write(f"typedef struct {name} {{\n")
                fh.writelines(fields)
                fh.write(f"}} {name};\n\n")

            fh.writelines(self.delegate_factory.declarations.getvalue())

            fh.write("#endif\n")

    def _create_delegates(self):

        for api_class in self.model.classes:

            # Object constructors are converted to static methods that return opaque pointers here
            for constructor in api_class.constructors:
                method = ApiMethod(
                    "Create",
                    ApiClassRef(api_class.qualified_name),
                    constructor.parameters
                )
                self.delegate_factory.create_delegate(
                    api_class,
                    CallForwardType.CONSTRUCTOR,
                    constructor.parameters
                )

            for method in api_class.methods:
                self.delegate_factory.create_delegate(
                    api_class,
                    CallForwardType.METHOD,
                    method.parameters,
                    method.name,
                    method.return_type
                )

            for method in api_class.static_methods:
                self.delegate_factory.create_delegate(
                    api_class,
                    CallForwardType.STATIC_METHOD,
                    method.parameters,
                    method.name,
                    method.return_type
                )

    def _generate_conversion_methods(self) -> Tuple[List[str], List[str]]:
        """
        Generate conversion methods for value types.
        """
        decls = ["#include \"cfilament.h\"\n"]
        impls = []

        # Add the needed include files at the top
        decls += {f"#include <{x.rel_header_path}>\n" for x in self.model.value_types}

        # Generate conversion methods for bitsets
        # This code assumes that our external representation for bitsets uses the same storage
        # type as the bitset itself, and that current only N=1 is supported
        impls += [
            """
            template<typename T>
            inline utils::bitset<T> convertInBitset(T t) {
                utils::bitset<T> b;
                static_assert(sizeof(b) == sizeof(t), "bitset size differs from expected size");
                memcpy(&b, &t, sizeof(t));
                return b;
            }
            
            template<typename T>
            inline T convertOutBitset(utils::bitset<T> b) {
                T t;
                static_assert(sizeof(b) == sizeof(t), "bitset size differs from expected size");
                memcpy(&t, &b, sizeof(b));
                return t;                
            }
            """
        ]

        # Generate conversion methods for EntityInstance types
        impls += [
            """
            template<typename T>
            inline utils::EntityInstance<T> convertInEntityInstance(uint32_t ei) {
                utils::EntityInstance<T> r;
                static_assert(sizeof(r) == sizeof(ei), "EntityInstance is not 32-bit");
                memcpy(&r, &ei, sizeof(r));
                return r;
            }
            
            template<typename T>
            inline uint32_t convertOutEntityInstance(utils::EntityInstance<T> ei) {
                uint32_t r;
                static_assert(sizeof(r) == sizeof(ei), "EntityInstance is not 32-bit");
                memcpy(&r, &ei, sizeof(ei));
                return r;                
            }
            """
        ]

        type_converter = self.type_converter

        # Add built-in conversions for the math types using memcpy
        for type in c_type_conversion._force_cast_primitive_kinds:
            filament_name = type_converter.get_filament_type(ApiPrimitiveType(type))
            wrapper_name = type_converter.get_wrapper_type(ApiPrimitiveType(type))

            # Method overloading sadly doesn't cut it for the uint32_t typedefs we use
            name_suffix = wrapper_name

            decls.append(f"{wrapper_name} convertOut{name_suffix}({filament_name});\n")
            decls.append(f"{filament_name} convertIn{name_suffix}({wrapper_name});\n")
            impls.append(f"""
inline {wrapper_name} convertOut{name_suffix}({filament_name} input) {{
    {wrapper_name} r;
    static_assert(sizeof(r) == sizeof(input), "{wrapper_name} size doesnt match {filament_name}'s");
    memcpy(&r, &input, sizeof(input));
    return r;
}}

inline {filament_name} convertIn{name_suffix}({wrapper_name} input) {{
    {filament_name} r;
    static_assert(sizeof(r) == sizeof(input), "{wrapper_name} size doesnt match {filament_name}'s");
    memcpy(&r, &input, sizeof(input));
    return r;
}}

// Directly cast const pointers
inline const {wrapper_name}* convertOut{name_suffix}(const {filament_name}* input) {{
    return reinterpret_cast<const {wrapper_name}*>(input);
}}

// Directly cast non-const pointers when write-only arguments are passed
inline {filament_name}* convertIn{name_suffix}({wrapper_name}* input) {{
    return reinterpret_cast<{filament_name}*>(input);
}}

// Directly cast const pointers when read-only arguments are passed
inline const {filament_name}* convertIn{name_suffix}(const {wrapper_name}* input) {{
    return reinterpret_cast<const {filament_name}*>(input);
}}
""")

        # Convert from C++ value type to C repr
        for value_type in self.model.value_types:
            v_decls, v_impls = self._generate_conversion_method_for_value_type(value_type)
            decls += v_decls
            impls += v_impls

        return decls, impls

    def _generate_conversion_method_for_value_type(self, value_type):
        decls = []
        impls_in = []
        impls_out = []

        filament_name = value_type.qualified_name
        wrapper_name = mangle_name(value_type.qualified_name)

        decls.append(f"{wrapper_name} convertOut({filament_name});\n")

        def add_force_cast(filament_type, wrapper_type, impls_in, impls_out):
            decls.append(f"{wrapper_type}* convertOut({filament_type}*);\n")
            decls.append(f"{filament_type}* convertIn({wrapper_type}*);\n")
            impls_in += [
                f"inline {filament_type}* convertIn({wrapper_type}* input) {{\n",
                f"    return reinterpret_cast<{filament_type}*>(input);\n",
                "}\n\n"
            ]
            impls_out += [
                f"inline {wrapper_type}* convertOut({filament_type}* input) {{\n",
                f"    return reinterpret_cast<{wrapper_type}*>(input);\n",
                "}\n\n"
            ]

        add_force_cast(filament_name, wrapper_name, impls_in, impls_out)
        add_force_cast("const " + filament_name, "const " + wrapper_name, impls_in, impls_out)

        # We consider the memory layout of value types to be interchangeable

        impls_in.append(f"inline {filament_name} convertIn({wrapper_name} input) {{\n")
        impls_in.append(f"    {filament_name} result;\n")
        impls_out.append(f"inline {wrapper_name} convertOut({filament_name} input) {{\n")
        impls_out.append(f"    {wrapper_name} result;\n")

        type_converter = self.type_converter

        for field in value_type.fields:
            # TODO: use static_assert(offsetof(Struct, field) == offsetof(WrapperStruct, field))
            # to fully ensure a simple memcpy will not garble the entire struct

            # Arrays need to be considered
            if isinstance(field.type, ApiConstantArray):
                for i in range(0, field.type.element_count):
                    expression = type_converter.convert_out(f"input.{field.name}[{i}]", field.type.element_type)
                    impls_out.append(f"    result.{field.name}[{i}] = {expression};\n")

                    expression = type_converter.convert_in(f"input.{field.name}[{i}]", field.type.element_type)
                    impls_in.append(f"    result.{field.name}[{i}] = {expression};\n")
            else:
                expression = type_converter.convert_out("input." + field.name, field.type)
                impls_out.append(f"    result.{field.name} = {expression};\n")

                expression = type_converter.convert_in("input." + field.name, field.type)
                impls_in.append(f"    result.{field.name} = {expression};\n")

        impls_in.append("    return result;\n")
        impls_in.append("}\n\n")
        impls_out.append("    return result;\n")
        impls_out.append("}\n\n")

        return decls, impls_in + impls_out

    def generate(self, output_dir: Path):
        if not output_dir.is_dir():
            output_dir.mkdir()

        # Convert stuff
        (conversion_decls, conversion_impls) = self._generate_conversion_methods()
        with output_dir.joinpath("conversions.h").open("wt", buffering=4096) as fh:
            fh.writelines(conversion_decls)
            fh.writelines(conversion_impls)

        self._create_delegates()

        self._generate_header(output_dir)
        with output_dir.joinpath("cfilament.cpp").open("wt", buffering=4096) as fh:
            fh.write("""extern "C" {\n""")
            fh.write("#include \"cfilament.h\"\n")
            fh.write("""};\n\n""")
            fh.write("#include \"conversions.h\"\n")

            # Add includes for all C++ classes at the top
            fh.writelines([f"#include <{c.header}>\n" for c in self.model.classes])
            fh.write("\n")

            fh.write(self.delegate_factory.implementations.getvalue())

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

    def _get_function_pointer_decl(self,
                                   name: str,
                                   return_type: Optional[ApiTypeRef],
                                   method_parameters: List[ApiParameterModel]) -> str:

        result = ""

        # Handle the special case where a method needs to be reformed because the return type
        # is non-trivial
        trailing_return_value = not self.type_converter.can_be_returned(return_type)
        if trailing_return_value:
            result = "void"
            method_parameters.append(ApiParameterModel(
                "result",
                ApiPassByRef(False, ApiPassByRefType.POINTER, return_type)
            ))
        else:
            result += self.type_converter.get_wrapper_type(return_type)
        result += f"(*{name})("

        # Write method parameters
        for i in range(0, len(method_parameters)):
            param = method_parameters[i]
            if i > 0:
                result += ", "
            result += self.type_converter.get_wrapper_type(param.type)
            result += " "
            result += param.name

        result += ")"
        return result
