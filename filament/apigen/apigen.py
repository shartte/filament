import os.path
from clang import cindex
from typing import Iterable
import tempfile
from apiparser import ApiModelParser
from apimodel import ApiModel
from directories import *
from json import dumps


def get_defines() -> List[str]:
    """
    Get a list of additional defines that are required to parse the public clang API.
    :return:
    """
    return [
        "_USE_MATH_DEFINES"
    ]


def find_headers() -> Iterable[str]:
    """
    Find all public filament headers to generate an API specification for.
    :return: List of C++ include paths (i.e. "filament/Camera.h")
    """
    filament_includes = repo_root.joinpath("filament/include")
    files = filament_includes.glob("filament/**/*.h")
    return map(lambda x: str(x.relative_to(filament_includes)), files)


def build_translation_unit() -> Path:
    """
    Creates a C++ translation unit that includes all public headers so that they can be
    parsed en-block by libclang. Keep in mind that libclang can only parse translation units
    that are actually on disk.
    :param file: Where to write the translation unit to.
    """
    headers = find_headers()

    translation_unit = Path(tempfile.mktemp(".cpp", "filament_api"))

    with translation_unit.open("wt") as fh:
        fh.writelines(map(lambda x: f"#include <{x}>\n", headers))

    return translation_unit


def write_diagnostics(diagnostics: Iterable[cindex.Diagnostic]):
    """
    Prints diagnostic information returned by clang to the console.
    """
    for diag in diagnostics:
        print(diag)


def parse_translation_unit(file: Path) -> ApiModel:
    clang_args = [
        # Add all required include paths
        *map(lambda x: f"-I{x}", get_public_include_paths()),
        # Add additional defines
        *map(lambda x: f"-D{x}", get_defines()),
        # Force C++ language
        "-x", "c++",
        # Enable C++ 14 standard
        "--std=c++14",
    ]

    index = cindex.Index.create()

    # Parse the translation unit
    tu = cindex.TranslationUnit.from_source(
        str(file),
        clang_args,
        index=index
    )
    write_diagnostics(tu.diagnostics)

    parser = ApiModelParser(tu)
    return parser.parse_api()


def build_apispec():
    translation_unit = build_translation_unit()

    try:
        api_model = parse_translation_unit(translation_unit)

    finally:
        translation_unit.unlink()

    for api_class in api_model.classes:
        print(dumps(api_class.to_dict(), indent="  "))


if __name__ == "__main__":
    build_apispec()
