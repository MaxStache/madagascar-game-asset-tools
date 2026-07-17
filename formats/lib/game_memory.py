import ctypes
import platform

if platform.system() == "Windows":
    import pymem
    import pymem.process


class PlayerPosition:
    BASE_OFFSET = 0x0021818C

    OFF_X = 0x150
    OFF_Y = 0x154
    OFF_Z = 0x158

    def __init__(self, process_name="Game.exe"):
        if platform.system() != "Windows":
            return
        
        self.pm = pymem.Pymem(process_name)
        self.base = self._resolve_base(process_name)

    def _resolve_base(self, process_name):
        # 1. canonical path: main module via EnumProcessModulesEx
        try:
            base = self.pm.base_address
            if base:
                return base
        except Exception:
            pass

        # 2. fallback: case-insensitive scan over the snapshot
        target = process_name.lower()
        found = []
        for module in pymem.process.list_modules(self.pm.process_handle):
            name = module.name
            if isinstance(name, bytes):
                name = name.decode("utf-8", "ignore")
            found.append(name)
            if name.lower() == target:
                return module.lpBaseOfDll

        raise RuntimeError(
            f"Could not resolve base address for {process_name!r}. "
            f"Modules visible: {found or '<none — bitness mismatch?>'} "
            f"(python={8 * ctypes.sizeof(ctypes.c_void_p)}-bit, "
            f"target_is_wow64={self._is_wow64()})"
        )

    def _is_wow64(self):
        result = ctypes.c_int(0)
        ok = ctypes.windll.kernel32.IsWow64Process(
            self.pm.process_handle,
            ctypes.byref(result),
        )
        return bool(result.value) if ok else None

    def _resolve_pointer(self):
        addr = self.pm.read_uint(self.base + self.BASE_OFFSET)
        if not addr:
            raise RuntimeError("Null pointer at base + BASE_OFFSET")

        addr = self.pm.read_uint(addr + 0xA8)
        if not addr:
            raise RuntimeError("Null pointer at +0xA8")

        addr = self.pm.read_uint(addr + 0x230)
        if not addr:
            raise RuntimeError("Null pointer at +0x230")

        return addr

    @property
    def address(self):
        return self._resolve_pointer()

    @property
    def x(self):
        return self.pm.read_float(self.address + self.OFF_X)

    @x.setter
    def x(self, value):
        self.pm.write_float(self.address + self.OFF_X, float(value))

    @property
    def y(self):
        return self.pm.read_float(self.address + self.OFF_Y)

    @y.setter
    def y(self, value):
        self.pm.write_float(self.address + self.OFF_Y, float(value))

    @property
    def z(self):
        return self.pm.read_float(self.address + self.OFF_Z)

    @z.setter
    def z(self, value):
        self.pm.write_float(self.address + self.OFF_Z, float(value))

    @property
    def position(self):
        addr = self.address
        return (
            self.pm.read_float(addr + self.OFF_X),
            self.pm.read_float(addr + self.OFF_Y),
            self.pm.read_float(addr + self.OFF_Z),
        )

    @position.setter
    def position(self, value):
        self.set_position(*value)

    def set_position(self, x=None, y=None, z=None):
        if platform.system() != "Windows":
            return
        addr = self.address

        for offset, value in (
            (self.OFF_X, x),
            (self.OFF_Y, y),
            (self.OFF_Z, z),
        ):
            if value is not None:
                self.pm.write_float(addr + offset, float(value))