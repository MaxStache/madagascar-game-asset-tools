CFXPARTSPRAY_ATTRIBUTES = {
    0: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Set Rate",
        "description": "Name of event which changes the output rate. Data points to a percentage (0 to 100). No effect if test fire.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "msg_data_type": "RwUInt32*",
        },
    },
    1: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Enable",
        "description": "Name of event which enables/disables system. Data holds flag (0 off, 1 on). Test firing toggles.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "msg_data_type": "RwBool*",
        },
    },
    2: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Position",
        "description": "Name of event which sets emitter position. Data holds new position and orientation. No effect if test fire.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "msg_data_type": "RwFrame*",
        },
    },
    3: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Emit On",
        "description": "Name of event which cause emitter to fire. No data needed. Test fire cause emission.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "default": "iMsgRunningTick",
        },
    },
    4: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Update On",
        "description": "Name of event which causes system to update. No data needed. Test fire causes single update.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "default": "iMsgRunningTick",
        },
    },
    # Display
    5: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Render",
        "description": "Name of event which initializes rendering. Data holds camera.",
        "data": {
            "type": "MESSAGE",
            "msg_direction": "RECEIVE",
            "msg_data_type": "RwCamera*",
            "default": "iMsgDoRender",
        },
    },
    6: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Render priority",
        "description": "Rendering priority of particles (0 = last).",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 65535,
            },
        },
    },
    7: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Render mode",
        "description": "Set the type of rendering. NO Z WRITE works particles with alpha. Z WRITE works if several particle systems overlap. DUAL PASS is slower but works in both cases.",
        "data": {
            "type": "RwUInt32",
            "list": {
                "values": ["NO Z WRITE", "Z WRITE", "DUAL PASS"],
                "default": 0,
            },
        },
    },
    8: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Source blend",
        "description": "Sets the RenderWare source blend mode for the particle system",
        "data": {
            "type": "RwUInt32",
            "list": {
                "values": [
                    "rwBLENDZERO",
                    "rwBLENDONE",
                    "rwBLENDSRCCOLOR",
                    "rwBLENDINVSRCCOLOR",
                    "rwBLENDSRCALPHA",  # default
                    "rwBLENDINVSRCALPHA",
                    "rwBLENDDESTALPHA",
                    "rwBLENDINVDESTALPHA",
                    "rwBLENDDESTCOLOR",
                    "rwBLENDINVDESTCOLOR",
                    "rwBLENDSRCALPHASAT",
                ],
                "default": 4,
            },
        },
    },
    9: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Destination blend",
        "description": "Sets the RenderWare destination blend mode for the particle system",
        "data": {
            "type": "RwUInt32",
            "list": {
                "values": [
                    "rwBLENDZERO",
                    "rwBLENDONE",
                    "rwBLENDSRCCOLOR",
                    "rwBLENDINVSRCCOLOR",
                    "rwBLENDSRCALPHA",  # default
                    "rwBLENDINVSRCALPHA",
                    "rwBLENDDESTALPHA",
                    "rwBLENDINVDESTALPHA",
                    "rwBLENDDESTCOLOR",
                    "rwBLENDINVDESTCOLOR",
                    "rwBLENDSRCALPHASAT",
                ],
                "default": 4,
            },
        },
    },
    10: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Positional offset",
        "description": "Positional offset of the emitter from object sending the position update message.",
        "data": {
            "type": "RwV3d",
            "ranges": (
                {
                    "min": -1000,
                    "default": 0,
                    "max": 1000,
                },
                {
                    "min": -1000,
                    "default": 0,
                    "max": 1000,
                },
                {
                    "min": -1000,
                    "default": 0,
                    "max": 1000,
                },
            ),
        },
    },
    11: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Positional heading",
        "description": "Positional heading offset of the emitter from object sending the position update message, in degrees.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -180,
                "default": 0,
                "max": 180,
            },
        },
    },
    12: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Positional deflection",
        "description": "Positional deflection of the emitter from object sending the position update message, in degrees.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -180,
                "default": 0,
                "max": 180,
            },
        },
    },
    # Emitter
    13: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Max particles",
        "description": "Maximum number of particles in the system. Should be as low as possible without causing starvation.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 1,
                "default": 5000,
                "max": 50000,
            },
        },
    },
    14: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Output rate",
        "description": "Num of particles emitted each time.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 100,
                "max": 5000,
            },
        },
    },
    15: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Output rate spread",
        "description": "Random additional particles emitted each time.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 500,
            },
        },
    },
    16: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Lifetime",
        "description": "Lifetime of particles in seconds.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0.5,
                "max": 10,
            },
        },
    },
    17: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Lifetime spread",
        "description": "Random additional lifetime of particles in seconds.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 5,
            },
        },
    },
    18: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Emitter spread",
        "description": "Emitter size in the X, Y and Z axes. Randomly applied.",
        "data": {
            "type": "RwV3d",
            "ranges": (
                {
                    "min": 0,
                    "default": 0,
                    "max": 500,
                },
                {
                    "min": 0,
                    "default": 0,
                    "max": 500,
                },
                {
                    "min": 0,
                    "default": 0,
                    "max": 500,
                },
            ),
        },
    },
    19: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Angular spread X",
        "description": "Emitter's angular variance on X axis. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 10,
                "max": 360,
            },
        },
    },
    20: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Angular spread Z",
        "description": "Emitter's angular variance on Z axis. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 10,
                "max": 360,
            },
        },
    },
    21: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Texture name",
        "description": "Name of texture to use. Blank = none. Texture is taken from textures on associated asset. Name must be EXACT (no path, no extension).",
        "data": {"type": "RwChar", "default": "", "read": "CString"},
    },
    22: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Sub-texture types",
        "description": "The number of sub-textures on the selected texture (if one). Sub-tex indices are auto assigned, top-left = 0, then increase left to right, top to bottom.",
        "data": {
            "type": "RwUInt32",
            "list": {
                "values": [
                    "NONE",
                    "1x2",
                    "2x2",
                    "2x4",
                    "4x4",
                    "4x8",
                    "8x8",
                ],
            },
        },
    },
    # Primary start state
    23: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Velocity",
        "description": "Initial velocity of particles",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.01,
                "default": 75.0,
                "max": 1000.0,
            },
        },
    },
    24: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Velocity spread",
        "description": "Initial additional velocity of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 500.0,
            },
        },
    },
    25: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity",
        "description": "Initial gravity rate on particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -25.0,
                "default": 9.81,
                "max": 25.0,
            },
        },
    },
    26: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag",
        "description": "Initial rate of drag on particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.1,
                "max": 1.0,
            },
        },
    },
    27: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color",
        "description": "Initial color of particles.",
        "data": {
            "type": "RwRGBA",
            "default": "0xFFFFFFFF",
        },
    },
    28: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Red spread",
        "description": "+/- variance of red in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    29: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Green spread",
        "description": "+/- variance of green in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    30: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Blue spread",
        "description": "+/- variance of blue in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    31: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Alpha spread",
        "description": "+/- variance of alpha in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    32: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size",
        "description": "Initial size of particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.1,
                "default": 5.0,
                "max": 100.0,
            },
        },
    },
    33: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size spread",
        "description": "Additional initial size of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
    34: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Minimum sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture).",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    35: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Maximum sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture).",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    # Primary end / anim state
    36: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration on",
        "description": "Allow continuous acceleration of particle on primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    37: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration",
        "description": "Level of continuous acceleration of particles during primary stage.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 20.0,
            },
        },
    },
    38: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration spread",
        "description": "Additional acceleration of particles during primary stage. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 10.0,
            },
        },
    },
    39: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity on",
        "description": "Allow animation of gravity over primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    40: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity",
        "description": "Stage end gravity rate on particle.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -25.0,
                "default": 9.81,
                "max": 25.0,
            },
        },
    },
    41: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag on",
        "description": "Allow animation of drag over primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    42: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag",
        "description": "Stage end rate of drag on particle.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.1,
                "max": 1.0,
            },
        },
    },
    43: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color on",
        "description": "Allow animation of color over primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    44: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color",
        "description": "Stage end color of particles.",
        "data": {
            "type": "RwRGBA",
            "default": 4294967295,
        },
    },
    45: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Red spread",
        "description": "Stage end +/- variance of red in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    46: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Green spread",
        "description": "Stage end +/- variance of green in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    47: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Blue spread",
        "description": "Stage end +/- variance of blue in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    48: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Alpha spread",
        "description": "Stage end +/- variance of alpha in particle's color. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    49: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Size on",
        "description": "Allow animation of particle size over primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    50: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size",
        "description": "Stage end size of particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.1,
                "default": 0.5,
                "max": 100.0,
            },
        },
    },
    51: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size spread",
        "description": "Additional stage end size of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
    52: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Sub-texture on",
        "description": "Allows animation of the sub-texture index over the primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    53: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Minimum end sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). This index is animated from the value in the stage start.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    54: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Maximum end sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). This index is animated from the value in the stage start.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    55: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Number of sub-tex loops",
        "description": "Number of times to loop from start index to end index of the sub-texture",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 100.0,
            },
        },
    },
    56: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "No. sub-tex loops spread",
        "description": "Number of random loops from start index to end index of the sub-texture.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
    # Secondary change over
    57: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary on",
        "description": "Allow secondary state.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    58: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary lifetime change",
        "description": "Life time at which change to secondary state occurs in seconds.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.1,
                "default": 1,
                "max": 15.0,
            },
        },
    },
    59: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary emitter",
        "description": "Number of extra particles emitted on secondary state emitter. For each first stage particle, this number will be emitted. Only noticeable if emitter angle is non-zero.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 500,
            },
        },
    },
    60: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary emit spread",
        "description": "Number of additional extra particles PER primary stage particle. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 250,
            },
        },
    },
    61: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary emit life adjust",
        "description": "Adjustment of lifetime on second stage emitted particles ONLY. Based on lifetime of source primary stage particle. Variance in seconds. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 10,
            },
        },
    },
    62: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary emitter min angle",
        "description": "Minimum angular deflection of particles. Randomly applied between min & max. Slower if non-zero. Heading change random.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 180.0,
            },
        },
    },
    63: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary emitter max angle",
        "description": "Maximum angular deflection of particles. Randomly applied between min & max. Slower if non-zero. Heading change random.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 180.0,
            },
        },
    },
    # Secondary start state
    64: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary boost on",
        "description": "Enable one time only secondary boost.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    65: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary boost",
        "description": "Secondary state emitter particle velocity boost, once only. Instantly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 1000.0,
            },
        },
    },
    66: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Secondary boost spread",
        "description": "Additional secondary particle velocity boost. Instant, random application.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 500.0,
            },
        },
    },
    67: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity on",
        "description": "Allow change of gravity.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    68: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity",
        "description": "Gravity rate per second on particle. Instantly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -25.0,
                "default": 9.81,
                "max": 25.0,
            },
        },
    },
    69: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag on",
        "description": "Allow change of drag.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    70: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag",
        "description": "Rate of drag on particle. Instantly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.1,
                "max": 1.0,
            },
        },
    },
    71: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color on",
        "description": "Allow change of color.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    72: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color",
        "description": "Start color of particle. Instantly applied.",
        "data": {
            "type": "RwRGBA",
            "default": 4294967295,
        },
    },
    73: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Red spread",
        "description": "+/- variance of red in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    74: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Green spread",
        "description": "+/- variance of green in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    75: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Blue spread",
        "description": "+/- variance of blue in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    76: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Alpha spread",
        "description": "+/- variance of alpha in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    77: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Size on",
        "description": "Allow change of particle size.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    78: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size",
        "description": "Start size of particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.1,
                "default": 0.5,
                "max": 100.0,
            },
        },
    },
    79: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size spread",
        "description": "Additional extra size of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
    80: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Sub-texture on",
        "description": "Allows snap change of the sub-texture index as enters the secondary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    81: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Minimum sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). Snap change of index occurs.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    82: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Maximum sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). Snap change of index occurs.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    # Secondary end / anim state
    83: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration on",
        "description": "Allow continuous acceleration over secondary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    84: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration",
        "description": "Level of continuous acceleration of particles during stage.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 20.0,
            },
        },
    },
    85: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Acceleration spread",
        "description": "Additionally extra acceleration of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0,
                "default": 0,
                "max": 10.0,
            },
        },
    },
    86: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity on",
        "description": "Allow animation of gravity over secondary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    87: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Gravity",
        "description": "Stage end gravity rate per second on particle.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": -25.0,
                "default": 9.81,
                "max": 25.0,
            },
        },
    },
    88: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag on",
        "description": "Allow animation of drag over secondary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    89: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Drag",
        "description": "Stage end rate of drag on particle.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.1,
                "max": 1.0,
            },
        },
    },
    90: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color on",
        "description": "Allow animation of color over secondary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    91: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Color",
        "description": "Stage end color of particles.",
        "data": {
            "type": "RwRGBA",
            "default": 4294967295,
        },
    },
    92: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Red spread",
        "description": "Stage end +/- variance of red in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    93: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Green spread",
        "description": "Stage end +/- variance of green in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    94: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Blue spread",
        "description": "Stage end +/- variance of blue in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    95: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Alpha spread",
        "description": "Stage end +/- variance of alpha in particles. Randomly applied.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 255,
            },
        },
    },
    96: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Size on",
        "description": "Allow animation of particle size over stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    97: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size",
        "description": "Stage end size of particles.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.1,
                "default": 0.5,
                "max": 100.0,
            },
        },
    },
    98: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Particle size spread",
        "description": "Stage end additional size of particles. Randomly applied.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
    99: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Sub-texture on",
        "description": "Allows animation of the sub-texture index over the primary stage.",
        "data": {"type": "BOOLEAN", "default": 0},
    },
    100: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Minimum end sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). This index is animated from the value in the stage start.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    101: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Maximum end sub-tex index",
        "description": "The sub-texture index is randomly selected between min and max (if using a texture). This index is animated from the value in the stage start.",
        "data": {
            "type": "RwUInt32",
            "range": {
                "min": 0,
                "default": 0,
                "max": 63,
            },
        },
    },
    102: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "Number of sub-tex loops",
        "description": "Number of times to loop from start index to end index of the sub-texture. Start index here is the index on entry to the secondary stage.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 100.0,
            },
        },
    },
    103: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/modules/FX/cfx_particles/partspray/cfxpartspray.h",
        "name": "No. sub-tex loops spread",
        "description": "Number of random loops from start index to end index of the sub-texture. Start index here is the index on entry to the secondary stage.",
        "data": {
            "type": "RwReal",
            "range": {
                "min": 0.0,
                "default": 0.0,
                "max": 50.0,
            },
        },
    },
}
