from tfbscript import ScriptFile
from tfbscript import open_editor
from tfbscript.opcodes import OpPrescript, OpStartup, OpShutdown
from tfbscript.opcodes.enums import CombineMode, MembershipCombiner
from tfbscript.opcodes.op_behavior_implementation import OpBehaviorImplementation
from tfbscript.opcodes.op_change_membership import OpChangeMembership
from tfbscript.opcodes.op_check_value import OpCheckValue
from tfbscript.opcodes.op_comment import OpComment
from tfbscript.opcodes.op_displace import OpDisplace
from tfbscript.opcodes.op_set_behavior import OpSetBehavior
from tfbscript.opcodes.op_set_reference import OpSetReference
from tfbscript.opcodes.op_spawn_actor import OpSpawnActor
from tfbscript.reference import BuiltinType, Reference
from tfbscript.rhs import Rhs
from tfbscript.string_table import StringTableEntry

script = ScriptFile()

LOCAL_REFS = [
    StringTableEntry(string="Idle::behavior"),
    StringTableEntry(string="Action 1::behavior"),
    StringTableEntry(string="Action 2::behavior"),
    StringTableEntry(string="Action 3::behavior"),
    StringTableEntry(string="Action 4::behavior"),
    StringTableEntry(string="myController::user::controller"),
]

script.local_refs.entries.extend(LOCAL_REFS)

GLOBAL_REFS = [
    StringTableEntry(string="Projectile::actor"),
    StringTableEntry(string="Players::set::actor"),
    StringTableEntry(string="controller 1::controller"),
]

script.global_refs.entries.extend(GLOBAL_REFS)

OPCODE_TABLE = [
    StringTableEntry(string="check value::op-code"),
    StringTableEntry(string="set behavior::op-code"),
    StringTableEntry(string="spawn actor::op-code"),
    StringTableEntry(string="displace::op-code"),
    StringTableEntry(string="change membership::op-code"),
    StringTableEntry(string="comment::op-code"),
    StringTableEntry(string="set reference::op-code"),
]

script.opcode_table.entries.extend(OPCODE_TABLE)

i_prescript = OpPrescript(0xFF)
i_prescript.flags.flow_control = 1  # Flow CONTINUE
script.instructions.append(i_prescript)

i_startup = OpStartup(0xFF)

i_changeMembership = OpChangeMembership(0x05)
i_changeMembership.ref = Reference.createSimple_global(script.global_refs, slot=1)
i_changeMembership.membershipCombiner = MembershipCombiner.include
i_changeMembership.ref2 = Reference.createSimple_builtin(BuiltinType.SELF)
i_startup.children.append(i_changeMembership)

i_comment = OpComment(0x05)
i_comment.content = "Player 1 has controller 1"
i_startup.children.append(i_comment)

i_setRef = OpSetReference(0x06)
i_setRef.dest_ref = Reference.createSimple_local(script.local_refs, slot=5)
i_setRef.src_ref = Reference.createSimple_global(script.global_refs, slot=2)
i_startup.children.append(i_setRef)

i_setBehavIdle = OpSetBehavior(0x01)
i_setBehavIdle.behavior = Reference.createSimple_local(script.local_refs, slot=0)
i_startup.children.append(i_setBehavIdle)

i_prescript.children.append(i_startup)

i_shutdown = OpShutdown(0xFF)
i_prescript.children.append(i_shutdown)

# region behav idle

i_behv_idle = OpBehaviorImplementation(0xFF)
i_behv_idle.behavior_entry = script.local_refs.entries[0]
script.instructions.append(i_behv_idle)

# region CONTROLLER CHECK1
# ---- CONTROLLER CHECK1 ---
i_behv_idle_check_controller_1 = OpCheckValue(0x00)
i_behv_idle_check_controller_1.lhs = Reference.createSimple_local(
    script.local_refs, slot=5
)
i_behv_idle_check_controller_1.flags.flow_control = 1  # Flow CONTINUE

i_behv_idle_check_controller_1.rhs = Rhs()
i_behv_idle_check_controller_1.rhs.kind = "int"
i_behv_idle_check_controller_1.rhs.value = 0x01

i_behv_idle_check_controller_1.lhs.member = 0x01
i_behv_idle.children.append(i_behv_idle_check_controller_1)
# -----

# ---- CONTROLLER CHECK1 - CHILDREN ---
i_behv_idle_check_controller_1_set_behav = OpSetBehavior(0x01)
i_behv_idle_check_controller_1_set_behav.behavior = Reference.createSimple_local(script.local_refs, slot=1)
i_behv_idle_check_controller_1.children.append(i_behv_idle_check_controller_1_set_behav)
# ----- 
# endregion

# region CONTROLLER CHECK2
# ---- CONTROLLER CHECK2 ---
i_behv_idle_check_controller_1 = OpCheckValue(0x00)
i_behv_idle_check_controller_1.lhs = Reference.createSimple_local(
    script.local_refs, slot=5
)
i_behv_idle_check_controller_1.flags.flow_control = 1  # Flow CONTINUE

i_behv_idle_check_controller_1.rhs = Rhs()
i_behv_idle_check_controller_1.rhs.kind = "int"
i_behv_idle_check_controller_1.rhs.value = 0x01

i_behv_idle_check_controller_1.lhs.member = 0x02
i_behv_idle.children.append(i_behv_idle_check_controller_1)
# -----

# ---- CONTROLLER CHECK2 - CHILDREN ---
i_behv_idle_check_controller_1_set_behav = OpSetBehavior(0x01)
i_behv_idle_check_controller_1_set_behav.behavior = Reference.createSimple_local(script.local_refs, slot=2)
i_behv_idle_check_controller_1.children.append(i_behv_idle_check_controller_1_set_behav)

