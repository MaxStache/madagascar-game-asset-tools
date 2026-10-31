from pathlib import Path

from madformats.lib.parser import Parser
from tfbscript.string_table import StringTable

folder = Path("example_scripts/kony")

OP_CODE = "cut-scene"


def check_occurance(file: Path):
    with open(file, "rb") as f:
        reader = Parser(f.read())

        _magic_string = reader.readString(reader.readUint8())
        _unk = reader.readBytes(4)

        opcode_table = StringTable.read(reader)
        _global_refs = StringTable.read(reader)
        _local_refs = StringTable.read(reader)

        #for e in _global_refs.entries:
        #    if "Melman Kick Lays" in e.string:
        #        print(file)
        #        print("DKWOAHDIUAWOHDIOWA")

        instruction_count = reader.readUint32()
        occurance_count = 0
        for _ in range(instruction_count):
            op_idx = reader.readUint8()
            reader.skip(4)
            reader.skip(reader.readUint8())
            if op_idx == 0xFF:
                continue
            else:
                op_name = opcode_table.get(op_idx)
                if op_name is None:
                    print(f"Opcode index {op_idx} not found in opcode table.")
                    continue
                if OP_CODE in op_name.string:
                    occurance_count += 1

        return occurance_count


for file in folder.rglob("*.ai"):
    count = check_occurance(file)

    if count:
        print(f"{file}: {count}")
