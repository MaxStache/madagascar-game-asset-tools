import cyclopts

app = cyclopts.App(name="madkit", version="1.0.0-LittleEndian")


def main() -> None:
    # from .commands import txd_unpack  # type: ignore
    # from .commands import txd_add_texture  # type: ignore
    from .commands import (
        config,  # type: ignore # noqa: F401
        mod,  # type: ignore # noqa: F401
        repack,  # type: ignore # noqa: F401
        unpack,  # type: ignore # noqa: F401
        unpack_directory,  # type: ignore # noqa: F401
        upgrade,  # type: ignore # noqa: F401
    )

    app()
