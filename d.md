 ▐▛███▜▌   Claude Code v2.1.217
▝▜█████▛▘  Sonnet 5 · Claude Pro
  ▘▘ ▝▝    ~\Projects\madagascar-game-asset-tools


❯ figure out the payloud format of the spawn actor::op-code                     

  Searched for 8 patterns, read 1 file (ctrl+o to expand)

● Skill(tfbscript-type-fields)
  ⎿  Successfully loaded skill

  Read 1 file (ctrl+o to expand)

● listMcpResources(List all MCP resources)
  ⎿  [
       {
         "uri": "ui://widget/keyword-research-v6.html",
     … +335 lines (ctrl+o to expand)

  Searched for 3 patterns, read 2 files (ctrl+o to expand)
  ⎿  Interrupted · What should Claude do instead?

❯ you now have mcp acces, try again                                             

  Searched for 7 patterns, read 1 file, listed 1 directory, called ghidra 16 times (ctrl+o to expand)
● Let me write a quick diagnostic script that parses every .ai file and checks
  whether the spawn-actor payload is fully consumed by the current 3-field
  model.

  Made 7 scratchpad edits +225 -20, searched for 1 pattern, read 3 files, called ghidra 8 times, ran 8 shell commands (ctrl+o to expand)

● Update(tfbscript_wip.py)
  ⎿  Added 13 lines, removed 4 lines
      392          )
      393  
      394      elif op_name == "spawn actor::op-code":
      395 -        # TODO: THIS IS A STUB AND MAY NEEDS REVISION!        
      396 -                                                              
      395          p = OpParser(instr["payload"])
      396          actor_ref = p.readRef()  # actor / prototype to spawn
      397          context_ref = p.readRef()  # spawn owner/location cont
           ext
      400 -        param_rhs = p.readRHS()  # spawn owner/location contex
          -t                                                             
      398 +        param_rhs = p.readRHS()  # spawn param value          
      399  
      400 +        # Trailing byte: only emitted when actor_ref resolves 
          +to an ::actor                                                 
      401 +        # prototype (never for ::sprite / ::particle / ::rumbl
          +e). payload_size                                              
      402 +        # already bakes in that decision, so remaining() is a 
          +lossless proxy --                                             
      403 +        # verified byte-exact (0 mismatches) against all 898 s
          +pawn actor                                                    
      404 +        # instances in the shipped corpus.                    
      405 +        actor_flag = p.readUint8() if p.remaining() > 0 else N
          +one                                                           
      406 +                                                              
      407 +        content = f"{CRef(actor_ref)}, owner: {CRef(context_re
          +f)}, param: {CRHS(param_rhs)}"                                
      408 +        if actor_flag is not None:                            
      409 +            content += f", flag: {CNum(actor_flag)}"          
      410 +                                                              
      411          line = BUILD_LINE(
      412              prefix,
      413              "SPAWN ACTOR",
      405 -            f"{CRef(actor_ref)}, owner: {CRef(context_ref)}, p
          -aram: {CRHS(param_rhs)}",                                     
      414 +            content,                                          
      415          )
      416  
      417      elif op_name == "teleport to::op-code":

  Ran 1 shell command (ctrl+o to expand)

❯ what is the actor_flag                                                        

  Called ghidra 6 times, ran 1 shell command (ctrl+o to expand)

● Good question — I dug into this with Ghidra rather than guessing. Here's what
  the trailing byte actually is:

  It's a boolean flag that's conditionally present — not a fixed 4th field.

  The current stub in tfbscript_wip.py reads 3 fields (actor_ref, context_ref,
  param_rhs) and stops. But checking every real spawn actor::op-code instance in
  the shipped corpus (898 occurrences across 330 .ai files) against the file's
  own payload_size byte showed 259 of them (~29%) have exactly 1 leftover byte
  that the 3-field parse never consumes.

  I found the rule with 100% correlation, zero exceptions across all 898
  instances:

  ▎ The byte is present if and only if actor_ref (the thing being spawned) 
  ▎ resolves to an ::actor-type prototype. It's never present when spawning a 
  ▎ ::sprite, ::particle, or ::rumble.

  That lines up with the runtime code (FUN_00431ad0, the executor for this op):
  it reads the byte, inverts it to a bool, and passes it as the 3rd argument to
  a vtable call that performs the actual instantiation — Spawn(owner_ref, 
  param_value, flag). Sprites/particles are simple render-only objects that
  don't take this extra argument; actors (which carry AI/physics/activation
  state) do.

  What the flag itself controls, I couldn't pin down with certainty from static
  analysis — following the call chain further (FUN_00431be0, the post-spawn init
  step) shows it feeding into activation/positioning setup on the newly created
  instance, consistent with something like "activate immediately" or a similar
  actor-only spawn behavior toggle, but I don't have a hard source for its exact
  name. Observed values in the corpus are only 0 or 1, roughly 50/50, with no
  clean correlation to context_ref being self vs. something else — so it's
  genuinely level-author-controlled per spawn call, not implied by other fields.

  I've already fixed the stub in tfbscript_wip.py to read this conditionally
  (mirroring the remaining()-as-proxy pattern already used elsewhere in that
  file for RHS parsing) and print it as flag: N when present. Full corpus
  re-check confirms every spawn-actor instance now consumes its payload exactly,
  with zero leftover bytes.

