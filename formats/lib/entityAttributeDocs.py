# MESSAGE

# Define a control within the user interface associated with this class, used to specify an event that will
# be sent or received by this behavior.
#
# x Enum Id
# s Short Text Description
# t Long Help Text Description
# a Event/Message Type Transmit Or Receive
# b Data Type associated with this event/message
# d Default message

# RWS_MESSAGE(x, s, t, a, b, d)

from .entityAtributeDocs.CFXPartSpray import CFXPARTSPRAY_ATTRIBUTES


CREATE_ENTITY_ATTRIBUTE_COMMANDS = {
    "CSystemCommands": {
        0: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/csystemcommands.h",
            "name": "Attach Resource",
            "source.rws.name_original": "Resource",
            "description": "Specify a resource attached to this entity",
            "data": {"type": "GUID"},
        },
        1: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/csystemcommands.h",
            "name": "Matrix",
            "description": "Specify a transformation matrix associated with this entity",
            "data": {"type": "Matrix4x4"},
        },
        2: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/csystemcommands.h",
            "name": "Solid Collisions",
            "description": "collisions repel intersecting objects. (If Enable Collisions is true)",
            "data": {"type": "BOOLEAN", "default": 1},
        },
        3: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/csystemcommands.h",
            "name": "Enable Collisions",
            "description": "Enable/Disable collisions. If collisions are enabled but solid collisions is disabled then the object will be sent collision events",
            "data": {"type": "BOOLEAN", "default": 1},
        },
        4: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/csystemcommands.h",
            "name": "Invisible",
            "description": "Set visible/invisible flag, invisble objects are not rendered but may be used to generate collisions",
            "data": {"type": "BOOLEAN", "default": 0},
        },
    },
    "CAttributeHandler": {
        0: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/cattributehandler.h",
            "name": "Debug",
            "description": "Enable/Disable debugging, each attribute handler has a Debug flag which is availalbe for use by any derived class to enable/disable behaviour specific per instance debugging (Programmers should look at uATTRIBUTEHANDLER_FLAG_DEBUG in CAttributeHandler.h)",
            "data": {"type": "BOOLEAN", "default": 0},
        },
    },
    "CFXPartSpray": CFXPARTSPRAY_ATTRIBUTES,
    "CDirectorsCamera": {
        0: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/generic/cdirectorscamera/cdirectorscamera.h",
            "name": "Transmit Render Camera Event",
            "description": "When the iMsgDoRenderDirectorsCamera event is received then this event is sent.",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "RwCamera*",
                "msg_direction": "TRANSMIT",
                "default": "iMsgDoRender",
            },
        }
    },
    "CTFBCommand": {
        0: {
            "source": "GUESS",
            "name": "Script Object Name",
            "description": "Name of the object that can be used in scripts to refer to this instance",
            "data": {"type": "RwChar", "default": "", "read": "CString"},
        }
    },
    "AudioGlobalMixer": {
        0: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Receive Render Camera Event",
            "description": "Updates the listener position.",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "RwCamera*",
                "msg_direction": "RECEIVE",
                "default": "iMsgDoRender",
            },
        },
        1: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Stop All Voices",
            "description": "Stop all voices from playing.",
            "data": {
                "type": "MESSAGE",
                "msg_direction": "RECEIVE",
            },
        },
        # Global Voice Fade
        2: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Fade Voices Up",
            "description": "Fade all voices up to the level of the output gain.",
            "data": {
                "type": "MESSAGE",
                "msg_direction": "RECEIVE",
            },
        },
        3: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Fade Voices Down",
            "description": "Fade All voices down.",
            "data": {
                "type": "MESSAGE",
                "msg_direction": "RECEIVE",
            },
        },
        4: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Fade Ended Msg",
            "description": "Message sent out when a fade operation has completed.",
            "data": {
                "type": "MESSAGE",
                "msg_direction": "TRANSMIT",
            },
        },
        5: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Fade Step",
            "description": "Specify the step for each fade increment.",
            "data": {
                "type": "RwReal",
                "range": {
                    "min": 0.0,
                    "default": 0.03,
                    "max": 0.5,
                },
            },
        },
        # Audio Output Parameters
        6: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Output Gain",
            "description": "Change Output gain",
            "data": {
                "type": "RwReal",
                "range": {
                    "min": 0.0,
                    "default": 0.5,
                    "max": 1.0,
                },
            },
        },
        7: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Change Doppler scale",
            "description": "Change Doppler scale\nSet the Doppler scale or Doppler factor on the Listener object. The Doppler scale is a \nscale of how much the Doppler effect is exaggerated. A large Doppler scale will cause \nlarger change in frequency with relation to relative speed of a listener to a source. \nA smaller Doppler scale will cause smaller change in frequency with relation to relative \nspeed of a listener to a source.",
            "data": {
                "type": "RwReal",
                "range": {
                    "min": 0.0,
                    "default": 1,
                    "max": 10,
                },
            },
        },
        8: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Distance Factor",
            "description": "Sets the 3d distance factor for the user's coordinate system.",
            "data": {
                "type": "RwReal",
                "range": {
                    "min": 0.0,
                    "default": 1,
                    "max": 100,
                },
            },
        },
        9: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Roll-off Factor",
            "description": "Sets the global 3d roll-off factor for each sound. A higher roll-off factor makes the \nsounds approach zero gain as they depart, quicker than if it was left at 1.0f.",
            "data": {
                "type": "RwReal",
                "range": {
                    "min": 0.1,
                    "default": 1,
                    "max": 10,
                },
            },
        },
        10: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Speaker Configuration",
            "description": "Change Speaker Configuration",
            "data": {
                "type": "RwUInt32",
                "list": {
                    "values": [
                        "rwaSPEAKERCONFIG_STEREO",
                        "rwaSPEAKERCONFIG_MONO",
                        "rwaSPEAKERCONFIG_HEADPHONES",
                        "rwaSPEAKERCONFIG_SURROUND",
                    ],
                },
            },
        },
        # Debugging
        11: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/renderwareaudio/audioglobalmixer.h",
            "name": "Mixer Debug Output",
            "description": "If selected, display debug output in target. You need to enable print in the \nCDebugTools behavior before debug info will be displayed.",
            "data": {
                "type": "BOOLEAN",
                "default": 0,
            },
        },
    },
    "CXboxStndController": {
        0: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Port Select",
            "description": "Select which Game Pad",
            "data": {
                "type": "RwUInt32",
                "list": {"values": ["Pad 1", "Pad 2", "Pad 3", "Pad 4"]},
            },
        },
        1: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Left Joystick X Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_ACTN_TURN",
            },
        },
        2: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Left Joystick Y Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_ACTN_FWD",
            },
        },
        3: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Right Joystick X Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_ACTN_STRAFE",
            },
        },
        4: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Right Joystick Y Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_CAMERA_PITCH",
            },
        },
        5: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 1 (A) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_ACTN_FIRE",
            },
        },
        6: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 2 (B) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
                "default": "INQ_ACTN_JUMP",
            },
        },
        7: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 3 (X) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        8: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 4 (Y) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        9: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 5 (BLACK) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        10: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 6 (WHITE) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        11: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 7 (L Shoulder) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        12: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Button 8 (R Shoulder) Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        13: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Directional Pad Up Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        14: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Directional Pad Down Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        15: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Directional Pad Left Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        16: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Directional Pad Right Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        17: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Start Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        18: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Back Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        19: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Left Thumb Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        20: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Right Thumb Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        21: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Digital Joystick X Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
        22: {
            "source": "RWS",
            "source.rws.path": "RW/Studio/console/game_framework/source/modules/cxboxstndcontroller/cxboxstndcontroller.h",
            "name": "Digital Joystick Y Inquire",
            "description": "return's +-1.0 depending on state of this input device",
            "data": {
                "type": "MESSAGE",
                "msg_data_type": "return RwReal",
                "msg_direction": "RECEIVE",
            },
        },
    },
    "CTFBSound": {
        0: {
            "source": "GUESS",
            "name": "Sound Name",
            "description": "Name of the sound to play",
            "data": {"type": "RwChar", "default": "", "read": "CString"},
        },
        1: {
            "source": "GUESS",
            "name": "Sound File",
            "description": "Sound Filename",
            "data": {"type": "RwChar", "default": "", "read": "CString"},
        },
        2: {
            "source": "GUESS",
            "name": "UNKNOWN 2",
            "description": "",
            "data": {"type": "RwUInt32", "default": 100},
        },
        3: {
            "source": "GUESS",
            "name": "UNKNOWN 3",
            "description": "",
            "data": {"type": "RwUInt32", "default": 100},
        },
        4: {
            "source": "GUESS",
            "name": "UNKNOWN 4",
            "description": "",
            "data": {"type": "RwReal", "default": 300},
        },
        5: {
            # 5 is bool (ex. MELONS_Splat)
            "source": "GUESS",
            "name": "UNKNOWN 5",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        6: {
            # 6 is bool (ex. Simon_Fail01)
            "source": "GUESS",
            "name": "UNKNOWN 6",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        7: {
            # 7 is bool (ex. MudSlideLoop) maybe "Loop Sound"!?
            "source": "GUESS",
            "name": "Loop Sound",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        8: {
            # 8 is bool (ex. Simon_Mush_1)
            "source": "GUESS",
            "name": "UNKNOWN 8",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        9: {
            # 9 always 0 (tested: banquet, kingofny)
            "source": "GUESS",
            "name": "UNKNOWN 9",
            "description": "",
            "data": {"type": "RwUInt32", "default": 0},
        },
        10: {
            # 10 is bool (ex. Simon_Mush_1)
            "source": "GUESS",
            "name": "UNKNOWN 10",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        11: {
            # 11 is uint32 (ex. Whack_MoleOuch)
            "source": "GUESS",
            "name": "UNKNOWN 11",
            "description": "",
            "data": {"type": "RwUInt32", "default": 0},
        },
        12: {
            # 12 is uint32 (ex. Double Jump - 20), only example in banquet
            "source": "GUESS",
            "name": "UNKNOWN 12",
            "description": "",
            "data": {"type": "RwUInt32", "default": 0},
        },
        13: {
            # 13 is bool (ex. Gloria_Hipcheck_Hit)
            "source": "GUESS",
            "name": "UNKNOWN 13",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        14: {
            #  14 is bool (ex. Music_QueenieFlowers), maybe "Is Music"? (can only be found on music streams)
            "source": "GUESS",
            "name": "UNKNOWN 14",
            "description": "",
            "data": {"type": "BOOLEAN", "default": 0},
        },
        15: {
            # 15 always 0 (tested: banquet)
            "source": "GUESS",
            "name": "UNKNOWN 15",
            "description": "",
            "data": {"type": "RwUInt32", "default": 0},
        },
        16: {
            # 16 is uint32 (ex. Simon_Fail01), weirdly mostly exactly 1 bigger than last
            "source": "GUESS",
            "name": "UNKNOWN 16",
            "description": "",
            "data": {"type": "RwUInt32", "default": 0},
        },
    },
}

"""
"CAttributeHandler": {
    0: {
        "source": "RWS",
        "source.rws.path": "RW/Studio/console/game_framework/source/framework/core/attributehandler/cattributehandler.h",
        "name": "Debug",
        "description": "Enable/Disable debugging, each attribute handler has a Debug flag which is availalbe for use by any derived class to enable/disable behaviour specific per instance debugging (Programmers should look at uATTRIBUTEHANDLER_FLAG_DEBUG in CAttributeHandler.h)",
        "data": {"type": "BOOLEAN", "default": 0},
    },
},
"""
