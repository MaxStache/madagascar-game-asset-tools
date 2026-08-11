import cyclopts

app = cyclopts.App(name="cli", version="1.0.0-LittleEndian")


def main() -> None:
    # Imported for their @app.command side effects. Deferred until here so
    # `from ..cli import app` in each command resolves against this module
    # after `app` exists.
    from .commands import unpack  # type: ignore # noqa: F401
    from .commands import repack  # type: ignore # noqa: F401

    app()
