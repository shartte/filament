from typing import List
from pathlib import Path

# Find root of the actual repository
repo_root = Path(__file__).parent.parent.parent


def get_public_include_paths() -> List[Path]:
    """
    Get a list of all the include paths that are required to correctly parse the filament public API.
    :return:
    """
    relative_paths = [
        "filament/include",
        "libs/utils/include",
        "libs/math/include",
        "libs/filabridge/include"
    ]
    return list(map(lambda x: repo_root.joinpath(x), relative_paths))
