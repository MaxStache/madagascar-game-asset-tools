from dataclasses import dataclass, field


def str_set() -> set[str]:
    return set()


@dataclass
class DebugStore:
    """
    Stores debug information while parsing a scirpt
    """

    unresolved_ops: set[str] = field(default_factory=str_set)
