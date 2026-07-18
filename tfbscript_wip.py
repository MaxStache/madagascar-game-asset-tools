from enum import IntEnum

from formats.lib.parser import Parser
from formats.lib.sytax_hilighting import Color, color_text
from formats.lib.tfb_reference import Reference, parse_reference
from formats.lib.tfb_rhs import read_rhs, rhs_to_string

import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

ENABLE_ANSI_COLORING = True
TABLE1 = []
TABLE2 = []
TABLE3 = []
UNIMPLEMENTED_OPCODES = set()

FILTER_OUT_PLUS_MINUS_ZERO_IN_RHS = True  # if true (Ref: Script Time::value + Int32: 0) will be printed as (Ref: Script Time::value)
SHOW_RHS_TYPES = False  # if true will show types like "Int32: 0"


class OpParser(Parser):
    def readRef(self):
        ref_bytes = self.readBytes(4)
        return parse_reference(ref_bytes, offset=0, table2=TABLE2, table3=TABLE3)

    def readRHS(self):
        return read_rhs(self, table2=TABLE2, table3=TABLE3)


class RelOp(IntEnum):
    """Relational operator for OpAbstractCheckValue / OpCheckValue."""

    LessOrEq = 0
    Eq = 1
    GreatOrEq = 2
    Less = 3
    Great = 4
    NotEq = 5

    def symbol(self) -> str:
        return ("<=", "==", ">=", "<", ">", "!=")[self.value]


class MembershipTest(IntEnum):
    """Membership test for OpCheckMembership."""

    includes = 0  # set_a includes element_a (element could be a set itself, that is called a subset)
    excludes = 1  # set_a excludes element_a (element could be a set itself, that is called a subset)
    intersects_with = 2  # set_a intersects with_b (set_a has at least one element in common with set_b)
    includes_all = 3  # set_a all in set_b

    def symbol(self) -> str:
        # assumes format is "set_a <membership_test> element_a" or "set_a <membership_test> set_b"
        return ("in", "not in", "intersects with", "all in")[self.value]


class CheckFOVMode(IntEnum):
    """Mode for OpCheckFOV."""

    ignore_obstructions = 0

    consider_obstructions = 1


# fmt: off
class MembershipCombiner(IntEnum):
    """Membership combiner for OpChangeMembership."""

    include        = 0
    exclude        = 1
    intersect_with = 2
    be_replaced_by = 3  
    add            = 4  # add all elements of set_b to set_a (set_a becomes the union of set_a and set_b)
    exclude_all    = 5  # unknown

    def symbol(self) -> str:
        # assumes format is "set_a.<membership_combiner>(element_a)" or "set_a.<membership_combiner>(set_b)"
        return ("include", "remove", "intersectWith", "replaceWith", "add", "removeAll")[self.value]

# fmt: on


class CombineMode(IntEnum):
    """Displacement combine mode for OpDisplace."""

    relative = 0
    absolute = 1
    local = 2


class Direction(IntEnum):
    """Facing/orientation (or iteration order) selector.

    The byte after the target reference in teleport to / move to / find subset /
    for each. Game.exe reads it via FUN_0042fc60 using the name table at
    0x00603044 (PTR_s_forward): {forward, backward, randomly}. It picks which way
    the actor faces after moving (or the order a collection is iterated).
    """

    forward = 0
    backward = 1
    randomly = 2


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


def opcode_name(op, op_table):
    if 0 <= op < len(op_table):
        return op_table[op]["string"]
    return f"OP_0x{op:02X}"


def BUILD_LINE(
    prefix: str,
    op_name: str,
    content: str,
):
    colored_name = (
        color_text(op_name, Color.METHOD) if ENABLE_ANSI_COLORING else op_name
    )
    line = f"{prefix}{colored_name} {content}"

    return line


def CRef(
    ref: Reference,
):
    return color_text(ref, Color.REFERENCE) if ENABLE_ANSI_COLORING else str(ref)


def CRelOp(
    rel_op: RelOp,
):
    return (
        color_text(rel_op.symbol(), Color.OPERATOR)
        if ENABLE_ANSI_COLORING
        else rel_op.symbol()
    )


def CRHS(
    rhs,
):
    return rhs_to_string(
        rhs, ENABLE_ANSI_COLORING, FILTER_OUT_PLUS_MINUS_ZERO_IN_RHS, SHOW_RHS_TYPES
    )


