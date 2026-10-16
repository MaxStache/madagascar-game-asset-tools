"""Opcode implementations, one module per opcode.

Importing this package registers every implemented opcode in OPCODE_REGISTRY
(via the @opcode decorator); unimplemented opcodes fall back to the generic
Opcode class, which keeps the raw payload.
"""

from tfbscript.opcodes.base import (
    OPCODE_REGISTRY,
    InstructionFlags,
    Opcode,
    ParserContext,
)
from tfbscript.opcodes.block import BlockOpcode
from tfbscript.opcodes.enums import RelOp
from tfbscript.opcodes.op_behavior_implementation import OpBehaviorImplementation
from tfbscript.opcodes.op_change_membership import OpChangeMembership
from tfbscript.opcodes.op_check_fov import OpCheckFOV
from tfbscript.opcodes.op_check_membership import OpCheckMembership
from tfbscript.opcodes.op_check_message import OpCheckMessage
from tfbscript.opcodes.op_check_reference import OpCheckReference
from tfbscript.opcodes.op_check_value import OpCheckValue
from tfbscript.opcodes.op_comment import OpComment
from tfbscript.opcodes.op_control import OpControl
from tfbscript.opcodes.op_create_variable import OpCreateVariable
from tfbscript.opcodes.op_cut_scene import OpCutScene
from tfbscript.opcodes.op_dec_value import OpDecValue
from tfbscript.opcodes.op_displace import OpDisplace
from tfbscript.opcodes.op_find_subset import OpFindSubset
from tfbscript.opcodes.op_find_variable import OpFindVariable
from tfbscript.opcodes.op_for_each import OpForEach
from tfbscript.opcodes.op_if_else import OpIfElse
from tfbscript.opcodes.op_inc_value import OpIncValue
from tfbscript.opcodes.op_loop_value import OpLoopValue
from tfbscript.opcodes.op_move_from import OpMoveFrom
from tfbscript.opcodes.op_move_to import OpMoveTo
from tfbscript.opcodes.op_play_animation import OpPlayAnimation
from tfbscript.opcodes.op_play_sound import OpPlaySound
from tfbscript.opcodes.op_prescript import OpPrescript
from tfbscript.opcodes.op_print import OpPrint
from tfbscript.opcodes.op_remove import OpRemove
from tfbscript.opcodes.op_reset import OpReset
from tfbscript.opcodes.op_run_as_player import OpRunAsPlayer
from tfbscript.opcodes.op_send_message import OpSendMessage
from tfbscript.opcodes.op_set_behavior import OpSetBehavior
from tfbscript.opcodes.op_set_reference import OpSetReference
from tfbscript.opcodes.op_set_value import OpSetValue
from tfbscript.opcodes.op_shutdown import OpShutdown
from tfbscript.opcodes.op_slide_value import OpSlideValue
from tfbscript.opcodes.op_spawn_actor import OpSpawnActor
from tfbscript.opcodes.op_startup import OpStartup
from tfbscript.opcodes.op_stop_sound import OpStopSound
from tfbscript.opcodes.op_teleport_to import OpTeleportTo
from tfbscript.opcodes.op_turn_to import OpTurnTo
from tfbscript.opcodes.op_use_camera import OpUseCamera

__all__ = [
    "OPCODE_REGISTRY",
    "BlockOpcode",
    "InstructionFlags",
    "OpBehaviorImplementation",
    "OpChangeMembership",
    "OpCheckFOV",
    "OpCheckMembership",
    "OpCheckMessage",
    "OpCheckReference",
    "OpCheckValue",
    "OpComment",
    "OpControl",
    "OpCreateVariable",
    "OpCutScene",
    "OpDecValue",
    "OpDisplace",
    "OpFindSubset",
    "OpFindVariable",
    "OpForEach",
    "OpIfElse",
    "OpIncValue",
    "OpLoopValue",
    "OpMoveFrom",
    "OpMoveTo",
    "OpPlayAnimation",
    "OpPlaySound",
    "OpPrescript",
    "OpPrint",
    "OpRemove",
    "OpReset",
    "OpRunAsPlayer",
    "OpSendMessage",
    "OpSetBehavior",
    "OpSetReference",
    "OpSetValue",
    "OpShutdown",
    "OpSlideValue",
    "OpSpawnActor",
    "OpStartup",
    "OpStopSound",
    "OpTeleportTo",
    "OpTurnTo",
    "OpUseCamera",
    "Opcode",
    "ParserContext",
    "RelOp",
]