✻ Baked for 13m 1s

❯ continue searhcing for what it does                                           

  Called ghidra 11 times (ctrl+o to expand)
● I pushed further using the actual disassembly (not just the decompiler's
  guess) and RTTI-derived class names in the binary. Here's the more complete
  picture of what the flag does:

  The exact call, confirmed byte-for-byte from FUN_00431ad0's assembly:

  context.vtable[0x44](prototype_or_fallback, param_value, flag_bool)

  Concretely:
  - context = the resolved context_ref (owner) object — a virtual/polymorphic
  call, dispatched through whatever object "self"/the owner actually is.
  - Arg 1 = the resolved actor_ref (the prototype), or the prototype itself as
  fallback if context resolution failed.
  - Arg 2 = the evaluated param_rhs value.
  - Arg 3 = our flag byte, but inverted: SETZ means the byte is compared to 0
  first, so flag_byte == 0 → true is passed, flag_byte == 1 → false is passed.

  So in the payload, 0 means "flag argument is true" and 1 means "flag argument
  is false" — an inverted boolean, which is a common pattern for something like
  a bool suppress_x or bool skip_y parameter (default-false behavior gets the 0
  byte).

  It's used a second time, too. The object returned by that call (the
  newly-created instance) then gets a follow-up setup call in FUN_00431be0:
  newInstance.vtable[0x78](param_value, flag_bool)   // same flag, reused
  newInstance.vtable[0x8](1)                          // unconditional
  FUN_0043ca30(newInstance, FLT_MAX)                  // resets some field to
  "infinite"
  newInstance.vtable[0x50](outer_context, 1)          // links back to spawning
  context
  So the flag isn't just "how to create it" — it's threaded into post-creation
  setup too, consistent with something like an activation/initialization toggle
  rather than a one-off creation parameter.

  Where I hit a hard wall: identifying the concrete class behind
  context.vtable[0x44] to name the flag precisely. I tried reading it off the
  ::actor instance vtable (found via the same method as the type-fields skill —
  0x005cd5e8/0x005cd728, both anchored to the confirmed actor getName stub).
  Slot 0x44 there resolves to FUN_00429d60, but its disassembly is a
  6-instruction stdcall accessor (RET 0x4, one stack arg) — incompatible with
  the 3-arg thiscall virtual dispatch actually used at the call site. That means
  "self"/context isn't dispatching through that vtable at all; resolveVar's
  "self" case pulls from a separate global pair (DAT_00621f14/DAT_00621f18), so
  the concrete runtime type is owner-script-dependent (could be an actor,
  sprite, etc., all sharing a common polymorphic base) and isn't pinned down by
  static address arithmetic. Ghidra does have OpSpawnActor/OpCheckValue/etc. as
  recognized namespaces (from earlier work on this project), but no Actor-class
  namespace and no member functions assigned yet, so there's no shortcut there
  either.

  Resolving it further would need live tracing (breakpoint the game at that
  indirect call and read the actual vtable pointer) — pure static analysis can't
  determine which concrete override runs behind a virtual call whose receiver
  type varies by which entity the script is attached to. If you want, I can try
  setting this up via the Ghidra debugger tools
  (debugger_attach/debugger_set_breakpoint) if you have the game runnable, which
  would nail the exact function and let me name the flag with certainty.

✻ Baked for 3m 43s

※ recap: Fixing tfbscript_wip.py's spawn-actor payload parser using Ghidra; confirmed a conditional trailing flag byte tied to actor-type spawns and applied the fix. Next: optionally attach the Ghidra debugger to pin down exactly what that flag controls. (disable recaps in /config)