i_spawn_projectile = OpSpawnActor(0x02)
i_spawn_projectile.clone_ref = Reference.createSimple_global(script.global_refs, slot=0)
i_spawn_projectile.at_ref = Reference.createSimple_builtin(BuiltinType.SELF)

i_spawn_projectile.facing_rhs = Rhs()
i_spawn_projectile.facing_rhs.kind = "reference"
i_spawn_projectile.facing_rhs.value = Reference.createSimple_builtin(BuiltinType.SELF)

i_behv_idle_check_controller_1.children.append(i_spawn_projectile)

i_displace_projectile = OpDisplace(0x03)
i_displace_projectile.target = Reference.createSimple_global(script.global_refs, slot=0)
i_displace_projectile.combine_mode = CombineMode.relative

i_displace_projectile.length = Rhs()
i_displace_projectile.length.kind = "float"
i_displace_projectile.length.value = 20

i_displace_projectile.heading = Rhs()
i_displace_projectile.heading.kind = "reference"
disp_projectile_facing_ref = Reference.createSimple_builtin(BuiltinType.SELF)
i_displace_projectile.heading.value = disp_projectile_facing_ref

i_displace_projectile.pitch = Rhs()
i_displace_projectile.pitch.kind = "float"
i_displace_projectile.pitch.value = 60

i_spawn_projectile.children.append(i_displace_projectile)
# ----- 
# endregion

# region CONTROLLER CHECK3
# ---- CONTROLLER CHECK3 ---
i_behv_idle_check_controller_1 = OpCheckValue(0x00)
i_behv_idle_check_controller_1.lhs = Reference.createSimple_local(
    script.local_refs, slot=5
)
i_behv_idle_check_controller_1.flags.flow_control = 1  # Flow CONTINUE

i_behv_idle_check_controller_1.rhs = Rhs()
i_behv_idle_check_controller_1.rhs.kind = "int"
i_behv_idle_check_controller_1.rhs.value = 0x01

i_behv_idle_check_controller_1.lhs.member = 0x03
i_behv_idle.children.append(i_behv_idle_check_controller_1)
# -----

# ---- CONTROLLER CHECK3 - CHILDREN ---
i_behv_idle_check_controller_1_set_behav = OpSetBehavior(0x01)
i_behv_idle_check_controller_1_set_behav.behavior = Reference.createSimple_local(script.local_refs, slot=3)
i_behv_idle_check_controller_1.children.append(i_behv_idle_check_controller_1_set_behav)
# ----- 
# endregion

# region CONTROLLER CHECK4
# ---- CONTROLLER CHECK4 ---
i_behv_idle_check_controller_1 = OpCheckValue(0x00)
i_behv_idle_check_controller_1.lhs = Reference.createSimple_local(
    script.local_refs, slot=5
)
i_behv_idle_check_controller_1.flags.flow_control = 1  # Flow CONTINUE

i_behv_idle_check_controller_1.rhs = Rhs()
i_behv_idle_check_controller_1.rhs.kind = "int"
i_behv_idle_check_controller_1.rhs.value = 0x01

i_behv_idle_check_controller_1.lhs.member = 0x04
i_behv_idle.children.append(i_behv_idle_check_controller_1)
# -----

# ---- CONTROLLER CHECK4 - CHILDREN ---
i_behv_idle_check_controller_1_set_behav = OpSetBehavior(0x01)
i_behv_idle_check_controller_1_set_behav.behavior = Reference.createSimple_local(script.local_refs, slot=4)
i_behv_idle_check_controller_1.children.append(i_behv_idle_check_controller_1_set_behav)
# ----- 
# endregion


# endregion

# region Action 1
i_behv_act1 = OpBehaviorImplementation(0xFF)
i_behv_act1.behavior_entry = script.local_refs.entries[1]
i_behv_act1.flags.flow_control = 0  # Flow END
script.instructions.append(i_behv_act1)

behv_act1_i_setbehav = OpSetBehavior(0x01)
behv_act1_i_setbehav.behavior = Reference.createSimple_local(script.local_refs, slot=0)

i_behv_act1.children.append(behv_act1_i_setbehav)
# endregion

# region Action 2
i_behv_act2 = OpBehaviorImplementation(0xFF)
i_behv_act2.behavior_entry = script.local_refs.entries[2]
i_behv_act2.flags.flow_control = 0  # Flow END
script.instructions.append(i_behv_act2)

behv_act2_i_setbehav = OpSetBehavior(0x01)
behv_act2_i_setbehav.behavior = Reference.createSimple_local(script.local_refs, slot=0)

i_behv_act2.children.append(behv_act2_i_setbehav)
# endregion

# region Action 3
i_behv_act3 = OpBehaviorImplementation(0xFF)
i_behv_act3.behavior_entry = script.local_refs.entries[3]
i_behv_act3.flags.flow_control = 0  # Flow END
script.instructions.append(i_behv_act3)

behv_act3_i_setbehav = OpSetBehavior(0x01)
behv_act3_i_setbehav.behavior = Reference.createSimple_local(script.local_refs, slot=0)

i_behv_act3.children.append(behv_act3_i_setbehav)
# endregion

# region Action 4
i_behv_act4 = OpBehaviorImplementation(0xFF)
i_behv_act4.behavior_entry = script.local_refs.entries[4]
i_behv_act4.flags.flow_control = 0  # Flow END
script.instructions.append(i_behv_act4)

behv_act4_i_setbehav = OpSetBehavior(0x01)
behv_act4_i_setbehav.behavior = Reference.createSimple_local(script.local_refs, slot=0)

i_behv_act4.children.append(behv_act4_i_setbehav)
# endregion

open_editor(script)
