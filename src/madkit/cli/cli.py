import cyclopts

app = cyclopts.App(name="madkit", version="1.0.0-LittleEndian")


def main() -> None:
    from .commands import unpack  # type: ignore # noqa: F401
    from .commands import unpack_directory  # type: ignore # noqa: F401
    from .commands import repack  # type: ignore # noqa: F401
    #from .commands import txd_unpack  # type: ignore # noqa: F401
    #from .commands import txd_add_texture  # type: ignore # noqa: F401
    from .commands import mod  # type: ignore # noqa: F401
    from .commands import config  # type: ignore # noqa: F401

    app()
