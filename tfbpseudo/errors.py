"""Errors raised while turning TfbPseudo source into a script file and back."""


class ParseError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"{line}:{col}: {msg}")
        self.line, self.col = line, col


class CompileError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"{line}:{col}: {msg}")
        self.line, self.col = line, col


class DecompileError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        # There is no source position to point at unless a caller knows one.
        super().__init__(f"{line}:{col}: {msg}" if line or col else msg)
        self.line, self.col = line, col
