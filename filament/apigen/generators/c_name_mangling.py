from typing import List, Union

from model import ApiParameterModel, ApiClass, ApiInterface, ApiMethod

CONSTRUCTOR_NAME = "Create"
DESTRUCTOR_NAME = "Destroy"


def mangle_name(name: str) -> str:
    return name.replace("::", "_")


def resolve_overloaded_name(
        class_model: Union[ApiClass, ApiInterface],
        method_name: str,
        parameters: List[ApiParameterModel]) -> str:
    """
    Gets a unique name for a method, considering method overloading.
    """

    # Are there other models in the class with the same name?
    conflicts = []
    if isinstance(class_model, ApiClass):
        other_methods = class_model.methods + class_model.static_methods

        # Consider constructors to be methods with name "Create" for purposes
        # of overload resolution
        other_methods += [ApiMethod(CONSTRUCTOR_NAME, None, x.parameters) for x in class_model.constructors]

        # Destructors are considered parameter less functions with name "Destroy"
        if class_model.destructible:
            other_methods += [ApiMethod(DESTRUCTOR_NAME, None, [])]
    else:
        other_methods = class_model.methods
    for other_method in other_methods:
        if other_method.name == method_name:
            conflicts.append(other_method.parameters)

    if len(conflicts) == 0 or (len(conflicts) == 1 and conflicts[0] == parameters):
        return method_name

    index_of_method = conflicts.index(parameters) + 1

    return method_name + str(index_of_method)
