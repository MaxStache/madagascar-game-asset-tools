from collections.abc import Callable

from tfbpseudo.arguments import (
    Argument,
    Choice,
    Comparison,
    Condition,
    Number,
    Ref,
    Text,
    Value,
    read_arguments,
    write_arguments,
)
from tfbpseudo.compiler import Compiler, opcode_handler
from tfbpseudo.decompiler import Decompiler, decompile_handler, make_statement
from tfbpseudo.errors import DecompileError
from tfbpseudo.nodes import FLOW_CONTINUE, Statement
from tfbscript import opcodes
from tfbscript.opcodes.base import Opcode
from tfbscript.opcodes.enums import (
    AnimationMapping,
    CamTransitionInMode,
    CamTransitionOutMode,
    CheckFOVMode,
    CombineMode,
    ControlRequirement,
    CutsceneCommand,
    MembershipCombiner,
    MembershipTest,
    SetDirection,
)

# Runs after the arguments are read, for the opcodes that record their payload
# shape in a private field: it is told how many arguments were actually there.
Finalize = Callable[[Opcode, int], None]
# Runs before an opcode is written out, to refuse the ones that cannot be.
Verify = Callable[[Opcode], None]


def declare(
    name: str,
    opcode_type: type[Opcode],
    op_name: str,
    arguments: list[Argument] | None = None,
    finalize: Finalize | None = None,
    verify: Verify | None = None,
) -> None:
    """Register `name` as a TfbPseudo method for `opcode_type`, in both
    directions, from one list of arguments."""
    spec = arguments or []

    optional_from = next(
        (i for i, argument in enumerate(spec) if argument.optional), len(spec)
    )
    for argument in spec[optional_from:]:
        if not argument.optional:
            raise ValueError(
                f"{name}: `{argument.name}` is required but follows an optional "
                + "argument, which no caller could leave out"
            )

    @opcode_handler(
        name,
        op_name=op_name,
        arg_count=optional_from,
        max_args=len(spec),
    )
    def compile_method(
        opcode_index: int, statement: Statement, compiler: Compiler
    ) -> Opcode:
        instruction = opcode_type(opcode_index)
        instruction.context = compiler.context

        read_arguments(statement.arguments, spec, instruction, compiler)

        if finalize is not None:
            finalize(instruction, len(statement.arguments))

        if statement.block is not None:
            compiler.compile_block_into(instruction, statement.block)

        return instruction

    @decompile_handler(opcode_type, method_name=name)
    def decompile_method(instruction: Opcode, decompiler: Decompiler) -> Statement:
        if verify is not None:
            verify(instruction)

        # A body is written whenever there is something to put in it -- which
        # includes a lone `flow`, since an opcode with no children can still
        # carry one and it would be lost otherwise.
        has_body = bool(instruction.children) or (
            instruction.flags.flow_control != FLOW_CONTINUE
        )

        return make_statement(
            name,
            write_arguments(spec, instruction, decompiler),
            block=decompiler.block_from_opcode(instruction) if has_body else None,
        )

    # The generated functions are registered, not called by name.
    del compile_method, decompile_method


# ----- checks -----

declare(
    "checkValue",
    opcodes.OpCheckValue,
    op_name="check value",
    arguments=[Condition("lhs", rel_op_name="rel_op", rhs_name="rhs")],
)

declare(
    "checkReference",
    opcodes.OpCheckReference,
    op_name="check reference",
    arguments=[Ref("ref1"), Ref("ref2")],
)

declare(
    "checkMembership",
    opcodes.OpCheckMembership,
    op_name="check membership",
    arguments=[
        Ref("ref1"),
        Choice("membershipTest", enum=MembershipTest),
        Ref("ref2"),
    ],
)


def _finalize_check_message(instruction: Opcode, argument_count: int) -> None:
    # The sender condition is only in the payload when it was written; the
    # engine decides that from the message's own declaration in the level hub,
    # which is not in this file, so the source says it by having the argument.
    instruction._is_extended = argument_count >= 2  # pyright: ignore[reportAttributeAccessIssue]


declare(
    "checkMessage",
    opcodes.OpCheckMessage,
    op_name="check message",
    arguments=[
        Ref("message_ref"),
        Condition(
            "sender_ref",
            rel_op_name="rel_op",
            rhs_name="value",
            optional=True,
            present_if=lambda op: op._is_extended,  # pyright: ignore[reportAttributeAccessIssue]
        ),
    ],
    finalize=_finalize_check_message,
)

declare(
    "checkFOV",
    opcodes.OpCheckFOV,
    op_name="check fov",
    arguments=[
        Value("angle_base"),
        Value("arc_width"),
        Ref("target_ref"),
        Comparison("range_relop"),
        Value("range"),
        Choice("mode", enum=CheckFOVMode),
    ],
)

declare(
    "findSubset",
    opcodes.OpFindSubset,
    op_name="find subset",
    arguments=[Condition("set_ref", rel_op_name="rel_op", rhs_name="rhs")],
)

declare(
    "findVariable",
    opcodes.OpFindVariable,
    op_name="find variable",
    arguments=[Ref("var_ref"), Ref("owner_ref")],
)


def _finalize_control(instruction: Opcode, argument_count: int) -> None:
    # The requirement byte is only in the payload for an actor target; writing
    # it is what says so (see OpControl._has_script_control).
    instruction._has_script_control = argument_count >= 2  # pyright: ignore[reportAttributeAccessIssue]


declare(
    "control",
    opcodes.OpControl,
    op_name="control",
    arguments=[
        Ref("target"),
        Choice(
            "script_control",
            enum=ControlRequirement,
            optional=True,
            default=ControlRequirement.Allow,
            present_if=lambda op: op._has_script_control,  # pyright: ignore[reportAttributeAccessIssue]
        ),
    ],
    finalize=_finalize_control,
)

