from lib.parser import Parser


def readStringTable(buf: Parser):
    tableEntries = buf.readUint32()
    table = []
    for _ in range(tableEntries):
        string_length = buf.readUint8()
        entry = {
            "len": string_length,
            "string": buf.readString(string_length),
            "metadata": buf.readUint32(),
        }
        table.append(entry)
    return table


def safe_name(table, idx):
    if 0 <= idx < len(table):
        return table[idx]["string"]
    return None


def opcode_name(op, op_table):
    if 0 <= op < len(op_table):
        return op_table[op]["string"]
    return f"OP_0x{op:02X}"


def fmt_idx(idx, table):
    return str(idx)

debug_variable_counter = 0
debug_variables = {
}


with open("Levels/KingOfNY/562_RW_Balloon.ai", "rb") as f:
    buf = Parser(f.read())

    scriptNameLength = buf.readUint8()
    scriptName = buf.readString(scriptNameLength)

    unk_count = buf.readUint32()

    table1 = readStringTable(buf)  # opcode names
    table2 = readStringTable(buf)  # sounds/actors (probably)
    table3 = readStringTable(buf)  # actors (probably)

    print(f"Script Name: {scriptName}")
    print(f"Unknown Count: {unk_count}")
    print(f"Opcode Table: {len(table1)} entries")
    for i, entry in enumerate(table1):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")
    print(f"Table 2: {len(table2)} entries")
    for i, entry in enumerate(table2):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")
    print(f"Table 3: {len(table3)} entries")
    for i, entry in enumerate(table3):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")

    instruction_count = buf.readUint32()
    instructions = []
    for _ in range(instruction_count):
        instruction = {
            "opcode": buf.readUint8(),
            "a": buf.readUint8(),
            "b": buf.readUint8(),
            "c": buf.readUint8(),
            "d": buf.readUint8(),
            "payload_size": buf.readUint8(),
        }
        instruction["payload"] = buf.readBytes(instruction["payload_size"])
        instructions.append(instruction)

    print("----- INSTRUCTIONS -----")
    indent = 0
    stack = []  # remaining transitive-instruction count per open block

    for instr in instructions:
        op = instr["opcode"]
        op_name = opcode_name(op, table1)

        a = instr["a"]
        b = instr["b"]
        c = instr["c"]
        d = instr["d"]
        payload_hex = instr["payload"].hex()

        prefix = "   " * indent

        if op_name == "comment:::op-code":
            payload_buf = Parser(instr["payload"])
            comment_length = payload_buf.readUint8()
            comment_string = payload_buf.readString(comment_length)
            line = f"{prefix}// {comment_string}"
        elif op_name == "print::op-code":
            payload_buf = Parser(instr["payload"])
            unknown = payload_buf.readUint32()
            print_length = payload_buf.readUint8()
            comment_string = payload_buf.readString(print_length)
            line = f'{prefix}PRINT "{comment_string}", unknown: {unknown}'
        elif op_name == "play animation::op-code":
            payload_buf = Parser(instr["payload"])
            animation_idx = payload_buf.readUint8()
            line = f"{prefix}PLAY ANIMATION, IDX: {animation_idx}"
        elif op_name == "create variable::op-code": 
            payload_buf = Parser(instr["payload"])
            variable = payload_buf.readBytes(4)
            debug_variables[variable.hex()] = f"var{debug_variable_counter}"
            line = f"{prefix}CREATE VARIABLE, VARIABLE: {variable.hex()} (var{debug_variable_counter})"
            debug_variable_counter += 1
        elif op_name == "check valude::op-code":
            payload_buf = Parser(instr["payload"])
            variable = payload_buf.readBytes(4)
            line = f"{prefix}CHECK VALUE, VARIABLE: {variable.hex()}"
        elif op_name == "set value::op-code":
            payload_buf = Parser(instr["payload"])
            value = payload_buf.readBytes(4)
            operation = payload_buf.readUint8()
            newValue = payload_buf.readBytes(4)
            if variable.hex() in debug_variables:
                var_name = debug_variables[variable.hex()]
                line = f"{prefix}SET VALUE, VAR: {var_name}, OPERATION: {operation}, NEW VALUE: {newValue.hex()}"
            else:
                line = f"{prefix}SET VALUE, POS: {value.hex()}, OPERATION: {operation}, NEW VALUE: {newValue.hex()}"
        else:
            line = (
                f"{prefix}{op_name:<26} "
                f"A: {fmt_idx(a, table2):<3} "
                f"B: {fmt_idx(b, table2):<3} "   #figured out so far
                f"C: {fmt_idx(c, table3):<3} " # always 0 in tested scirpts
                f"D: {d:<3} " # always 0 in tested scirpts
                f"Payload: {payload_hex}"
            )
        if c > 0:
            raise NotImplementedError(f"Unhandle instruction prop: {b} in opcode {op_name}")
        if d > 0:
            raise NotImplementedError(f"Unhandle instruction prop: {b} in opcode {op_name}")
        print(line)

        # This instruction occupies one transitive slot in every currently-open block.
        for j in range(len(stack)):
            stack[j] -= 1

        # Close any blocks whose body has been fully consumed.
        while stack and stack[-1] <= 0:
            stack.pop()
            indent -= 1

        # If this instruction opens a block, push its body size (in instructions).
        if b > 0:
            stack.append(b // 8)
            indent += 1
        #if a > 0:
        #    stack.append(a // 8)
        #    indent += 1

    if stack:
        print(f"// WARNING: {len(stack)} block(s) did not close cleanly; remaining: {stack}")