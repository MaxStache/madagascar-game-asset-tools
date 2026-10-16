# pyright: basic

"""Read/write the player's world position in a running Madagascar process.

Uses PyMemoryEditor, which speaks Windows, Linux (ptrace) and macOS, so the
same pointer chain works against the native game and against a Wine/Proton
copy of it.
"""

from PyMemoryEditor import OpenProcess


class PlayerPosition:
    BASE_OFFSET = 0x0021818C

    # Static "is the game paused?" flag, relative to the Game.exe image base.
    PAUSED_OFFSET = 0x0022A520

    OFF_X = 0x150
    OFF_Y = 0x154
    OFF_Z = 0x158

    # Game.exe is a 32-bit image, so every pointer in the chain is 4 bytes
    # wide - regardless of the host we are reading it from.
    PTR_SIZE = 4

    def __init__(self, process_name="Game.exe", *, pid=None, module_name=None):
        self.process_name: str = process_name
        self.process = OpenProcess(
            pid=pid,
            name=None if pid is not None else process_name,
            case_sensitive=False,
        )
        self.base: int = self._resolve_base(module_name or process_name)

    def _resolve_base(self, module_name) -> int:
        """Base address of the main module (Game.exe), defeating ASLR."""
        target = module_name.lower()
        found = []

        first_base = None
        for module in self.process.get_modules():
            name = module.name or module.path.replace("\\", "/").rsplit("/", 1)[-1]
            found.append(name)

            if first_base is None:
                first_base = module.base_address

            if name.lower() == target:
                return module.base_address

        # Fallback: the loader maps the executable itself first, so the first
        # module is the main image on every backend.
        if first_base is not None:
            return first_base

        raise RuntimeError(
            f"Could not resolve base address for {module_name!r} "
            f"(pid={self.process.pid}). "
            f"Modules visible: {found or '<none - permission or bitness mismatch?>'}"
        )

    def _read_pointer(self, address) -> int:
        return int.from_bytes(
            self.process.read_bytes(address, self.PTR_SIZE),
            "little",
            signed=False,
        )

    def _resolve_pointer(self) -> int:
        addr = self._read_pointer(self.base + self.BASE_OFFSET)
        if not addr:
            raise RuntimeError("Null pointer at base + BASE_OFFSET")

        addr = self._read_pointer(addr + 0xA8)
        if not addr:
            raise RuntimeError("Null pointer at +0xA8")

        addr = self._read_pointer(addr + 0x230)
        if not addr:
            raise RuntimeError("Null pointer at +0x230")

        return addr

    def close(self):
        self.process.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def address(self):
        return self._resolve_pointer()

    @property
    def paused_raw(self) -> int:
        """Raw value of the pause flag (0 = running, non-zero = paused)."""
        return self._read_pointer(self.base + self.PAUSED_OFFSET)

    @property
    def paused(self) -> bool:
        return self.paused_raw != 0

    @property
    def x(self):
        return self.process.read_float(self.address + self.OFF_X)

    @x.setter
    def x(self, value):
        self.process.write_float(self.address + self.OFF_X, float(value))

    @property
    def y(self):
        return self.process.read_float(self.address + self.OFF_Y)

    @y.setter
    def y(self, value):
        self.process.write_float(self.address + self.OFF_Y, float(value))

    @property
    def z(self):
        return self.process.read_float(self.address + self.OFF_Z)

    @z.setter
    def z(self, value):
        self.process.write_float(self.address + self.OFF_Z, float(value))

    @property
    def position(self):
        addr = self.address
        return (
            self.process.read_float(addr + self.OFF_X),
            self.process.read_float(addr + self.OFF_Y),
            self.process.read_float(addr + self.OFF_Z),
        )

    @position.setter
    def position(self, value):
        self.set_position(*value)

    def set_position(self, x=None, y=None, z=None):
        addr = self.address

        for offset, value in (
            (self.OFF_X, x),
            (self.OFF_Y, y),
            (self.OFF_Z, z),
        ):
            if value is not None:
                self.process.write_float(addr + offset, float(value))