# ----- loops -----

declare(
    "forEach",
    opcodes.OpForEach,
    op_name="for each",
    arguments=[Ref("set_ref"), Choice("set_direction", enum=SetDirection)],
)

declare(
    "loopValue",
    opcodes.OpLoopValue,
    op_name="loop value",
    arguments=[Value("loop_amount")],
)

# ----- values -----

declare(
    "setValue",
    opcodes.OpSetValue,
    op_name="set value",
    arguments=[Ref("lhs"), Value("rhs")],
)

declare(
    "incValue", opcodes.OpIncValue, op_name="inc value", arguments=[Ref("lhs")]
)

declare(
    "decValue", opcodes.OpDecValue, op_name="dec value", arguments=[Ref("lhs")]
)


def _verify_slide_value(instruction: Opcode) -> None:
    if instruction._trailing:  # pyright: ignore[reportAttributeAccessIssue]
        raise DecompileError(
            "slide value kept raw trailing bytes because its right-hand sides "
            + "could not be read back exactly, so its easing is unreliable"
        )


declare(
    "slideValue",
    opcodes.OpSlideValue,
    op_name="slide value",
    arguments=[
        Ref("lhs"),
        Value("target_value"),
        Value("interpolation_time"),
        Number("ease_out"),
        Number("ease_in"),
    ],
    verify=_verify_slide_value,
)

declare(
    "createVariable",
    opcodes.OpCreateVariable,
    op_name="create variable",
    arguments=[Ref("variable")],
)

declare(
    "setReference",
    opcodes.OpSetReference,
    op_name="set reference",
    arguments=[Ref("dest_ref"), Ref("src_ref")],
)

# ----- sets -----

declare(
    "changeMembership",
    opcodes.OpChangeMembership,
    op_name="change membership",
    arguments=[
        Ref("ref"),
        Choice("membershipCombiner", enum=MembershipCombiner),
        Ref("ref2"),
    ],
)

# ----- actors -----

declare(
    "setBehavior",
    opcodes.OpSetBehavior,
    op_name="set behavior",
    arguments=[Ref("behavior")],
)

declare(
    "spawnActor",
    opcodes.OpSpawnActor,
    op_name="spawn actor",
    arguments=[
        Ref("clone_ref"),
        Ref("at_ref"),
        Value("facing_rhs"),
        # Only some files carry this byte, so parse records its absence as None.
        Number("remaining", optional=True, default=None),
    ],
)

declare("remove", opcodes.OpRemove, op_name="remove", arguments=[Ref("target")])

declare("reset", opcodes.OpReset, op_name="reset", arguments=[Ref("target")])

declare(
    "runAsPlayer",
    opcodes.OpRunAsPlayer,
    op_name="run as player",
    arguments=[Ref("actor_ref")],
)

# ----- movement -----

declare(
    "moveTo",
    opcodes.OpMoveTo,
    op_name="move to",
    arguments=[
        Ref("target_ref"),
        Choice("set_direction", enum=SetDirection),
        Choice("with_anim", enum=AnimationMapping),
        Value("until_within"),
    ],
)

declare(
    "moveFrom",
    opcodes.OpMoveFrom,
    op_name="move from",
    arguments=[
        Ref("target_ref"),
        Choice("with_anim", enum=AnimationMapping),
        Value("until_beyond"),
    ],
)

declare(
    "teleportTo",
    opcodes.OpTeleportTo,
    op_name="teleport to",
    arguments=[
        Ref("target_ref"),
        Choice("set_direction", enum=SetDirection),
        Value("facing"),
        Value("duration"),
    ],
)

declare(
    "turnTo",
    opcodes.OpTurnTo,
    op_name="turn to",
    arguments=[Value("rhs"), Choice("animation", enum=AnimationMapping)],
)

declare(
    "displace",
    opcodes.OpDisplace,
    op_name="displace",
    arguments=[
        Ref("target"),
        Choice("combine_mode", enum=CombineMode),
        Value("length"),
        Value("heading"),
        Value("pitch"),
    ],
)

# ----- presentation -----

declare(
    "playAnimation",
    opcodes.OpPlayAnimation,
    op_name="play animation",
    arguments=[Choice("animation", enum=AnimationMapping)],
)

declare(
    "playSound", opcodes.OpPlaySound, op_name="play sound", arguments=[Ref("sound")]
)

declare(
    "stopSound", opcodes.OpStopSound, op_name="stop sound", arguments=[Ref("sound")]
)

declare(
    "useCamera",
    opcodes.OpUseCamera,
    op_name="use camera",
    arguments=[
        Ref("camera_ref"),
        Choice("trans_in_mode", enum=CamTransitionInMode),
        Number("trans_in_duration", is_float=True),
        Choice("trans_out_mode", enum=CamTransitionOutMode),
        # There is only a second duration when there is a transition to time.
        Number("trans_out_duration", is_float=True, optional=True, default=None),
    ],
)

declare(
    "cutScene",
    opcodes.OpCutScene,
    op_name="cut-scene",
    arguments=[Choice("cutscene_command", enum=CutsceneCommand)],
)

# ----- messages and debugging -----

declare(
    "sendMessage",
    opcodes.OpSendMessage,
    op_name="send message",
    arguments=[
        Ref("message_ref"),
        Ref("reciver_Ref"),
        Value("value"),
        # A byte send's execute never reads, but it is not always the same on
        # disk, so it is written out whenever it is not the usual value.
        Number("_rec8", optional=True, default=2),
    ],
)

declare(
    "print",
    opcodes.OpPrint,
    op_name="print",
    arguments=[Ref("target"), Text("content")],
)
