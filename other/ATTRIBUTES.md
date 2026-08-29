<!-- markdownlint-disable MD010 -->

# TFB Entity Reference

## CameraData

```text
Sector 2759
Length: 328 Type: 1796 (sf_CreateEntity)
Create Entity Call:
	Behaviour:	CameraData
	Entity ID:	{ec90332c-5bfe-b74f-8a97-7a44874c4310}
	Class:	CTFBCommand
		0x5c - Script Object Name: Alex_FountainCam01
	Class:	CameraData
		0x8c - Attribute   0: [Alex_FountainCam01  ][41 6C 65 78 5F 46 6F 75 6E 74 61 69 6E 43 61 6D 30 31 00 BF]
		0xa4 - Attribute   1: [SplashMaster    ][53 70 6C 61 73 68 4D 61 73 74 65 72 00 BF BF BF]
		0xb8 - Attribute   2: [  4B       C][00 00 34 42 00 00 A0 40 00 80 AC 43]
		0xc4 - Attribute   3: [    ][00 00 00 00]
		0xdc - Attribute   4: [SplashMaster    ][53 70 6C 61 73 68 4D 61 73 74 65 72 00 BF BF BF]
		0xf0 - Attribute   5: [       A    ][00 00 00 00 00 00 88 41 00 00 00 00]
		0xfc - Attribute   6: [    ][00 00 00 00]
		0x108 - Attribute   7: [  pB][00 00 70 42]
		0x114 - Attribute   8: [    ][00 00 00 00]
	Class:	CAttributeHandler
		0x13c - Debug          : RWBool(0) (False)
	isGlobal:	False
```

| Attr | Type | Meaning |
| --- | --- | --- |
| 0 | cstring | Name |
| 1 | cstring | Look from target — `(Current)` = none |
| 2 | 3× f32 | Look from horizontal / vertical / heading offset |
| 3 | s32 bool | Look from heading relative |
| 4 | cstring | Look at target — `(Current)` = none |
| 5 | 3× f32 | Look at horizontal / vertical / heading offset |
| 6 | s32 bool | Look at heading relative |
| 7 | f32 | Field of view, degrees |
| 8 | s32 bool | Laziness (smoothed follow) |

---

## CTFBSound

```text
Sector 1879
Length: 360 Type: 1796 (sf_CreateEntity)
Create Entity Call:
	Behaviour:	CTFBSound
	Entity ID:	{d64acb2a-5f3c-7747-860b-4e44ee7da71b}
	Class:	CTFBCommand
		0x54 - Script Object Name: Alex_Roar_1
	Class:	CTFBSound
		0x7c - Sound Name     : Alex_Roar_1
		0x98 - Sound File     : Alex_roar_01.wav
		0xa4 - UNKNOWN 2      : 100
		0xb0 - UNKNOWN 3      : 100
		0xbc - UNKNOWN 4      : 300.0
		0xc8 - UNKNOWN 5      : RWBool(0) (False)
		0xd4 - UNKNOWN 6      : RWBool(0) (False)
		0xe0 - UNKNOWN 7      : RWBool(0) (False)
		0xec - UNKNOWN 8      : RWBool(0) (False)
		0xf8 - UNKNOWN 9      : 0
		0x104 - UNKNOWN 10     : RWBool(0) (False)
		0x110 - UNKNOWN 11     : 0
		0x11c - UNKNOWN 12     : 0
		0x128 - UNKNOWN 13     : RWBool(1) (True)
		0x134 - UNKNOWN 14     : RWBool(0) (False)
	Class:	CAttributeHandler
		0x15c - Debug          : RWBool(0) (False)
	isGlobal:	False
```

| Attr | Type | Meaning |
| --- | --- | --- |
| 0 | cstring | Sound name (in wave dict) |
| 1 | cstring | Sound file (not used by game) |
| 2 | f32 | Volume % |
| 3 | f32 | Pitch % |
| 4 | f32 | Radius / max audible distance (in TFB feet) |
| 5 | f32 | Stereo pan % |
| 6 | RWBool | Stream from disk |
| 7 | RWBool | Looping |
| 8 | RWBool | Smooth distance falloff |
| 9 | RWBool | Doppler velocity tracking |
| 10 | RWBool | Attach to emitter |
| 11 | f32 | Random volume variation % |
| 12 | f32 | Random pitch variation % |
| 13 | RWBool | Allow overlapping instances |
| 14 | RWBool | Route to music bus (is music?) |
| 15 | NONE | — |
| 16 | RWInt32 | Localized string ID (subtitle) — Dutch console version only |

---

## GameCamera

