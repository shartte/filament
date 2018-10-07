import re
from typing import Optional, Set, Union, Any, Tuple

import settings
from clang.cindex import TranslationUnit, Cursor, CursorKind, SourceLocation, Type, TypeKind, AccessSpecifier
from directories import *
from model import ApiModel, ApiClass, ApiConstructor, ApiParameterModel, ApiTypeRef, ApiEnumRef, ApiPrimitiveType, \
    PrimitiveTypeKind, ApiMethod, ApiClassRef, ApiPassByRef, ApiPassByRefType, ApiEnum, ApiEnumConstant, ApiValueType, \
    ApiInterface, ApiAnonymousCallback, ApiCallbackRef, ApiCallback, ApiBitsetType, ApiEntityInstance, ApiConstantArray, \
    ApiValueTypeRef, ApiStringType, ApiOpaqueRef
# Cache of paths that are considered public includes of the filament API
from model.value_types import ApiValueTypeField

_public_includes = set()

ENTITY_INSTANCE_PATTERN = re.compile("""utils::EntityInstance<([^,>]+).*>""")


def _is_in_public_header(cursor: Cursor) -> bool:
    """
    Tries to determine whether a cursor is within a system header.
    libclang itself has Location_isInSystemHeader, but the Python bindings don't expose this method.
    :param cursor:
    :return:
    """
    location: SourceLocation = cursor.location
    if not location.file:
        return False  # Unclear what conditions cause this

    src_path = Path(location.file.name)
    if src_path in _public_includes:
        return True

    found = False
    for public_include_dir in get_public_include_paths():
        try:
            src_path.relative_to(public_include_dir)
            _public_includes.add(src_path)
            found = True
            break
        except ValueError:
            pass
    return found


def _get_qualified_name(cursor: Cursor) -> str:
    """
    Creates a fully qualified name for the cursor, i.e. filament::Camera or filament::Texture::Builder.
    :param cursor:
    :return:
    """

    display_name = cursor.displayname
    parent = cursor.semantic_parent
    if parent and (
            parent.kind == CursorKind.NAMESPACE or parent.kind == CursorKind.CLASS_DECL or parent.kind == CursorKind.CLASS_TEMPLATE):
        display_name = _get_qualified_name(parent) + "::" + display_name
    return display_name


def _get_base_classes(cursor: Cursor, include_transitive: bool = True) -> Set[str]:
    """
    Determine base classes for a C++ class pointed to by the given cursor.
    The cursor must be at the actual definition, not just a forward declaration.
    """
    if cursor.kind != CursorKind.CLASS_DECL and cursor.kind != CursorKind.CLASS_TEMPLATE \
            and cursor.kind != CursorKind.STRUCT_DECL:
        raise RuntimeError(cursor.kind)
    assert cursor.is_definition()

    for child in cursor.get_children():
        if child.kind == CursorKind.CXX_BASE_SPECIFIER:
            result = set()
            for base_spec in child.get_children():
                if base_spec.kind == CursorKind.TYPE_REF or base_spec.kind == CursorKind.TEMPLATE_REF:
                    base_def: Cursor = base_spec.get_definition()
                    if base_def:
                        result.add(_get_qualified_name(base_def))

                        # Add transitive base classes as well
                        if include_transitive:
                            result.update(_get_base_classes(base_def))
                    else:
                        # This can occur for forward-declared template arguments
                        pass
            return result

    return set()


def _get_public_constructors(cursor: Cursor) -> Optional[List[Cursor]]:
    """
    Finds all public constructors of the class pointed at by the given cursor.
    :param cursor:
    :return: None if the class has no public constructors. An empty list if it only has the default constructor.
    """
    base_classes = _get_base_classes(cursor)
    if settings.borrowed_obj_superclass in base_classes:
        return None

    explicit_default_constructor_found = False

    constructors = []

    for child in cursor.get_children():
        if child.kind != CursorKind.CONSTRUCTOR:
            continue

        if child.is_copy_constructor() or child.is_move_constructor():
            continue  # Ignore copy and move constructors

        if child.is_default_constructor():
            explicit_default_constructor_found = True

        if child.access_specifier == AccessSpecifier.PUBLIC:
            constructors.append(child)

    if explicit_default_constructor_found and len(constructors) == 0:
        # If an explicit default constructor is found, and it is not public,
        # and no other public constructors exist, then the class is not constructable
        return None

    return constructors


