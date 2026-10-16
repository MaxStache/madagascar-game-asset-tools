"""The opcode-arena size stored in the .ai header.

The 4-byte field after the magic string is not opaque: it is the size, in
dwords, of the arena the loader allocates for the script's instruction objects.
From ``TFBScript::read`` @ 004349e0 in Game.exe::

    FUN_00432920(&count);                    // the header dword
    DAT_0061f890 = FUN_00550170(count * 4);  // allocate the arena

``read`` then carves ``1 + instructionCount`` dwords off the front for the
instruction pointer array (plus its NULL terminator), and every instruction's
``instantiate`` (vtable +0x30) bumps ``DAT_0061f890`` by that opcode's object
size.  So::

    header = 1 + instructionCount + sum(objectSize(opcode) / 4)

Two accounting details, both recovered from the corpus rather than assumed:

* instructions with ``flags.no_handler`` (bit 6) set are **still counted** --
  the exporter reserves space for them even though the loader never constructs
  them;
* every 0xFF control-block marker costs 4 dwords, including the behavior
  implementations past the first three.

The per-opcode sizes below were solved as a linear system over the 577 shipped
scripts (one equation per file, one unknown per opcode) and reproduce the
stored header exactly for 575 of them.  The five that could be cross-checked
against Game.exe's ``parse`` return values all agree: set value 0x18, control
0x10, check message 0x1c, send message 0x1c, cut-scene 0x0c.
"""

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from tfbscript.opcodes.base import Opcode
    from tfbscript.script import ScriptFile

# Cost of one 0xFF control-block marker (prescript/startup/shutdown/behavior).
MARKER_DWORDS = 4

# opcode table name -> object size in dwords.
OPCODE_OBJECT_DWORDS: dict[str, int] = {
    "comment:": 0,
    "create variable": 0,
    "if/else": 2,
    "cut-scene": 3,
    "dec value": 3,
    "inc value": 3,
    "play animation": 3,
    "play sound": 3,
    "remove": 3,
    "reset": 3,
    "run as player": 3,
    "set behavior": 3,
    "stop sound": 3,
    "check reference": 4,
    "control": 4,
    "for each": 4,
    "print": 4,
    "set reference": 4,
    "change membership": 5,
    "check membership": 5,
    "loop value": 5,
    "turn to": 5,
    "check value": 6,
    "find subset": 6,
    "find variable": 6,
    "set value": 6,
    "use camera": 6,
    "check message": 7,
    "move from": 7,
    "move to": 7,
    "send message": 7,
    "spawn actor": 8,
    "teleport to": 9,
    "check fov": 12,
    "displace": 12,
    "slide value": 17,
}


def _walk(ops: "list[Opcode]") -> "Iterator[Opcode]":
    for op in ops:
        yield op
        yield from _walk(op.children)


def _marker_classes() -> tuple[type, ...]:
    from tfbscript.opcodes.op_behavior_implementation import OpBehaviorImplementation
    from tfbscript.opcodes.op_prescript import OpPrescript
    from tfbscript.opcodes.op_shutdown import OpShutdown
    from tfbscript.opcodes.op_startup import OpStartup

    return (OpPrescript, OpStartup, OpShutdown, OpBehaviorImplementation)


def arena_dwords(script: "ScriptFile") -> int | None:
    """The header dword this script needs, or None if it can't be computed.

    Returns None when the script contains an opcode with no known object size
    (an unrecognised name, or the generic `Opcode` fallback) -- callers should
    fall back to the value the file was read with rather than guess.
    """
    from tfbscript.opcodes.base import OPCODE_REGISTRY

    name_of = {cls: name for name, cls in OPCODE_REGISTRY.items()}
    markers = _marker_classes()

    total = 1  # the pointer array's NULL terminator
    for op in _walk(script.instructions):
        total += 1  # this instruction's slot in the pointer array
        if isinstance(op, markers):
            total += MARKER_DWORDS
            continue
        size = OPCODE_OBJECT_DWORDS.get(name_of.get(type(op), ""))
        if size is None:
            return None
        total += size
    return total
