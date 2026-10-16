"""The top-level TFB script (.ai) file."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from tfbscript import ansi
from tfbscript.binary import BinaryReader, write_u32, write_u8
from tfbscript.arena import arena_dwords
from tfbscript.debug import DebugStore
from tfbscript.opcodes import Opcode, ParserContext
from tfbscript.string_table import StringTable


@dataclass
class ScriptFile:
    """A parsed TFB script (.ai) file."""

    _file_path: Path | None = field(default=None)

    magic_string: str = field(default="TFB Script")
    unk: bytes = field(
        default=b"\x00\x00\x00\x00"
    )  # 4 unknown bytes after the magic string

    opcode_table: StringTable = field(default_factory=StringTable)
    global_refs: StringTable = field(default_factory=StringTable)
    local_refs: StringTable = field(default_factory=StringTable)

    instructions: list[Opcode] = field(default_factory=list)

    @classmethod
    def read(
        cls, reader: BinaryReader, debugOptions: dict[str, bool | int] | None = None
    ) -> "ScriptFile":
        """Read a ScriptFile from a binary reader."""

        if debugOptions is None:
            debugOptions = {}

        debug_store: DebugStore = DebugStore()

        magic_string = reader.read_string(reader.read_u8())
        #print(magic_string)
        unk = reader.read_bytes(4)

        opcode_table = StringTable.read(reader)
        global_refs = StringTable.read(reader)
        local_refs = StringTable.read(reader)

        instruction_count = reader.read_u32()
        context = ParserContext(opcode_table, global_refs, local_refs)

        instructions: list[Opcode] = []
        instructions_read = 0
        try:
            while instructions_read < instruction_count:
                instruction = Opcode.read(
                    reader, context, debug_store=debug_store, debugOptions=debugOptions
                )
                instructions.append(instruction)
                # Count the instruction and its descendants.
                instructions_read += instruction.total_span()
        except Exception as error:
            raise ValueError(
                f"Error reading instruction {instructions_read}: {error}"
            ) from error

        if debugOptions.get("listUnresolvedOps"):
            if len(debug_store.unresolved_ops) > 0:
                print(f"Unresolved ops: {' '.join(debug_store.unresolved_ops)}")
            else:
                print("Unresolved ops: None \U0001f973")  # None :party_emoji:

        return cls(
            magic_string=magic_string,
            unk=unk,
            opcode_table=opcode_table,
            global_refs=global_refs,
            local_refs=local_refs,
            instructions=instructions,
        )

    def write(self, f: BinaryIO) -> None:
        """Write the ScriptFile to a binary file."""

        write_u8(f, len(self.magic_string))
        f.write(self.magic_string.encode("latin1"))

        # The 4 bytes after the magic are the opcode-arena size in dwords; see
        # tfbscript/arena.py. Recompute it so edits that add instructions stay
        # loadable, but never write a value smaller than the one the file came
        # with: the field is an allocation size, so over-reserving is harmless
        # while under-reserving would corrupt the loader's bump allocator.
        computed = arena_dwords(self)
        if computed is None:
            f.write(self.unk)
        else:
            write_u32(f, max(computed, int.from_bytes(self.unk, "little")))

        self.opcode_table.write(f)
        self.global_refs.write(f)
        self.local_refs.write(f)

        instruction_count = sum(
            instruction.total_span() for instruction in self.instructions
        )

        write_u32(f, instruction_count)
        for instruction in self.instructions:
            instruction.write(f)

    @classmethod
    def from_path(
        cls, path: str | Path, debugOptions: dict[str, bool | int] | None = None
    ) -> "ScriptFile":
        """Read a ScriptFile from an .ai file on disk."""

        if debugOptions is None:
            debugOptions = {}

        data = Path(path).read_bytes()

        script = cls.read(
            BinaryReader(data, little_endian=True), debugOptions=debugOptions
        )
        script._file_path = Path(path)
        return script

    @staticmethod
    def _print_ref_table(title: str, table: StringTable) -> None:
        """Print one reference table as `index: name::category::type  [metadata]`."""
        print(ansi.comment(f"----- {title} ({len(table)} entries) -----"))

        for index, entry in enumerate(table.entries):
            parts = [ansi.variable(entry.name)]
            if entry.category is not None:
                parts.append(ansi.builtin(entry.category))
            parts.append(ansi.type_(entry.type))

            metadata = entry.metadata.hex(" ")

            print(
                f"  {ansi.number(f'{index:>3}')}: {'::'.join(parts)}"
                + f"  {ansi.comment(f'[{metadata}]')}"
            )

    def print_tree(self) -> None:
        """Print the reference tables, then the whole script as indented pseudo-source."""
        print()
        self._print_ref_table("GLOBAL REFS", self.global_refs)
        print()
        self._print_ref_table("LOCAL REFS", self.local_refs)
        print()
        self._print_ref_table("OPCODES", self.opcode_table)
        print()
        print(ansi.comment("----- INSTRUCTIONS -----"))

        for instruction in self.instructions:
            instruction.print_tree()