def _is_destructible(cursor: Cursor) -> bool:
    """
    Check if the class has a publicly visible destructor, making it possible for the client to dispose of it.
    """

    explicit_public_destructor = False
    has_non_destructible_baseclass = False

    for child in cursor.get_children():
        # Check base classes for destructibility
        if child.kind == CursorKind.CXX_BASE_SPECIFIER:
            for base_spec in child.get_children():
                if base_spec.kind == CursorKind.TYPE_REF or base_spec.kind == CursorKind.TEMPLATE_REF:
                    base_def: Cursor = base_spec.get_definition()
                    if base_def and not _is_destructible(base_def):
                        has_non_destructible_baseclass = True

        if child.kind != CursorKind.DESTRUCTOR:
            continue
        if child.access_specifier != AccessSpecifier.PUBLIC:
            return False
        else:
            explicit_public_destructor = True  # may override a protected base class destructor

    if has_non_destructible_baseclass:
        return explicit_public_destructor

    # If no base class makes it hidden, the subclass is destructible by default as well
    return True


_primitive_type_map = {
    TypeKind.BOOL: PrimitiveTypeKind.BOOL,
    TypeKind.SCHAR: PrimitiveTypeKind.INT8,
    TypeKind.CHAR_S: PrimitiveTypeKind.INT8,
    TypeKind.UCHAR: PrimitiveTypeKind.UINT8,
    TypeKind.SHORT: PrimitiveTypeKind.INT16,
    TypeKind.USHORT: PrimitiveTypeKind.UINT16,
    TypeKind.INT: PrimitiveTypeKind.INT32,
    TypeKind.UINT: PrimitiveTypeKind.UINT32,
    TypeKind.LONGLONG: PrimitiveTypeKind.INT64,
    TypeKind.ULONGLONG: PrimitiveTypeKind.UINT64,
    TypeKind.FLOAT: PrimitiveTypeKind.FLOAT,
    TypeKind.DOUBLE: PrimitiveTypeKind.DOUBLE
}


def _dump_cursor(cursor: Cursor, indent: str = ""):
    print(indent + cursor.spelling + " (" + str(cursor.kind) + ")")
    indent = "  " + indent
    for c in cursor.get_children():
        _dump_cursor(c, indent)


# Declaration should be hidden from API spec document
ATTR_HIDE_FROM_SPEC = "hide_from_spec"


# Find all annotations of the form __attribute__((annotate("x")))
def _find_annotations(cursor: Cursor) -> Set[str]:
    if cursor.kind == CursorKind.ANNOTATE_ATTR:
        return {cursor.spelling}
    result = set()
    for child in cursor.get_children():
        result.update(_find_annotations(child))
    return result


def get_method_comparison_obj(method) -> Tuple[Any, bool]:
    method_obj = method.to_dict()
    # Clear out the const-ness of the return-value for comparisons sake
    has_const_return = False
    if isinstance(method.return_type, ApiPassByRef):
        if method.return_type.const:
            method_obj["return_type"]["const"] = False
            has_const_return = True
    return method_obj, has_const_return


def _remove_duplicate_methods(methods) -> List[ApiMethod]:
    # Remove duplicates, which can occur because of const methods
    filtered_methods = []
    for i in range(0, len(methods)):
        method, i_has_const_return = get_method_comparison_obj(methods[i])
        keep = True

        for j in range(i + 1, len(methods)):
            other_method, j_has_const_return = get_method_comparison_obj(methods[j])
            if method == other_method:
                # Prefer to delete the const version
                print("Removing duplicate method", methods[i].name)
                if not i_has_const_return:
                    keep = False
                    break

        if keep:
            filtered_methods.append(methods[i])
    return filtered_methods