def CNum(
    num,
):
    return color_text(str(num), Color.NUMBER) if ENABLE_ANSI_COLORING else str(num)


def CStr(
    string,
):
    return (
        color_text(str(f'"{string}"'), Color.STRING)
        if ENABLE_ANSI_COLORING
        else str(f'"{string}"')
    )


def CEnum(
    enumValue,
):
    return (
        color_text(enumValue.name, Color.ENUM_VALUE)
        if ENABLE_ANSI_COLORING
        else enumValue.name
    )


def render_line(instructions, op_names, i, prefix):
    """Render instruction `i` to a single display line.

    `prefix` is the indentation to put before the line; pass "" to get just
    the colored op-name + content with no leading whitespace (used when a
    line is being embedded inside another line, e.g. if/else's condition).
    """
    instr = instructions[i]
    op_name = op_names[i]

    pl = instr["payload"]
    payload_hex = pl.hex()

    if op_name == "comment:::op-code":
        payload_buf = Parser(instr["payload"])
        comment_length = payload_buf.readUint8()
        comment_string = payload_buf.readString(comment_length)
        line = (
            color_text(f"{prefix}// {comment_string}", Color.COMMENT)
            if ENABLE_ANSI_COLORING
            else f"{prefix}// {comment_string}"
        )

    elif op_name == "print::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()

        print_length = p.readUint8()
        text = p.readString(print_length)

        line = BUILD_LINE(
            prefix,
            "PRINT",
            f"{CRef(ref)} + {CStr(text)}",
        )

    elif op_name == "if/else::op-code":
        # if/else carries no payload of its own. Its condition is always its
        # first child (i+1); the condition's OWN span is the then-branch, and
        # whatever follows within if/else's own span (when its 'b' bit 0 is
        # clear) is the else-branch (Game.exe FUN_00431790; see hidden_indices/
        # else_start in parse_tfbscirpt_file). Fold the condition's rendered
        # line into this IF/ELSE line instead of printing it standalone.
        cond_idx = i + 1
        cond_line = render_line(instructions, op_names, cond_idx, "")

        line = BUILD_LINE(
            prefix,
            "IF/ELSE",
            f"({cond_line})",
        )

    elif op_name == "displace::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()  # the object being displaced
        combine_mode = CombineMode(p.readUint8())

        length = p.readRHS()  # magnitude of displacement
        heading = p.readRHS()  # yaw/heading
        pitch = p.readRHS()  # pitch

        line = BUILD_LINE(
            prefix,
            "DISPLACE",
            f"{CRef(ref)} {CEnum(combine_mode)} by length: {CRHS(length)}, heading: {CRHS(heading)}, pitch: {CRHS(pitch)}",
        )

    elif op_name == "check message::op-code":
        p = OpParser(instr["payload"])

        message_ref = p.readRef()  # the message being checked for

        if p.remaining() == 0:
            line = BUILD_LINE(
                prefix,
                "CHECK MESSAGE",
                f"{CRef(message_ref)}",
            )

        else:
            sender_ref = p.readRef()  # who must have sent it (context to match)
            rel_op = RelOp(
                p.readUint8()
            )  # comparison operator (name table @ 0x00602f98)
            value = p.readRHS()  # comparison Value

            line = BUILD_LINE(
                prefix,
                "CHECK MESSAGE",
                f"{CRef(message_ref)} from {CRef(sender_ref)} with value {CRelOp(rel_op)} {CRHS(value)}",
            )

    elif op_name == "send message::op-code":
        p = OpParser(instr["payload"])

        message_ref = p.readRef()  # which message to send
        recipient_ref = p.readRef()  # who to send it to
        rel_op = RelOp(p.readUint8())  # comparison operator (name table @ 0x00602f98)
        value = p.readRHS()  # the message's argument Value

        line = BUILD_LINE(
            prefix,
            "SEND MESSAGE",
            f"{CRef(message_ref)} to {CRef(recipient_ref)} with value {CRelOp(rel_op)} {CRHS(value)}",
        )

    elif op_name == "create variable::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CREATE VARIABLE",
            f"{CRef(ref)}",
        )

    elif op_name == "check fov::op-code":
        """
        Is there an actor from target_ref within arc_width°
        of angle_base, whose distance to me satisfies
        "distance range_relop range°",
        and if mode == consider_obstructions,
        i have a clear line of sight to them?
        """
        p = OpParser(instr["payload"])

        angle_base = p.readRHS()
        arc_width = p.readRHS()
        target_ref = p.readRef()
        range_relop = RelOp(p.readUint8())  # how angle compares to range
        range = p.readRHS()
        mode = CheckFOVMode(p.readUint8())

        line = BUILD_LINE(
            prefix,
            "CHECK FOV",
            f"{CRef(target_ref)} is within a {CRHS(arc_width)}° cone centered on heading {CRHS(angle_base)}, distance {CRelOp(range_relop)} {CRHS(range)}, {CEnum(mode)}",
        )

    # elif op_name == "use camera::op-code":
    #    p = OpParser(instr["payload"])

    #    camera_ref = p.readRef()

    #    line = BUILD_LINE(
    #        prefix,
    #        "USE CAMERA",
    #        f"{CRef(camera_ref)}",
    #    )

    elif op_name == "inc value::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "INCREMENT VALUE",
            f"{CRef(ref)}",
        )

    elif op_name == "dec value::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "DECREMENT VALUE",
            f"{CRef(ref)}",
        )

    elif op_name == "find variable::op-code":
        p = OpParser(instr["payload"])
        var_ref = p.readRef()
        owner_ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "FIND VARIABLE",
            f"{CRef(var_ref)} in {CRef(owner_ref)}",
        )

    elif op_name == "set behavior::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()  # the behavior to set

        line = BUILD_LINE(
            prefix,
            "SET BEHAVIOR",
            f"{CRef(ref)}",
        )

    elif op_name == "set reference::op-code":
        p = OpParser(instr["payload"])
        dest_ref = p.readRef()  # dest
        src_ref = p.readRef()  # src

        line = BUILD_LINE(
            prefix,
            "SET *REFERENCE",
            f"*{CRef(dest_ref)} to {CRef(src_ref)}",
        )

    elif op_name == "spawn actor::op-code":
        # TODO: THIS IS A STUB AND MAY NEEDS REVISION!

        p = OpParser(instr["payload"])
        actor_ref = p.readRef()  # actor / prototype to spawn
        context_ref = p.readRef()  # spawn owner/location context
        param_rhs = p.readRHS()  # spawn owner/location context

        line = BUILD_LINE(
            prefix,
            "SPAWN ACTOR",
            f"{CRef(actor_ref)}, owner: {CRef(context_ref)}, param: {CRHS(param_rhs)}",
        )

    elif op_name == "teleport to::op-code":
        p = OpParser(instr["payload"])
        target_ref = (
            p.readRef()
        )  # reference: teleport destination (e.g. an actor/placement)
        facing = Direction(p.readUint8())  # which way the actor faces after teleporting
        offset = p.readRHS()  # positional offset
        seconds_rhs = p.readRHS()  # transition time in seconds

        line = BUILD_LINE(
            prefix,
            "TELEPORT TO",
            f"{CRef(target_ref)} facing {CEnum(facing)} offset by {CRHS(offset)} over {CRHS(seconds_rhs)} seconds",
        )

    elif op_name == "play sound::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "PLAY SOUND",
            f"{CRef(ref)}",
        )

    elif op_name == "stop sound::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "STOP SOUND",
            f"{CRef(ref)}",
        )

    elif op_name == "cut-scene::op-code":
        p = OpParser(instr["payload"])

        cmd = p.readUint8()

        cmd_str = "UNK"
        if cmd == 3:
            cmd_str = "pause"
        elif cmd == 2:
            cmd_str = "resume"
        elif cmd == 1 or cmd == 0:
            cmd_str = "begin"

        line = BUILD_LINE(
            prefix,
            "CUT-SCENE",
            f"COMMAND: {CNum(cmd)} ({cmd_str}!?)",
        )

    elif op_name == "loop value::op-code":
        p = OpParser(instr["payload"])

        numLoops = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "LOOP VALUE",
            f"{CRHS(numLoops)}",
        )

    elif op_name == "play animation::op-code":
        p = OpParser(instr["payload"])
        anim_idx = p.readUint8()

        line = BUILD_LINE(
            prefix,
            "PLAY ANIMATION",
            f"{CNum(anim_idx)}",
        )

    elif op_name == "check value::op-code":
        p = OpParser(pl)

        ref = p.readRef()
        rel_op = RelOp(p.readUint8())
        rhs = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "CHECK VALUE",
            f"{CRef(ref)} {CRelOp(rel_op)} {CRHS(rhs)}",  # example: var == rhs
        )

    elif op_name == "set value::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        rhs = p.readRHS()
        line = BUILD_LINE(
            prefix,
            "SET VALUE",
            f"{CRef(ref)} to {CRHS(rhs)}",
        )

    elif op_name == "check reference::op-code":
        p = OpParser(instr["payload"])

        ref1 = p.readRef()
        ref2 = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CHECK REFERENCE",
            f"{CRef(ref1)} is reference to {CRef(ref2)}",
        )

    elif op_name == "turn to::op-code":
        p = OpParser(instr["payload"])

        target = p.readRHS()
        animationIdx = p.readUint8()

        line = BUILD_LINE(
            prefix,
            "TURN TO",
            f"{CRHS(target)} with animation {animationIdx}",
        )

    elif op_name == "run as player::op-code":
        p = OpParser(instr["payload"])

        actor_ref = (
            p.readRef()
        )  #  reference to the actor that becomes player-controlled

        line = BUILD_LINE(
            prefix,
            "RUN AS PLAYER",
            f"{CRef(actor_ref)}",
        )

    elif op_name == "reset::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()  #  reference to object to reset

        line = BUILD_LINE(
            prefix,
            "RESET",
            f"{CRef(ref)}",
        )

    elif op_name == "check membership::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        membershipTest = MembershipTest(p.readUint8())
        ref2 = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CHECK MEMBERSHIP",
            f"{CRef(ref2)} {membershipTest.symbol()} {CRef(ref)}",
        )

    elif op_name == "change membership::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        membershipCombiner = MembershipCombiner(p.readUint8())
        ref2 = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CHANGE MEMBERSHIP",
            f"{CRef(ref)}.{membershipCombiner.symbol()}({CRef(ref2)})",
        )

    elif op_name == "move to::op-code":
        p = OpParser(instr["payload"])

        destination = p.readRef()
        facing = Direction(p.readUint8())  # which way to face at the destination
        extra = p.readBytes(1)
        value = p.readRHS()  #  movement target/speed

        line = BUILD_LINE(
            prefix,
            "MOVE TO",
            f"{CRef(destination)}, facing {CEnum(facing)}, extra: {extra}, value: {CRHS(value)}",
        )

    elif op_name == "move from::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        extra = p.readBytes(1)
        value = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "MOVE FROM",
            f"{CRef(ref)}, extra: {extra}, value: {CRHS(value)}",
        )

    elif op_name == "for each::op-code":
        p = OpParser(instr["payload"])

        collection_ref = p.readRef()
        order = Direction(p.readUint8())  # iteration order (forward/backward/randomly)

        line = BUILD_LINE(
            prefix,
            "FOR EACH",
            f"in {CRef(collection_ref)} ({CEnum(order)})",
        )

    elif op_name == "use camera::op-code":
        p = OpParser(instr["payload"])

        cam_ref = p.readRef()
        trans_in_mode = p.readUint8()
        trans_in_duration = p.readFloat()
        trans_out_mode = p.readUint8()
        if trans_out_mode != 0:
             trans_out_duration = p.readFloat()

        line = BUILD_LINE(
            prefix,
            "USE CAMERA",
            f"{CRef(cam_ref)}, transition in {CNum(trans_in_mode)} for {CNum(trans_in_duration)} seconds, transition out {CNum(trans_out_mode)} for {CNum(trans_out_duration) if trans_out_mode != 0 else 'N/A'} seconds",
        )

    elif op_name == "find subset::op-code":
        p = OpParser(instr["payload"])

        collection_ref = p.readRef()  # the set to filter
        rel_op = RelOp(p.readUint8())  # filter comparator (name table @ 0x00602f98)
        value = p.readRHS()  # value each element is compared against

        line = BUILD_LINE(
            prefix,
            "FIND SUBSET",
            f"of {CRef(collection_ref)} where element {CRelOp(rel_op)} {CRHS(value)}",
        )

    elif op_name == "control::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()

        # TODO: figure out wtf this extra byte is for that is sometimes present in the payload (e.g. 0x00 in 967_ME_Sound_Ambient.ai, 0x01 in 702_ME_Hint.ai, 0x02 in 1069_RW_Haybale_Shed.ai, 0x03 in 556_RW_Balloon.ai)

        note = f", extra: {p.readRemaining().hex()}" if p.remaining() > 0 else ""

        line = BUILD_LINE(
            prefix,
            "CONTROL",
            f"{CRef(ref)}{note}",  # example: var == rhs
        )

    elif op_name == "slide value::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()
        target = p.readRHS()
        seconds = p.readRHS()
        
        if p.remaining() >= 8:
            ease_out = p.readRef()
            ease_in = p.readRef()
        else:
            # TODO: DO FOLLOWING
            print("THIS IS A WEIRD SPECIAL CASE THAT COMPLETELY BREAKS THE EXPECTED PAYLOAD FORMAT, NEEDS INVESTIGATION")
            ease_out = None
            ease_in = None

        line = BUILD_LINE(
            prefix,
            "SLIDE VALUE",
            f"{CRef(ref)} to {CRHS(target)} over {CRHS(seconds)} seconds, ease_out: {CRef(ease_out)}, ease_in: {CRef(ease_in)}",
        )

    elif op_name == "find subset::op-code":
        p = OpParser(instr["payload"])

        collection_ref = p.readRef()
        rel_op = RelOp(p.readUint8())
        value = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "FIND SUBSET",
            f"filterList({CRef(collection_ref)}, element_value {CRelOp(rel_op)} {CRHS(value)})",
        )

    elif op_name == "remove::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "REMOVE",
            f"{CRef(ref)}",
        )

    else:
        if ("[BEHAVIOR: " not in op_name) and op_name not in (
            "\n\n[PRESCRIPT]",
            "\n\n[STARTUP]",
            "\n\n[SHUTDOWN]",
        ):
            UNIMPLEMENTED_OPCODES.add(op_name)
        line = (
            f"{prefix}{op_name:<26} "
            f"branchPC: {instr['span']:<4} "  # descendant count: (a|b<<8|c<<16|d<<24)>>11
            f"Payload: {payload_hex}"
        )

    return line


