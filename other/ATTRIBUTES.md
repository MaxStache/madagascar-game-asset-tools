════════════════════ CameraData ════════════════════

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

ATTRIBUTE 0  TYPE: cstring  │ name    
ATTRIBUTE 1  TYPE: cstring  │ look from target — "(Current)" = none            
ATTRIBUTE 2  TYPE: 3× f32   │ look from horizontal / vertical / heading offset 
ATTRIBUTE 3  TYPE: s32 bool │ look from heading relative                       
ATTRIBUTE 4  TYPE: cstring  │ look at target — "(Current)" = none              
ATTRIBUTE 5  TYPE: 3× f32   │ look at horizontal / vertical / heading offset   
ATTRIBUTE 6  TYPE: s32 bool │ look at heading relative                         
ATTRIBUTE 7  TYPE: f32      │ field of view, degrees                           
ATTRIBUTE 8  TYPE: s32 bool │ laziness (smoothed follow)                       


════════════════════ CTFBSound ════════════════════

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


ATTRIBUTE 0   TYPE: cstring   | Sound Name (In Wave Dict)
ATTRIBUTE 1   TYPE: cstring   | Sound File (Not used by game)
ATTRIBUTE 2   TYPE: f32       | volume%
ATTRIBUTE 3   TYPE: f32       | pitch%
ATTRIBUTE 4   TYPE: f32       | radius / max audible distance (in TFB feet)
ATTRIBUTE 5   TYPE: f32       | Stereo pan%
ATTRIBUTE 6   TYPE: RWBool    | stream from disk
ATTRIBUTE 7   TYPE: RWBool    | looping
ATTRIBUTE 8   TYPE: RWBool    | Smooth distance falloff
ATTRIBUTE 9   TYPE: RWBool    | Doppler velocity tracking
ATTRIBUTE 10  TYPE: RWBool    | Attach to emitter
ATTRIBUTE 11  TYPE: f32       | random volume variation%
ATTRIBUTE 12  TYPE: f32       | random pitch variation%
ATTRIBUTE 13  TYPE: RWBool    | allow to be played multiple times at same time (allow overlapping instances)
ATTRIBUTE 14  TYPE: RWBool    | Route to music bus (is music?)
ATTRIBUTE 15  TYPE: NONE      | -
ATTRIBUTE 16  TYPE: RWInt32   | localized string ID (subtitle) (dutch console version only)

════════════════════ GameCamera ════════════════════
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
	isGlobal:	Falseit 

ATTRIBUTE 0   TYPE: cstring   | "in render event" message
ATTRIBUTE 1   TYPE:           |
ATTRIBUTE 2   TYPE: cstring   | "out render event" message
ATTRIBUTE 3   TYPE: cstring   | "look at" message
ATTRIBUTE 4   TYPE: f32       | fov
ATTRIBUTE 5   TYPE: f32       | 
ATTRIBUTE 6   TYPE: cstring   | cam pitch event
ATTRIBUTE 7   TYPE: cstring   | cam rotate event
ATTRIBUTE 8   TYPE: RWBool    |
ATTRIBUTE 9   TYPE: RWBool    |



════════════════════ LevelHub ════════════════════

ATTRIBUTE 0   TYPE: u32 value, cstring                   | Implicit value global NOTED: same as attr 1 with type forced to 0. Only 2 shipped, both mutiny: Have Red Key_3, Have Gun and ammo
ATTRIBUTE 1   TYPE: u32 value, u32 tfbtypeTag, cstring   | Global variable declaration
ATTRIBUTE 2   TYPE: u32 unused, cstring                  | Message name declaration
ATTRIBUTE 4   TYPE: cstring                              | Level audio stream path
ATTRIBUTE 5   TYPE: cstring                              | Music stream name

tfbtypeTag  │ type     

0x00        │ value       
0x01        │ behavior       
0x02        │ actor       
0x04        │ sound      
0x03        | message 
0x05        │ camera     
0y06        | - - -      
0x07        │ sprite      
0x8X        │ set of X

════════════════════ SpriteObject ════════════════════

