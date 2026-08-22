from enum import Enum


class RWClass(str, Enum):
    CSystemCommands = "CSystemCommands"
    CTFBCommand = "CTFBCommand"
    CProtoActor = "CProtoActor"
    CAttributeHandler = "CAttributeHandler"
    LevelHub = "LevelHub"
    CTFBWorld = "CTFBWorld"
    CTFBModel = "CTFBModel"
    SpriteManager = "SpriteManager"
    SpriteObject = "SpriteObject"
    AssetHub = "AssetHub"
    CTFBSound = "CTFBSound"
    CameraData = "CameraData"
    CFXPartSpray = "CFXPartSpray"
    CFXColorLight = "CFXColorLight"
    GameCamera = "GameCamera"
    CDirectorsCamera = "CDirectorsCamera"
    CFXMotionBlur = "CFXMotionBlur"
    RadarRender = "RadarRender"
    TFBShadowCamera = "TFBShadowCamera"
    ShadowRender = "ShadowRender"