# 556_RW_Balloon.ai
# 967_ME_Sound_Ambient.ai
# 702_ME_Hint.ai
# 1069_RW_Haybale_Shed.ai
def parse_tfbscirpt_file(filename):
    global TABLE1, TABLE2, TABLE3

    with open(filename, "rb") as f:
        buf = Parser(f.read())

        scriptNameLength = buf.readUint8()
        scriptName = buf.readString(scriptNameLength)

        unk_count = buf.readUint32()

        table1 = readStringTable(buf)  # opcode names
        table2 = readStringTable(buf) # global
        table3 = readStringTable(buf) # local

        behaviours = []
        for i in table3:
            if i["string"].split("::")[1] == "behavior":
                behaviours.append(i["string"])

        TABLE1, TABLE2, TABLE3 = table1, table2, table3


        instruction_count = buf.readUint32()
        instructions = []
        for _ in range(instruction_count):
            instruction = {
                "opcode": buf.readUint8(),
            }
            # Confirmed via Ghidra (Game.exe FUN_004349e0 + 15 opcode-handler
            # functions): the four bytes following the opcode pack into ONE
            # little-endian u32; bits 11-31 are a single 21-bit descendant span
            # -- NOT separate byte-wise then-count/else-count fields, that was
            # wrong. Bit 6 (0x40) = no handler bound for this instruction
            # (loader skips construction). Bit 7 (0x80) is a runtime-only
            # scratch flag, always 0 as authored on disk. Bit 8 (0x100) is
            # if/else's "no else branch" flag (see else_start below).
            packed = buf.readUint32()
            instruction["payload_size"] = buf.readUint8()
            instruction["payload"] = buf.readBytes(instruction["payload_size"])
            instruction["span"] = packed >> 11
            instruction["no_handler_bound"] = bool(packed & 0x40)
            instruction["else_absent"] = bool(packed & 0x100)
            instructions.append(instruction)

        def compute_layout(instrs):
            """Rebuild the pre-order instruction tree.

            Confirmed via Ghidra (Game.exe FUN_00431130, the shared "walk my span"
            driver reused by ~15 opcode handlers): every instruction carries ONE
            span -- the count of following instructions that are its descendants,
            flattened pre-order. There's no separate then/else split at this level;
            for if/else specifically, the then/else boundary is recovered below
            from its condition child's own span.
            """
            n = len(instrs)
            depth = [0] * n

            def consume(i, d):
                depth[i] = d
                j = i + 1
                end = j + instrs[i]["span"]
                while j < end:
                    j = consume(j, d + 1)
                return j

            idx = 0
            while idx < n:
                idx = consume(idx, 0)
            return depth

        depth = compute_layout(instructions)

        # Opcode 0xFF is a script SECTION marker (no handler, no payload). The engine
        # (Game.exe FUN_004349e0) names each by order of appearance: 1st=PRESCRIPT,
        # 2nd=STARTUP, 3rd=SHUTDOWN, 4th=main body, 5th+=further sections.
        # Resolved up front (rather than mutated inline during printing) so that
        # if/else's condition-child can be looked up and rendered out of order.
        SECTION_NAMES = {0: "PRESCRIPT", 1: "STARTUP", 2: "SHUTDOWN"}
        for i, b in enumerate(behaviours):
            SECTION_NAMES[3 + i] = (
                "BEHAVIOR: " + b
            )  # main body is section 3, then each behavior gets its own section
        op_names = []
        section_index = 0
        for instr in instructions:
            if instr["opcode"] == 0xFF:
                op_names.append(
                    "[%s]"
                    % SECTION_NAMES.get(
                        section_index, "UNKNOWN SECTION %d" % section_index
                    )
                )
                section_index += 1
            else:
                op_names.append(opcode_name(instr["opcode"], table1))

        # if/else's condition is always its first child (Game.exe FUN_00431790
        # unconditionally evaluates it). Fold that line into the IF/ELSE line
        # instead of also printing it standalone.
        hidden_indices = set()
        for i, instr in enumerate(instructions):
            if op_names[i] == "if/else::op-code":
                hidden_indices.add(i + 1)

        # The condition's own span becomes an extra (invisible) nesting level once
        # its line is folded into IF/ELSE's -- pull its descendants back up one
        # depth so the "then" body lines up directly under IF/ELSE, not under the
        # hidden condition.
        for h in hidden_indices:
            for k in range(h + 1, h + 1 + instructions[h]["span"]):
                depth[k] -= 1

        # Confirmed via Ghidra (Game.exe FUN_00431790, raw disassembly at
        # 0x004317d8 "TEST CH, 0x1"): if/else's own "else_absent" bit (mask
        # 0x100 on the packed dword) is clear when an else-branch is present.
        # That branch is whatever remains of if/else's span after the
        # condition's own (then-branch) span ends.
        else_start = set()
        for i, instr in enumerate(instructions):
            if op_names[i] != "if/else::op-code":
                continue
            cond_idx = i + 1
            has_else = not instr["else_absent"]
            if has_else:
                else_idx = cond_idx + 1 + instructions[cond_idx]["span"]
                if else_idx < i + 1 + instr["span"]:
                    else_start.add(else_idx)

        print("----- INSTRUCTIONS -----")

        for i, instr in enumerate(instructions):
            if i in hidden_indices:
                continue

            indent = depth[i]
            if i in else_start:
                print("   " * (indent - 1) + "ELSE:")

            prefix = "   " * indent
            line = render_line(instructions, op_names, i, prefix)
            print(line)



# 1046_Alex_RunAsPlayer.ai
# 556_RW_Balloon.ai
# 567_RW_Balloon_Spawner.ai
# 543_ME_Ring_Detector.ai
if __name__ == "__main__":

    parse_tfbscirpt_file("Levels/KingOfNY-unchanged/845_Marty_RunAsPlayer.ai")
    #for filename in glob.glob("Levels/KingOfNY/*.ai"):
    #    print(f"\n\nParsing {filename}...")
    #    parse_tfbscirpt_file(filename)

filtered_unimplemented_opcodes = {
    op for op in UNIMPLEMENTED_OPCODES if "::op-code" in op
}
if filtered_unimplemented_opcodes:
    print()
    print("----- UNIMPLEMENTED OPCODES -----")
    for op in sorted(filtered_unimplemented_opcodes):
        print(op)


"""
Still unimplemented opcodes:

- use camera::op-code

"""