Length: 548 Type: 1796 (sf_CreateEntity)
Create Entity Call:
	Behaviour:	SpriteObject
	Entity ID:	{f5766a57-ee58-484c-a0a1-ee12b6e43879}
	Class:	CTFBCommand
		0x58 - Script Object Name: Ring_Green
	Class:	SpriteObject
		0x84 - Attribute   0: [Ring_Green  ][52 69 6E 67 5F 47 72 65 65 6E 00 BF] NAME
		0x90 - Attribute   1: [    ][03 00 00 00]  Content kind 0=texture, 1=numeric text, 2=localized text, 3=linked world entity
		0xa0 - Attribute   2: [ none   ][3C 6E 6F 6E 65 3E 00 BF] TEXTURE NAME (placeholder  <need a texture name...>)
		0xb0 - Attribute   3: [ none   ][3C 6E 6F 6E 65 3E 00 BF] FONT NAME (placeholder <... or a font>)
		0xc0 - Attribute   4: [ none   ][3C 6E 6F 6E 65 3E 00 BF]
		0xcc - Attribute   5: [    ][00 00 00 00] Visible
		0xd8 - Attribute   6: [    ][00 00 00 00] 
		0xe4 - Attribute   7: [    ][00 00 00 00] Justification
		0xf0 - Attribute   8: [    ][00 00 00 00] Rotation (deg)
		0x104 - Attribute   9: [   D   B    ][00 C0 0D 44 00 00 2C 42 00 00 00 00]  Location (x, y; z forced to FLT_MAX)
		0x118 - Attribute  10: [   A   A    ][00 00 20 41 00 00 20 41 00 00 00 00]  Scale%
		0x124 - Attribute  11: [    ][00 00 00 00]  z-order
		0x130 - Attribute  12: [    ][01 00 00 00]  Auto-size from texture
		0x13c - Attribute  13: [   B][00 00 00 42]  Explicit width
		0x148 - Attribute  14: [   B][00 00 00 42]   Explicit height

		BELOW - Linked World Entity
		0x184 - Attribute  15: [    {6FFDCB62-02E4-47B4-AAC4-3FDBD85AE9B3}  NY_Ring ][FF FF FF FF 7B 36 46 46 44 43 42 36 32 2D 30 32 45 34 2D 34 37 42 34 2D 41 41 43 34 2D 33 46 44 42 44 38 35 41 45 39 42 33 7D 20 20 4E 59 5F 52 69 6E 67 00]

		0x190 - Attribute  16: [    ][01 00 00 00] Scale with distance
		0x19c - Attribute  17: [    ][00 00 00 00]
		0x1a8 - Attribute  18: [    ][00 00 00 00] roll
		0x1b4 - Attribute  19: [    ][00 00 00 00] tilt
		0x1c0 - Attribute  20: [    ][00 00 00 00] facing
		0x1cc - Attribute  21: [    ][00 BF BF BF] Parent / group sprite name
		0x1d8 - Attribute  22: [    ][00 00 00 00] Attach anchor in parent (same 3×3 code as attr 7)
		0x1e4 - Attribute  23: [    ][00 00 00 00] Localized string id; skipped when kind == 1
		0x1f0 - Attribute  26: [    ][00 00 00 00] Text auto-fit axis (0 = scale X, 1 = scale Y)
	Class:	CAttributeHandler
		0x218 - Debug          : RWBool(0) (False)
	isGlobal:	False

ATTRIBUTE 0    TYPE: cstring                        | Sprite object name (rebinds the entity)
ATTRIBUTE 1    TYPE: s32                            | Content kind 0=texture, 1=numeric text, 2=localized text, 3=linked world entity
ATTRIBUTE 2    TYPE: cstring                        | Texture name
ATTRIBUTE 3    TYPE: cstring                        | Font name (.met, extension stripped)
ATTRIBUTE 4    TYPE: cstring                        | -
ATTRIBUTE 5    TYPE: s32bool                        | Visible
ATTRIBUTE 6    TYPE: s32bool                        | -
ATTRIBUTE 7    TYPE: s32                            | Justification, 3×3 anchor code 0–8
ATTRIBUTE 8    TYPE: f32                            | Rotation (deg)
ATTRIBUTE 9    TYPE: 3×f32                          | Location (x, y; z forced to FLT_MAX)
ATTRIBUTE 10   TYPE: 2×f32                          | Scale%
ATTRIBUTE 11   TYPE: s32 (low byte)                 | Priority / z-order
ATTRIBUTE 12   TYPE: s32bool                        | Auto-size from texture
ATTRIBUTE 13   TYPE: f32                            | Explicit width
ATTRIBUTE 14   TYPE: f32                            | Explicit height
ATTRIBUTE 15   TYPE: u32(−1) + ASCII {GUID}  Name   | Linked world entity
ATTRIBUTE 16   TYPE: s32bool                        | shrink this sprite out as its anchor gets far away
ATTRIBUTE 17   TYPE: s32bool                        | -
ATTRIBUTE 18   TYPE: f32                            | roll
ATTRIBUTE 19   TYPE: f32                            | tilt
ATTRIBUTE 20   TYPE: f32                            | facing
ATTRIBUTE 21   TYPE: cstring                        | Parent / group sprite name 
ATTRIBUTE 22   TYPE: u32                            | Parent inheritance bitmask 
ATTRIBUTE 23   TYPE: s32                            | Attach anchor in parent (same 3×3 code as attr 7)
ATTRIBUTE 24   TYPE: u32                            | Tint RGBA
ATTRIBUTE 25   TYPE: s32                            | Localized string id; skipped when kind == 1
ATTRIBUTE 26   TYPE: s32bool                        | Text auto-fit axis (0 = scale X, 1 = scale Y)

Parent inheritance bitmask:

0x01 │ position   │ +0xAC/+0xB0 = parent's, plus an anchor delta: FUN_004509F0(parent justification) − FUN_004509F0(attr 23)
0x02 │ scale      │ +0xB4/+0xB8 = parent's                                                                                  
0x04 │ tint       │ +0xCC/+0xCD/+0xCE = parent's RGB — RGB only, alpha is bit 6                                             
0x08 │ visibility │ if (own +0xA8 != 0) +0xA8 = parent's — AND, not copy: visible only if both are                          
0x10 │ rotation   │ +0xBC = parent's                                                                                        
0x20 │ priority   │ +0xD0 += parent's +0xD0 — additive, not copy                                                            
0x40 │ alpha      │ +0xC0 = parent's                                                                                        

DEFAULT
27 = 0x1B (2905) │ 0,1,3,4 │ position + scale + visibility + rotation