❯ Find the serialized file, rwsector extension format of TFB Material Plugin    

  Searched for 1 pattern, called ghidra 48 times (ctrl+o to expand)

❯ example for a material with uv transform effect 00000000  0D 00 0F 0F 03 02   
  00 00  ........                                                               
  00000008  03 00 00 00 02 00 00 00  ........                                   
  00000010  05 00 00 00 0A D7 23 3C  ......#<                                   
  00000018  0A D7 23 3C 0A D7 A3 3C  ..#<...<                                   
  00000020  CD CC 4C 3D CD CC 4C 3D  ..L=..L=                                   
  00000028  CD CC CC 3D 52 B8 5E 3F  ...=R.^?                                   
  00000030  00 00 00 3F 00 00 00 00  ...?....                                   
  00000038  00 00 00 00 00 00 00 00  ........                                   
  00000040  00                       .                                          
   axampe without any materal effects: 00000000  0D 00 0F 0F 01 02 00 00        
  ........                                                                      
  00000008  03 00 00 00 02 00 00 00  ........                                   
  00000010  05 00 00 00 00 00 00 00  ........                                   
  00000018  00 00 00 00 00 00 00 00  ........                                   
  00000020  00                       .                                          

● That's a great, concrete data point — let me verify it directly against the
  actual read function in Ghidra rather than guessing at the byte layout.

  Called ghidra (ctrl+o to expand)

❯ another one with uv trasform 00000000  0D 00 0F 0F 03 02 00 00  ........      
  00000008  03 00 00 00 02 00 00 00  ........                                   
  00000010  05 00 00 00 0A D7 23 3C  ......#<                                   
  00000018  0A D7 23 3C 0A D7 A3 3C  ..#<...<                                   
  00000020  CD CC 4C 3D CD CC 4C 3D  ..L=..L=                                   
  00000028  CD CC CC 3D 52 B8 5E 3F  ...=R.^?                                   
  00000030  00 00 00 3F 00 00 00 00  ...?....                                   
  00000038  00 00 00 00 00 00 00 00  ........                                   
  00000040  00                       .                                          
  ⎿  Interrupted · What should Claude do instead?

❯ continue                                                                      
  ⎿  Interrupted · What should Claude do instead?

❯ /model 
  ⎿  Kept model as Sonnet 5

❯ /model                                                                          ⎿  Set model to Opus 4.8 and saved as your default for new sessions
          .claude\settings.json pins Sonnet 5 — that applies on restart

❯ continue                                                                      

● The version dword confirms it — 0D 00 0F 0F = 0x0F0F000D, which is exactly the
  newest case in the FUN_0045f7d0 dispatcher, routing to FUN_0045ebf0. Let me
  trace the full reader chain to map every byte.

  Called ghidra 6 times (ctrl+o to expand)

● Both examples decode exactly against the reader chain — every byte accounted
  for, zero remainder. Let me confirm a couple of helper semantics (int vs float
  reads, and the +0x280 field) before writing it up.

  Called ghidra 3 times (ctrl+o to expand)

