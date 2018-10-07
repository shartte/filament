from enum import Enum, auto
from io import StringIO
from typing import Union, Optional, List

from generators.c_name_mangling import resolve_overloaded_name, CONSTRUCTOR_NAME, DESTRUCTOR_NAME
from generators.c_type_conversion import ExpressionTypeConverter
from model import ApiClass, ApiInterface, ApiParameterModel
from model.types import ApiTypeRef, ApiClassRef, ApiPassByRefType, ApiPassByRef
from .c_name_mangling import mangle_name


class CallForwardType(Enum):
    METHOD = auto()
    STATIC_METHOD = auto()
    CONSTRUCTOR = auto()
    DESTRUCTOR = auto()


THIS_PARAM_NAME = "self"


class DelegateFactory:

    def __init__(self, type_converter: ExpressionTypeConverter):
        self.declarations = StringIO()
        self.implementations = StringIO()
        self.type_converter = type_converter

    def create_delegate(self,
                        api_class: ApiClass,
                        forward_type: CallForwardType,
                        method_parameters: List[ApiParameterModel],
                        method_name: Optional[str] = None,
                        method_return_type: Optional[ApiTypeRef] = None):

        # The argument list is produced in the same way, regardless of call-type
        args = ", ".join([self.type_converter.convert_in(p.name, p.type) for p in method_parameters])

        # Decide on which way to actually invoke the method and produce a result
        if forward_type == CallForwardType.METHOD:
            cast_this_ptr = f"(({api_class.qualified_name}*){THIS_PARAM_NAME})"
            call_expression = f"{cast_this_ptr}->{method_name}({args})"
            return_type = method_return_type
        elif forward_type == CallForwardType.STATIC_METHOD:
            call_expression = f"{api_class.qualified_name}::{method_name}({args})"
            return_type = method_return_type
        elif forward_type == CallForwardType.CONSTRUCTOR:
            call_expression = f"new {api_class.qualified_name}({args})"
            return_type = ApiPassByRef(False, ApiPassByRefType.POINTER, ApiClassRef(api_class.qualified_name))

        # is the return-value converted to a pointer passed in as the last arg?
        return_by_pointer = False

        if forward_type == CallForwardType.METHOD or forward_type == CallForwardType.STATIC_METHOD:
            # Check required arguments for method forwarders
            if method_name is None:
                raise RuntimeError("When creating a delegate for calling methods, the method_name is required")

            # If the return-value needs to be returned by pointer because it's not ABI-safe,
            # add a corresponding Pointer parameter
            if method_return_type is not None and not self.type_converter.can_be_returned(method_return_type):
                return_by_pointer = True
                method_parameters.append(ApiParameterModel(
                    "result",
                    ApiPassByRef(False, ApiPassByRefType.POINTER, method_return_type)
                ))
        elif forward_type == CallForwardType.CONSTRUCTOR:
            method_name = CONSTRUCTOR_NAME
        elif forward_type == CallForwardType.DESTRUCTOR:
            method_name = DESTRUCTOR_NAME

        delegate_name = self._create_delegate_name(api_class, method_name, method_parameters)

        # Create the delegate's signature
        if forward_type == CallForwardType.METHOD:
            this_param = ApiParameterModel(
                THIS_PARAM_NAME, ApiPassByRef(False, ApiPassByRefType.POINTER, ApiClassRef(api_class.qualified_name))
            )
            method_signature = self._create_signature(
                delegate_name,
                None if return_by_pointer else return_type,
                [this_param] + method_parameters
            )
        else:
            method_signature = self._create_signature(
                delegate_name,
                None if return_by_pointer else return_type,
                method_parameters
            )

        # Insert a return if the method return type is not void
        if return_type is not None:
            if return_by_pointer:
                return_stmt = "*result = "
            else:
                return_stmt = "return "
            call_expression = return_stmt + self.type_converter.convert_out(call_expression, return_type)

        impl_lines = [
            method_signature,
            "{"
            f"    {call_expression};",
            "}",
            ""
        ]

        self.declarations.write(method_signature + ";\n")
        self.implementations.write("\n".join(impl_lines))

    def _create_delegate_name(self,
                              class_model: Union[ApiClass, ApiInterface],
                              method_name: str,
                              parameters: List[ApiParameterModel]) -> str:
        """
        Gets the name for an exported method, considering method overloading.
        """
        name_prefix = mangle_name(class_model.qualified_name) + "_"

        return name_prefix + resolve_overloaded_name(class_model, method_name, parameters)

    def _create_signature(self,
                          method_name: str,
                          method_return_type: Optional[ApiTypeRef],
                          method_parameters: List[ApiParameterModel]):

        type_converter = self.type_converter

        # Handle the special case where a method needs to be reformed because the return type
        # is non-trivial
        result = type_converter.get_wrapper_type(method_return_type)
        result += f" {method_name}("

        # Write method parameters
        for i in range(0, len(method_parameters)):
            param = method_parameters[i]
            if i > 0:
                result += ", "
            result += type_converter.get_wrapper_type(param.type)
            result += " "
            result += param.name

        result += ")"

        return result