class ApiModelParser:

    def __init__(self, translation_unit: TranslationUnit):
        self.translation_unit = translation_unit
        self._model: ApiModel = None

    def _build_callback_type(self, type: Type) -> Union[ApiCallbackRef, ApiAnonymousCallback]:
        """
        Given a function declaration type and an optional typedef name for it, return a callback type that
        describes it.
        """
        if type.kind == TypeKind.FUNCTIONPROTO:
            params = [self._build_type_model(t) for t in type.argument_types()]
            return_type = self._build_type_model(type.get_result())
            return ApiAnonymousCallback(return_type, params, type.spelling)

        assert type.kind == TypeKind.TYPEDEF

        type_decl: Cursor = type.get_declaration()
        typedef_name = _get_qualified_name(type_decl)

        found_callback = False
        for callback in self._model.callbacks:
            if callback.qualified_name == typedef_name:
                found_callback = True
                break

        return_type = self._build_type_model(type.get_canonical().get_pointee().get_result())
        params = self._build_method_parameters_models(type_decl)

        # Save the callback type if it didn't already exist
        if not found_callback:
            self._model.callbacks.append(ApiCallback(
                typedef_name, return_type, params
            ))

        # Treat it as a reference
        return ApiCallbackRef(typedef_name)

    def _build_type_model(self, type: Type, typedef_type: Optional[Type] = None) -> Optional[ApiTypeRef]:
        if type.kind == TypeKind.VOID:
            return None
        elif type.kind == TypeKind.ENUM:
            qualified_name = _get_qualified_name(type.get_declaration())
            return ApiEnumRef(qualified_name)
        elif type.kind == TypeKind.TYPEDEF:

            # Handle cases where the typedef name infers a certain semantic to an underlying type (i.e. color types)
            if type.spelling in settings.typedef_to_primitive_map:
                return ApiPrimitiveType(PrimitiveTypeKind[settings.typedef_to_primitive_map[type.spelling]])

            canonical_type: Type = type.get_canonical()

            # Handle a type-def'd function declaration because only the original typedef location can be
            # traced back to the declaration, and this is the only way to get the parameter names
            if canonical_type.kind == TypeKind.POINTER and canonical_type.get_pointee().kind == TypeKind.FUNCTIONPROTO:
                return self._build_callback_type(type)
            return self._build_type_model(canonical_type, typedef_type=type)
        elif type.kind in _primitive_type_map:
            return ApiPrimitiveType(_primitive_type_map[type.kind])
        elif type.kind == TypeKind.LVALUEREFERENCE:
            pointee_type = type.get_pointee()
            const_ref = pointee_type.is_const_qualified()
            return ApiPassByRef(const_ref, ApiPassByRefType.LVALUE_REF, self._build_type_model(pointee_type))
        elif type.kind == TypeKind.RVALUEREFERENCE:
            const_ref = type.is_const_qualified()
            pointee_type = type.get_pointee()
            return ApiPassByRef(const_ref, ApiPassByRefType.RVALUE_REF, self._build_type_model(pointee_type))
        elif type.kind == TypeKind.POINTER:
            pointee_type = type.get_pointee()
            const_ref = pointee_type.is_const_qualified()

            # Special case handling for function prototypes
            if pointee_type.kind == TypeKind.FUNCTIONPROTO:
                return self._build_callback_type(pointee_type)
            # Special case handling for pointer-to-char, which we consider strings
            elif pointee_type.kind == TypeKind.CHAR_S and const_ref:
                return ApiStringType()

            pointee_model = self._build_type_model(pointee_type)

            if isinstance(pointee_model, ApiClassRef):
                if pointee_model.qualified_name in settings.hidden_apis:
                    return ApiOpaqueRef(pointee_model.qualified_name)  # Converts to a void*

            return ApiPassByRef(const_ref, ApiPassByRefType.POINTER, pointee_model)
        elif type.kind == TypeKind.ELABORATED:
            # Elaborated types just seem to be a namespace qualified ref
            named_type = type.get_named_type()
            return self._build_type_model(named_type)
        elif type.kind == TypeKind.RECORD:
            record_decl: Cursor = type.get_declaration()
            record_name = _get_qualified_name(record_decl)

            # Handle special value types
            if record_name in settings.record_to_primitive_map:
                primitive_kind = PrimitiveTypeKind[settings.record_to_primitive_map[record_name]]
                return ApiPrimitiveType(primitive_kind)
            elif record_name in settings.value_types:
                return ApiValueTypeRef(record_name)

            # Handling templates really doesn't work nicely with libclang right now
            if record_name == "utils::bitset<unsigned int, 1, void>":
                return ApiBitsetType(PrimitiveTypeKind.UINT32, 1)

            m = ENTITY_INSTANCE_PATTERN.fullmatch(record_name)
            if m:
                qualified_name = m.group(1)
                return ApiEntityInstance(qualified_name)

            return ApiClassRef(record_name)
        elif type.kind == TypeKind.UNEXPOSED:
            return ApiPrimitiveType(PrimitiveTypeKind.UNEXPOSED)

        elif type.kind == TypeKind.CONSTANTARRAY:
            element_type = self._build_type_model(type.get_array_element_type())
            element_count = type.get_array_size()
            return ApiConstantArray(element_type, element_count)

        else:
            raise RuntimeError("Unsupported type: " + str(type.kind) + " (" + type.spelling + ")")

    def _build_method_parameters_models(self, method_cursor: Cursor) -> List[ApiParameterModel]:
        """
        For a cursor pointing to a method or constructor, this function will retrieve all parameters
        and return API models for them.
        """

        params = []

        for cursor in method_cursor.get_children():
            if cursor.kind == CursorKind.PARM_DECL:
                param_name = cursor.displayname
                param_type = self._build_type_model(cursor.type)
                params.append(ApiParameterModel(param_name, param_type))

        return params

    def _build_constructor_models(self, class_cursor: Cursor) -> List[ApiConstructor]:
        """
        Convert from a cursor that points to a class declaration to API models describing the publicly visible constructors,
        including an implied default constructor (if applicable).
        """
        public_constructors = _get_public_constructors(class_cursor)

        if public_constructors is None:
            return []  # No public constructors available

        if len(public_constructors) == 0:
            # Add a synthetic public default constructor
            return [ApiConstructor([])]

        result = []
        for cursor_constructor in public_constructors:
            params = self._build_method_parameters_models(cursor_constructor)
            result.append(ApiConstructor(params))
        return result

    def _build_method_models(self, class_cursor: Cursor):
        """
        Creates the API models for instance and static methods found in the class pointed to by the given cursor.
        Returns a tuple (methods, static_methods).
        """
        methods = []
        static_methods = []

        for cursor in class_cursor.get_children():
            if cursor.kind != CursorKind.CXX_METHOD:
                continue

            # Skip anything not publicly visible
            if cursor.access_specifier != AccessSpecifier.PUBLIC:
                continue

            # Skip assignment operators (for now)
            if cursor.spelling == "operator=":
                continue

            # Skip methods annotated with no_spec
            annotations = _find_annotations(cursor)
            if ATTR_HIDE_FROM_SPEC in annotations:
                print("Skipping hidden method " + cursor.spelling)
                continue

            method_name = cursor.spelling
            params = self._build_method_parameters_models(cursor)
            return_type = self._build_type_model(cursor.result_type)
            method = ApiMethod(method_name, return_type, params)

            if cursor.is_static_method():
                static_methods.append(method)
            else:
                methods.append(method)

        methods = _remove_duplicate_methods(methods)
        static_methods = _remove_duplicate_methods(static_methods)

        return methods, static_methods


    def _build_class_model(self, cursor: Cursor) -> Optional[ApiClass]:
        """
        Builds an ApiClass representation for a C++ class pointed at by a given cursor, if the
        class is configured to be a public API in settings.py
        """
        class_name = cursor.displayname
        qualified_name = _get_qualified_name(cursor)
        if qualified_name not in settings.public_apis:
            return None

        destructible = _is_destructible(cursor)

        constructors = self._build_constructor_models(cursor)
        (methods, static_methods) = self._build_method_models(cursor)

        rel_header_path = self._get_relative_path_from_cursor(cursor)

        return ApiClass(
            rel_header_path,
            qualified_name,
            class_name,
            destructible,
            constructors,
            methods,
            static_methods
        )

    def _get_relative_path_from_cursor(self, cursor: Cursor) -> str:
        # Figure out the relative include path
        rel_header_path = None
        abs_header_path = Path(cursor.location.file.name)
        for public_include_dir in get_public_include_paths():
            try:
                rel_header_path = str(abs_header_path.relative_to(public_include_dir))
                break
            except ValueError:
                pass

        if rel_header_path is None:
            raise Exception("Unable to determine relative header path for: " + str(abs_header_path))

        # Normalize to Linux style path separators
        rel_header_path = rel_header_path.replace("\\", "/")

        return rel_header_path

    def _build_interface_model(self, cursor: Cursor) -> Optional[ApiInterface]:
        """
        Builds an ApiInterface representation for a C++ class pointed at by a given cursor, if the
        class is configured to be an interface in settings.py
        """
        class_name = cursor.displayname
        qualified_name = _get_qualified_name(cursor)
        if qualified_name not in settings.interfaces:
            return None

        (methods, static_methods) = self._build_method_models(cursor)

        return ApiInterface(
            qualified_name,
            class_name,
            methods
        )

    def _build_value_type_model(self, cursor: Cursor) -> Optional[ApiValueType]:
        """
        Builds an ApiValueType representation for a C++ class or struct pointed at by a given cursor.
        """
        class_name = cursor.displayname
        qualified_name = _get_qualified_name(cursor)
        if qualified_name not in settings.value_types:
            return None

        if not _is_destructible(cursor):
            raise RuntimeError(f"{qualified_name} was configured as a value type but is not destructible")

        # Check if the struct/class has a parameter-less constructor
        constructors = self._build_constructor_models(cursor)
        found_constructor = False
        for constructor in constructors:
            if len(constructor.parameters) == 0:
                found_constructor = True
                break
        if not found_constructor:
            raise RuntimeError(f"{qualified_name} was configured as a value type but has no default constructor")

        union_field = None

        # Fields
        fields = []
        for child in cursor.get_children():
            if child.kind == CursorKind.FIELD_DECL:
                field_type = self._build_type_model(child.type)
                fields.append(ApiValueTypeField(child.spelling, field_type))
            elif child.kind == CursorKind.UNION_DECL:
                # For now we are just going to take the first one
                first_union_field = next(child.get_children())
                union_field = first_union_field.spelling
                for union_child in first_union_field.get_children():
                    if union_child.kind == CursorKind.FIELD_DECL:
                        field_type = self._build_type_model(union_child.type)
                        fields.append(ApiValueTypeField(union_child.spelling, field_type))

        rel_header_path = self._get_relative_path_from_cursor(cursor)

        return ApiValueType(
            rel_header_path,
            qualified_name,
            class_name,
            fields,
            union_field
        )

    def _build_enum_model(self, cursor: Cursor) -> Optional[ApiEnum]:
        """
        Builds an ApiEnum representation for a C++ class pointed at by a given cursor.
        """

        enum_name = cursor.displayname
        qualified_name = _get_qualified_name(cursor)

        # Get the declared base-type of the Enumeration (i.e. enum class X : int -> INT32)
        enum_type = self._build_type_model(cursor.enum_type)
        if not isinstance(enum_type, ApiPrimitiveType):
            raise RuntimeError(f"Expected base type of enum {qualified_name} to be primitive, but "
                               f"got: {enum_type.to_dict()}")
        base_type = enum_type.kind

        # Get all declared constants
        constants = []
        for child in cursor.get_children():
            if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                enum_value = child.enum_value
                constants.append(ApiEnumConstant(
                    child.spelling,
                    enum_value
                ))

        return ApiEnum(
            qualified_name,
            enum_name,
            base_type,
            constants
        )

    def _visit_cursor(self, cursor: Cursor):
        """
        Handles a cursor while recursively seeking through the translation unit.
        """

        # Only consider symbols defined in one of the public include files
        if not _is_in_public_header(cursor):
            return

        if cursor.kind == CursorKind.NAMESPACE:
            namespace = _get_qualified_name(cursor)
            # Ignore certain namespaces
            if namespace == "std" or namespace == "filament::details":
                return

        elif cursor.kind == CursorKind.CLASS_DECL or cursor.kind == CursorKind.STRUCT_DECL:
            # Fully ignore forward declarations
            if not cursor.is_definition():
                return

            # Attempt building a class model
            class_model = self._build_class_model(cursor)
            if class_model is not None:
                self._model.classes.append(class_model)

            # Attempt building an interface model
            interface_model = self._build_interface_model(cursor)
            if interface_model is not None:
                self._model.interfaces.append(interface_model)

            # Attempt building a value type model
            value_type_model = self._build_value_type_model(cursor)
            if value_type_model is not None:
                self._model.value_types.append(value_type_model)

        elif cursor.kind == CursorKind.ENUM_DECL:
            # Fully ignore forward declarations
            if not cursor.is_definition():
                return

            enum_model = self._build_enum_model(cursor)
            if enum_model is not None:
                self._model.enums.append(enum_model)

        # Recurse further into this cursor
        for child in cursor.get_children():
            self._visit_cursor(child)

    def _get_enum_refs(self) -> Set[str]:
        """
        Gets a set of the fully qualified names of all enumerations referenced by methods,
        static methods or constructors
        :return:
        """

        result = set()
        for api_class in self._model.classes:
            for method in api_class.methods + api_class.static_methods + api_class.constructors:
                for param in method.parameters:
                    if isinstance(param.type, ApiEnumRef):
                        result.add(param.type.qualified_name)
                if isinstance(method, ApiMethod) and isinstance(method.return_type, ApiEnumRef):
                    result.add(method.return_type.qualified_name)
        for value_type in self._model.value_types:
            for field in value_type.fields:
                if isinstance(field.type, ApiEnumRef):
                    result.add(field.type.qualified_name)
        return result

    def parse_api(self) -> ApiModel:
        """
        Given a cursor to the translation unit that includes all public filament headers,
        this function will recursively parse that translation unit's code model to extract
        anything of use into an ApiModel.
        """
        self._model = ApiModel()

        for child in self.translation_unit.cursor.get_children():
            self._visit_cursor(child)

        # Remove any enumerations not used
        enums = self._get_enum_refs()
        self._model.enums = [x for x in self._model.enums if x.qualified_name in enums]

        return self._model
