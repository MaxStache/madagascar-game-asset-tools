"""Enums shared by opcode payloads."""

from enum import IntEnum
from typing import override


# fmt: off
class RelOp(IntEnum):
    """Relational operator for OpCheckValue / OpFindSubset."""

    LessOrEq  = 0  # <=
    Eq        = 1  # ==
    GreatOrEq = 2  # >=
    Less      = 3  # <
    Great     = 4  # >
    NotEq     = 5  # !=

    def symbol(self) -> str:
        return ("<=", "==", ">=", "<", ">", "!=")[self.value]
    
    @override
    def __str__(self) -> str:
        return str(self.symbol())
    
class ControlRequirement(IntEnum):
    """u8 in OpControl payload that specifies how the control block is executed."""

    Suspend  = 0

    Allow = 1

    @override
    def __str__(self) -> str:
        return ("suspend script", "allow script")[self.value]
    
class CutsceneCommand(IntEnum):
    BeginAlt = 0 # start (allow skipping)    - in retail same effect as start because skipping is implmenented via tfbscript

    Begin    = 1 # start

    End      = 2 # end

    Pause  = 3 # pause

    @override
    def __str__(self) -> str:
        return {0: "start (allow skipping)", 1: "start", 2: "end", 3: "pause"}[self.value]
    
class SetDirection(IntEnum):
    """Direction for how to traverse a set"""

    forward = 0
    backward = 1
    randomly = 2

    @override
    def __str__(self) -> str:
        return ("forward", "backward", "randomly")[self.value]
    
class CombineMode(IntEnum):
    """Displacement combine mode for OpDisplace."""

    relative = 0
    absolute = 1
    local = 2

    @override
    def __str__(self) -> str:
        return ("relative", "absolute", "local")[self.value]
    
class MembershipTest(IntEnum):
    """Membership test for OpCheckMembership."""

    includes = 0  # set_a includes element_a
    excludes = 1  # set_a excludes element_a
    intersects_with = 2  # set_a intersects with_b (set_a has at least one element in common with set_b)
    includes_all = 3  # set_a all in set_b

    def symbol(self) -> str:
        # assumes format is "set_a <membership_test> element_a" or "set_a <membership_test> set_b"
        return ("in", "not in", "intersects with", "all in")[self.value]

class MembershipCombiner(IntEnum):
    """Membership combiner for OpChangeMembership."""

    include        = 0 # add a single thing?
    exclude        = 1 # remove a single thing?
    intersect_with = 2 
    be_replaced_by = 3  
    add            = 4  # concat sets together?
    exclude_all    = 5  # remove all elements that are also in set b?

    def symbol(self) -> str:
        # assumes format is "set_a.<membership_combiner>(element_a)" or "set_a.<membership_combiner>(set_b)"
        return ("include", "remove", "intersectWith", "replaceWith", "add", "removeAll")[self.value]

    @override
    def __str__(self) -> str:
        return ("include", "remove", "intersectWith", "replaceWith", "add", "removeAll")[self.value]

class AnimationMapping(IntEnum):
    """Animation mapping for ops that play an animation."""

    NO_ANIMATION = 0x00
    ambient = 0x01
    slowest_move = 0x02
    slow_move = 0x03
    fast_move = 0x04
    jump = 0x05
    fall = 0x06
    youch = 0x07
    slide = 0x08
    attack_1 = 0x09
    attack_2 = 0x0A
    tumble = 0x0B
    extra_1 = 0x0C
    extra_2 = 0x0D
    extra_3 = 0x0E
    extra_4 = 0x0F
    extra_5 = 0x10
    extra_6 = 0x11
    extra_7 = 0x12
    extra_8 = 0x13
    extra_9 = 0x14
    extra_10 = 0x15
    extra_11 = 0x16
    extra_12 = 0x17
    extra_13 = 0x18
    extra_14 = 0x19
    extra_15 = 0x1A
    extra_16 = 0x1B
    extra_17 = 0x1C
    extra_18 = 0x1D
    extra_19 = 0x1E
    extra_20 = 0x1F
    extra_21 = 0x20
    extra_22 = 0x21
    extra_23 = 0x22
    extra_24 = 0x23
    extra_25 = 0x24
    extra_26 = 0x25
    extra_27 = 0x26
    extra_28 = 0x27
    extra_29 = 0x28
    extra_30 = 0x29
    extra_31 = 0x2A
    extra_32 = 0x2B
    left_turn = 0x2C
    right_turn = 0x2D
    jump_land_slow = 0x2E
    jump_land_running = 0x2F
    jump_land_hard = 0x30
    stop_from_full_speed = 0x31
    stop_from_slow_speed = 0x32
    running_180_change = 0x33
    player_9 = 0x34
    player_10 = 0x35
    player_11 = 0x36
    player_12 = 0x37
    player_13 = 0x38
    player_14 = 0x39
    lean_left_slow = 0x3A
    lean_left_medium = 0x3B
    lean_left_fast = 0x3C
    lean_right_slow = 0x3D
    lean_right_medium = 0x3E
    lean_right_fast = 0x3F
    
    idle_cycle_1_A = 0x40
    idle_cycle_1_B = 0x41
    idle_cycle_1_C = 0x42
    idle_trans_1_to_2 = 0x43
    idle_trans_1_to_3 = 0x44
    idle_cycle_2_A = 0x45
    idle_cycle_2_B = 0x46
    idle_cycle_2_C = 0x47
    idle_trans_2_to_3 = 0x48
    idle_trans_2_to_1 = 0x49
    idle_cycle_3_A = 0x4A
    idle_cycle_3_B = 0x4B
    idle_cycle_3_C = 0x4C
    idle_trans_3_to_1 = 0x4D
    idle_trans_3_to_2 = 0x4E

    @override
    def __str__(self) -> str:
        return self.name.replace("_", " ")

class CheckFOVMode(IntEnum):
    """Mode for OpCheckFOV."""

    ignore_obstructions = 0

    consider_obstructions = 1

    @override
    def __str__(self) -> str:
        return ("ignore obstructions", "consider obstructions")[self.value]

class CamTransitionInMode(IntEnum):
    pan = 0
    fade_in = 1
    iris_in = 2

    @override
    def __str__(self) -> str:
        return ("pan", "fade in", "iris in")[self.value]


class CamTransitionOutMode(IntEnum):
    no_transition = 0
    fade_out = 1
    iris_out = 2

    @override
    def __str__(self) -> str:
        return ("no transition", "fade out", "iris out")[self.value]

# fmt: on