● Both examples decode byte-perfect against the reader chain, with zero bytes
  left over. Here's the full format.

  TFB Material Plugin — serialized (RW stream) format

  Registration (FUN_0045f920): this is a RenderWare material plugin extension,
  plugin/chunk ID 0x800000F6. It attaches a 732-byte (0x2DC) block to every
  RwMaterial (DAT_006068cc is that block's offset into the material), and
  registers stream callbacks: read = FUN_0045f7d0, get-size = FUN_0045e1a0. On
  disk it lives as a sub-chunk inside the material's rwID_EXTENSION block, like
  any RW plugin.

  Dispatch (FUN_0045f7d0): the first dword is a format version, and it selects
  the reader:

  ┌──────────────┬──────────────┬─────────────────────────────────────────┐
  │   version    │    reader    │                  notes                  │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ < 0x0F0F0008 │ FUN_0045f320 │ legacy layout (4×0x98-byte blocks @ +8) │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F0008   │ FUN_0045f4a0 │ legacy                                  │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F0009   │ FUN_0045f630 │ legacy                                  │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F000A   │ FUN_0045e8d0 │ modern base                             │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F000B   │ FUN_0045e9e0 │ base + sub-array                        │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F000C   │ FUN_0045eaf0 │ + two optional arrays                   │
  ├──────────────┼──────────────┼─────────────────────────────────────────┤
  │ 0x0F0F000D   │ FUN_0045ebf0 │ current (+ 1 trailing byte)             │
  └──────────────┴──────────────┴─────────────────────────────────────────┘

  Your two samples are both version 0x0F0F000D. The modern readers are strictly
  additive (ebf0→eaf0→e9e0→e8d0), so the current layout is:

  Layout (version 0x0F0F000D)

  ┌───────────────────┬──────┬────────┬──────────┬─────────────────────────┐
  │                   │      │   →    │          │                         │
  │    stream off     │ size │ struct │  field   │         meaning         │
  │                   │      │   off  │          │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x00              │ 4    │ +0x000 │ version  │ 0x0F0F000D              │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x04              │ 4    │ +0x004 │ flags    │ bitfield (below)        │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │                   │      │        │ blend    │ enum 0–4, expands to    │
  │ 0x08              │ 4    │ +0x280 │ preset   │ src/dst blend via       │
  │                   │      │        │          │ FUN_0045e230            │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x0C              │ 4    │ +0x28C │ int      │ render-state (raw)      │
  │                   │      │        │ field    │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x10              │ 4    │ +0x290 │ int      │ render-state (raw)      │
  │                   │      │        │ field    │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ — the next block  │      │        │          │                         │
  │ exists only if    │      │        │          │                         │
  │ flags & 0x0002 —  │      │        │          │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x14              │ 4    │ +0x2A8 │ float[0] │ UV-transform effect     │
  │                   │      │        │          │ params                  │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x18              │ 4    │ +0x2AC │ float[1] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x1C              │ 4    │ +0x2B0 │ float[2] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x20              │ 4    │ +0x2B4 │ float[3] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x24              │ 4    │ +0x2B8 │ float[4] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x28              │ 4    │ +0x2BC │ float[5] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ 0x2C              │ 4    │ +0x2C0 │ float[6] │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │                   │      │        │          │ (then an animated       │
  │ 0x30              │ 4    │ +0x2C4 │ float[7] │ texture is allocated:   │
  │                   │      │        │          │ FUN_004db700→+0x2A4)    │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ — resume          │      │        │          │                         │
  │ unconditionally — │      │        │          │                         │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │                   │      │        │          │ count of 0x3C-byte      │
  │ next              │ 4    │ +0x2C8 │ N        │ sub-records; N of them  │
  │                   │      │        │          │ follow (FUN_0045abb0)   │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │                   │      │        │          │ if >0, that many        │
  │ next              │ 4    │ —      │ countA   │ 0x50-byte records →     │
  │                   │      │        │          │ +0x2D0                  │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │                   │      │        │          │ if >0, that many        │
  │ next              │ 4    │ —      │ countB   │ 0x50-byte records →     │
  │                   │      │        │          │ +0x2D4                  │
  ├───────────────────┼──────┼────────┼──────────┼─────────────────────────┤
  │ next              │ 1    │ +0x2D8 │ trailing │ added in version …000D  │
  │                   │      │        │  byte    │                         │
  └───────────────────┴──────┴────────┴──────────┴─────────────────────────┘

  flags bits (+0x04): 0x0001 = has valid material data (else FUN_0045f200
  early-out); 0x0002 = UV-transform effect present (the 8-float block); 0x0200 =
  set in both your samples (a default capability bit); 0x0400 = checked at
  load, sets material_flag |= 2.

  blend preset (FUN_0045e230) maps to RenderWare RwBlendFunction (src +0x284,
  dst +0x288): 0→ONE/ZERO (opaque), 1→SRCALPHA/ONE (additive),
  2→INVSRCALPHA/SRCALPHA, 4→SRCALPHA/SRCALPHA, 3/default→SRCALPHA/INVSRCALPHA 
  (standard alpha).

  Your samples, decoded

  With UV effect (65 bytes):
  0D 00 0F 0F   version   = 0x0F0F000D
  03 02 00 00   flags     = 0x0203  (valid | UV-effect | 0x200)
  03 00 00 00   blend     = 3  → src=SRCALPHA(5), dst=INVSRCALPHA(6)
  02 00 00 00   +0x28C    = 2
  05 00 00 00   +0x290    = 5
  0A D7 23 3C   fx[0] = 0.01     ┐
  0A D7 23 3C   fx[1] = 0.01     │
  0A D7 A3 3C   fx[2] = 0.02     │ 8 UV-transform
  CD CC 4C 3D   fx[3] = 0.05     │ floats (present
  CD CC 4C 3D   fx[4] = 0.05     │ because flag 0x02)
  CD CC CC 3D   fx[5] = 0.10     │
  52 B8 5E 3F   fx[6] = 0.87     │
  00 00 00 3F   fx[7] = 0.50     ┘
  00 00 00 00   N        = 0  (no sub-records)
  00 00 00 00   countA   = 0
  00 00 00 00   countB   = 0
  00            trailing byte = 0

  No effect (33 bytes):
  0D 00 0F 0F   version = 0x0F0F000D
  01 02 00 00   flags   = 0x0201  (valid | 0x200; bit 0x02 clear → NO float
  block)
  03 00 00 00   blend   = 3
  02 00 00 00   +0x28C  = 2
  05 00 00 00   +0x290  = 5
  00 00 00 00   N       = 0
  00 00 00 00   countA  = 0
  00 00 00 00   countB  = 0
  00            trailing byte = 0

  The single flag bit 0x0002 is exactly what gates the 32-byte float block —
  everything else is identical between the two.

  What I couldn't pin down from static analysis: the precise semantics of the
  two int fields at +0x28C/+0x290 (read raw, values 2 and 5 here), and
  individual names for the 8 UV-transform floats — they're consumed as a block
  and fed into an animated-texture setup
  (FUN_004a2120/FUN_004db700/FUN_004a2990), but the reader doesn't label them.
  The values (three pairs-ish: 0.01,0.01,0.02 / 0.05,0.05,0.1 / 0.87,0.5) look
  like scroll/scale rates plus two scalars, but I'd want the render/update path
  (or a live trace) to name them with certainty rather than guess. Want me to
  chase those?

✻ Churned for 2m 44s

❯ figure out the other flields                                                  

  Called ghidra 3 times (ctrl+o to expand)

● FUN_0045ec30 is the per-frame material update, and it routes each optional
  block to its own animator. The 8 floats go through FUN_0045e4f0. Let me open
  that plus the sub-record reader/animator.

  Called ghidra 2 times (ctrl+o to expand)

● FUN_0045e4f0 is the UV animator — two sines plus linear scroll. The decompiler
  lost two of the eight floats into extraout_ST0 (FPU stack). Let me read the
  assembly to recover them exactly.

  Called ghidra (ctrl+o to expand)

● The assembly gives the exact math. FUN_00558b00 is the float→int truncation
  used to wrap the scroll offset to its fractional part. That fully resolves the
  8 floats. Now let me nail the remaining unknowns — the sub-records and the
  +0x28C/+0x290 render-state ints.

  Called ghidra 3 times (ctrl+o to expand)

● That completes the picture — the render path names every remaining field.
  Here's what the "other fields" actually are.

  The 8 UV floats — solved (exact formula)

  FUN_0045e4f0 is the per-frame UV animator. Reading its FPU assembly, each axis
  is linear scroll + a sine wobble:

  U(t) =  A·t  +  C·sin(E·t + G)
  V(t) =  B·t  +  D·sin(F·t + H)

  then each is wrapped to its fractional part (x − trunc(x), that's what
  FUN_00558b00 does) and applied as the material's texture UV offset (V
  negated), via FUN_004daf10 on the animated texture at +0x2A4.

  Mapping the eight serialized floats to the formula:

  ┌────────┬────────────┬─────────────────────┬─────────────┐
  │ stream │ struct off │        role         │ your sample │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[0]  │ +0x2A8     │ U scroll speed (·t) │ 0.01        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[1]  │ +0x2AC     │ V scroll speed (·t) │ 0.01        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[2]  │ +0x2B0     │ U wobble amplitude  │ 0.02        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[3]  │ +0x2B4     │ V wobble amplitude  │ 0.05        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[4]  │ +0x2B8     │ U wobble frequency  │ 0.05        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[5]  │ +0x2BC     │ V wobble frequency  │ 0.10        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[6]  │ +0x2C0     │ U wobble phase      │ 0.87        │
  ├────────┼────────────┼─────────────────────┼─────────────┤
  │ fx[7]  │ +0x2C4     │ V wobble phase      │ 0.50        │
  └────────┴────────────┴─────────────────────┴─────────────┘

  So your sample = slow diagonal scroll (0.01,0.01) with a small U ripple and a
  larger, slower V ripple. The two sin terms are what the decompiler had hidden
  in extraout_ST0.

  The two int fields at +0x28C / +0x290 — solved

  FUN_0045e370 (the render-state applier) reads a 5-dword render-state block at 
  +0x284 and pushes each to the engine's SetRenderState(id, value):

  ┌──────────┬───────────────┬───────────────────┬─────────────────────────┐
  │ struct   │  serialized?  │      source       │       applied as        │
  │   off    │               │                   │                         │
  ├──────────┼───────────────┼───────────────────┼─────────────────────────┤
  │ +0x284   │               │ from blend preset │ state 0x0A (+ 0x0C      │
  │ src      │ no — derived  │  (FUN_0045e230)   │ vertex-alpha = src≠2)   │
  │ blend    │               │                   │                         │
  ├──────────┼───────────────┼───────────────────┼─────────────────────────┤
  │ +0x288   │               │                   │                         │
  │ dst      │ no — derived  │ from blend preset │ state 0x0B              │
  │ blend    │               │                   │                         │
  ├──────────┼───────────────┼───────────────────┼─────────────────────────┤
  │ +0x28C   │ yes (stream   │ file              │ render state 0x1E       │
  │          │ off 0x0C)     │                   │                         │
  ├──────────┼───────────────┼───────────────────┼─────────────────────────┤
  │ +0x290   │ yes (stream   │ file              │ render state 0x1D       │
  │          │ off 0x10)     │                   │                         │
  ├──────────┼───────────────┼───────────────────┼─────────────────────────┤
  │ +0x294   │ no (runtime)  │ —                 │ gates states            │
  │ flags    │               │                   │ 0x18/0x1A/0x15/0x19     │
  └──────────┴───────────────┴───────────────────┴─────────────────────────┘

  So +0x28C and +0x290 are two per-material render-state overrides that sit
  right after the blend mode. Their raw values (2 and 5 in your samples) are
  pushed verbatim to render states 0x1E and 0x1D in the game's own render-state
  enum (which is not stock RenderWare — its blend states are 0x0A/0x0B, not RW's
  0x0C/0x0D). Nailing their human names would require mapping that engine enum
  through the D3D8 backend (DAT_0062ac18 vtable slot 8) — a separate dig if you
  want it, but structurally they're confirmed as draw-time render states, not
  geometry/animation data.

  Corrected field map (what's on disk vs. derived vs. runtime)

  Key correction to my earlier table: +0x284/+0x288 (src/dst blend) are not in
  the file — they're computed from the blend preset. The three serialized ints
  after the flags are blend-preset, renderstate-0x1E, renderstate-0x1D.

  The three trailing optional arrays are also now identified from their
  readers/animators:

  - N @ +0x2C8 → N × 0x3C-byte records (FUN_0045abb0/FUN_0045a4b0): an animated 
  multi-frame texture (flipbook — each record holds a rate float + a list of
  texture rasters loaded via RwStreamFindChunk type 6). Animated by
  FUN_0045e5d0.
  - countA @ +0x2D0 → 0x50-byte records: RGB color animation track (FUN_0045ec30
  perturbs the material's R/G/B).
  - countB @ +0x2D4 → 0x50-byte records: alpha animation track (perturbs A).

  Refined flags (+0x04)

  ┌───────┬──────────────────────────────────────────────────────────────────┐
  │  bit  │                             meaning                              │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x001 │ has valid material data (else early-out)                         │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x002 │ UV-transform effect present (the 8 floats + animated texture)    │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x020 │ runtime: fully transparent → skip render states                  │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x040 │ runtime: per-instance initialized (saved original color @        │
  │       │ +0x298)                                                          │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x100 │ runtime: color changed this frame                                │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x200 │ set in both samples; not consumed in any runtime path examined   │
  │       │ (looks like an authoring/import marker)                          │
  ├───────┼──────────────────────────────────────────────────────────────────┤
  │ 0x400 │ at load, sets the material's own flag |= 2                       │
  └───────┴──────────────────────────────────────────────────────────────────┘

  Only 0x001 and 0x002 are meaningful authoring bits in the file; 0x200 is
  always-set but inert at runtime. Everything in your two samples is now fully
  accounted for, field by field. Want me to chase the exact engine names for
  render states 0x1D/0x1E?

✻ Brewed for 3m 26s

● Unknown command: /expoer. Did you mean /export?

● Args from unknown skill: d.md