```text
Length: 524 Type: 1796 (sf_CreateEntity)
Create Entity Call:
	Behaviour:	GameCamera
	Entity ID:	{f2efe12b-89d3-aa45-8ee3-9906cdd1f7c0}
	Class:	CSystemCommands
		0x5c - Attach Resource: {3d338f61-bd98-624b-a54b-adceec8ac526}
	Class:	CTFBCommand
		0x84 - Script Object Name: Default Cam
	Class:	GameCamera
		0xb0 - Attribute   0: [iMsgDoRender    ][69 4D 73 67 44 6F 52 65 6E 64 65 72 00 BF BF BF]
		0xbc - Attribute   1: [    ][FF FF 00 00]
		0xd4 - Attribute   2: [3rd_person_cam  ][33 72 64 5F 70 65 72 73 6F 6E 5F 63 61 6D 00 BF]
		0xec - Attribute   3: [look_at_point   ][6C 6F 6F 6B 5F 61 74 5F 70 6F 69 6E 74 00 BF BF]
		0xf8 - Attribute   4: [  4B][00 00 34 42]
		0x104 - Attribute   5: [  4 ][00 00 34 C2]
		0x120 - Attribute   6: [INQ_CAMERA_PITCH    ][49 4E 51 5F 43 41 4D 45 52 41 5F 50 49 54 43 48 00 BF BF BF]
		0x13c - Attribute   7: [INQ_CAMERA_ROTATE   ][49 4E 51 5F 43 41 4D 45 52 41 5F 52 4F 54 41 54 45 00 BF BF]
		0x148 - Attribute   8: [    ][FF FF FF FF]
		0x154 - Attribute   9: [    ][FF FF FF FF]
	Class:	CSystemCommands
		0x1b4 - Matrix         : Matrix4x4([1.000  , 0.000, 0.000  , 0.000]
                                           [0.000  , 1.000, 0.000  , 0.000]
                                           [0.000  , 0.000, 1.000  , 0.000]
                                           [339.054, 0.000, 130.129, 0.000])
		0x1c0 - Solid Collisions: RWBool(255) (True)
		0x1cc - Enable Collisions: RWBool(255) (True)
		0x1d8 - Invisible      : RWBool(1) (True)
	Class:	CAttributeHandler
		0x200 - Debug          : RWBool(0) (False)
	isGlobal:	False
```

| Attr | Type | Meaning |
| --- | --- | --- |
| 0 | cstring | "In render event" message |
| 1 | — | — |
| 2 | cstring | "Out render event" message |
| 3 | cstring | "Look at" message |
| 4 | f32 | FOV |
| 5 | f32 | — |
| 6 | cstring | Cam pitch event |
| 7 | cstring | Cam rotate event |
| 8 | RWBool | — |
| 9 | RWBool | — |

---

## LevelHub

| Attr | Type | Meaning |
| --- | --- | --- |
| 0 | u32 value, cstring | Implicit value global. Same as attr 1 with type forced to 0. Only 2 shipped, both Mutiny: `Have Red Key_3`, `Have Gun and ammo` |
| 1 | u32 value, u32 tfbtypeTag, cstring | Global variable declaration |
| 2 | u32 unused, cstring | Message name declaration |
| 4 | cstring | Level audio stream path |
| 5 | cstring | Music stream name |

### tfbtypeTag

| Tag | Type |
| --- | --- |
| 0x00 | value |
| 0x01 | behavior |
| 0x02 | actor |
| 0x03 | message |
| 0x04 | sound |
| 0x05 | camera |
| 0x06 | — |
| 0x07 | sprite |
| 0x8X | set of X |

---

## SpriteObject

```text
Length: 548 Type: 1796 (sf_CreateEntity)
Create Entity Call:
	Behaviour:	SpriteObject
	Entity ID:	{f5766a57-ee58-484c-a0a1-ee12b6e43879}
	Class:	CTFBCommand
		0x58 - Script Object Name: Ring_Green
	Class:	SpriteObject
		0x84 - Attribute   0: [Ring_Green  ][52 69 6E 67 5F 47 72 65 65 6E 00 BF]                 NAME
		0x90 - Attribute   1: [    ][03 00 00 00]                                                 Content kind 0=texture, 1=numeric text, 2=localized text, 3=linked world entity
		0xa0 - Attribute   2: [ none   ][3C 6E 6F 6E 65 3E 00 BF]                                 TEXTURE NAME (placeholder <need a texture name...>)
		0xb0 - Attribute   3: [ none   ][3C 6E 6F 6E 65 3E 00 BF]                                 FONT NAME (placeholder <... or a font>)
		0xc0 - Attribute   4: [ none   ][3C 6E 6F 6E 65 3E 00 BF]
		0xcc - Attribute   5: [    ][00 00 00 00]                                                 Visible
		0xd8 - Attribute   6: [    ][00 00 00 00]
		0xe4 - Attribute   7: [    ][00 00 00 00]                                                 Justification
		0xf0 - Attribute   8: [    ][00 00 00 00]                                                 Rotation (deg)
		0x104 - Attribute   9: [   D   B    ][00 C0 0D 44 00 00 2C 42 00 00 00 00]                Location (x, y; z forced to FLT_MAX)
		0x118 - Attribute  10: [   A   A    ][00 00 20 41 00 00 20 41 00 00 00 00]                Scale%
		0x124 - Attribute  11: [    ][00 00 00 00]                                                z-order
		0x130 - Attribute  12: [    ][01 00 00 00]                                                Auto-size from texture
		0x13c - Attribute  13: [   B][00 00 00 42]                                                Explicit width
		0x148 - Attribute  14: [   B][00 00 00 42]                                                Explicit height

		BELOW - Linked World Entity
		0x184 - Attribute  15: [    {6FFDCB62-02E4-47B4-AAC4-3FDBD85AE9B3}  NY_Ring ][FF FF FF FF 7B 36 46 46 44 43 42 36 32 2D 30 32 45 34 2D 34 37 42 34 2D 41 41 43 34 2D 33 46 44 42 44 38 35 41 45 39 42 33 7D 20 20 4E 59 5F 52 69 6E 67 00]

		0x190 - Attribute  16: [    ][01 00 00 00]                                                Scale with distance
		0x19c - Attribute  17: [    ][00 00 00 00]
		0x1a8 - Attribute  18: [    ][00 00 00 00]                                                roll
		0x1b4 - Attribute  19: [    ][00 00 00 00]                                                tilt
		0x1c0 - Attribute  20: [    ][00 00 00 00]                                                facing
		0x1cc - Attribute  21: [    ][00 BF BF BF]                                                Parent / group sprite name
		0x1d8 - Attribute  22: [    ][00 00 00 00]                                                Attach anchor in parent (same 3×3 code as attr 7)
		0x1e4 - Attribute  23: [    ][00 00 00 00]                                                Localized string id; skipped when kind == 1
		0x1f0 - Attribute  26: [    ][00 00 00 00]                                                Text auto-fit axis (0 = scale X, 1 = scale Y)
	Class:	CAttributeHandler
		0x218 - Debug          : RWBool(0) (False)
	isGlobal:	False
```

| Attr | Type | Meaning |
| --- | --- | --- |
| 0 | cstring | Sprite object name (rebinds the entity) |
| 1 | s32 | Content kind — 0 = texture, 1 = numeric text, 2 = localized text, 3 = linked world entity |
| 2 | cstring | Texture name |
| 3 | cstring | Font name (`.met`, extension stripped) |
| 4 | cstring | — |
| 5 | s32 bool | Visible |
| 6 | s32 bool | — |
| 7 | s32 | Justification, 3×3 anchor code 0–8 |
| 8 | f32 | Rotation (deg) |
| 9 | 3× f32 | Location (x, y; z forced to `FLT_MAX`) |
| 10 | 2× f32 | Scale % |
| 11 | s32 (low byte) | Priority / z-order |
| 12 | s32 bool | Auto-size from texture |
| 13 | f32 | Explicit width |
| 14 | f32 | Explicit height |
| 15 | u32(−1) + ASCII `{GUID}  Name` | Linked world entity |
| 16 | s32 bool | Shrink this sprite out as its anchor gets far away |
| 17 | s32 bool | — |
| 18 | f32 | Roll |
| 19 | f32 | Tilt |
| 20 | f32 | Facing |
| 21 | cstring | Parent / group sprite name |
| 22 | u32 | Parent inheritance bitmask |
| 23 | s32 | Attach anchor in parent (same 3×3 code as attr 7) |
| 24 | u32 | Tint RGBA |
| 25 | s32 | Localized string id; skipped when kind == 1 |
| 26 | s32 bool | Text auto-fit axis (0 = scale X, 1 = scale Y) |

### Parent inheritance bitmask

| Bit | Field | Effect |
| --- | --- | --- |
| 0x01 | Position | `+0xAC/+0xB0` = parent's, plus an anchor delta: `FUN_004509F0(parent justification) − FUN_004509F0(attr 23)` |
| 0x02 | Scale | `+0xB4/+0xB8` = parent's |
| 0x04 | Tint | `+0xCC/+0xCD/+0xCE` = parent's RGB — RGB only, alpha is bit 6 |
| 0x08 | Visibility | if (own `+0xA8` != 0) `+0xA8` = parent's — AND, not copy: visible only if both are |
| 0x10 | Rotation | `+0xBC` = parent's |
| 0x20 | Priority | `+0xD0` += parent's `+0xD0` — additive, not copy |
| 0x40 | Alpha | `+0xC0` = parent's |

**Default:** `27 = 0x1B` (bits 0, 1, 3, 4) → position + scale + visibility + rotation
