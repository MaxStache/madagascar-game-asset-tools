import copy
import io
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, override
import uuid

from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_alignedString, write_u32, write_bool, write_s32
from madagascar.lib.rwConstants import strfunc_func
from madagascar.lib.rw_basics import (
    RW_Matrix4x4,
    RW_StreamFunc,
    RWHeader,
    expect_chunk_type_or_raise,
)
from .sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset

if TYPE_CHECKING:
    from madagascar.stream.query import StreamQueryMixin

RWSPH_CLASSID = 0x80000000  # Class
RWSPH_INSTANCEID = 0x40000000  # Entity ID
RWSPH_CREATECLASSID = 0x20000000  # Behavior


@dataclass
class RW_sf_CreateEntity_Attribute_TFBReference:
    index: int = field(default=-1)
    guid: uuid.UUID = field(default=uuid.UUID(int=0))
    name: str | None = field(default=None)

    def resolveSoft(
        self, stream: "StreamQueryMixin"
    ) -> "RW_sf_CreateEntity | RW_sf_LoadEmbeddedAsset | None":
        """Resolve the reference to an embedded asset or entity if possible, else returns None"""
        return stream.assetByIDSoft(self.guid) or stream.entityByIDSoft(self.guid)

    def resolve(
        self, stream: "StreamQueryMixin"
    ) -> "RW_sf_CreateEntity | RW_sf_LoadEmbeddedAsset":
        """Resolves the reference to a RW_sf_LoadEmbeddedAsset or RW_sf_CreateEntity, raises if none matches"""
        found = self.resolveSoft(stream)
        if not found:
            raise AssertionError(
                f"No entity or asset in this stream with the id: {self.guid}"
            )
        return found


@dataclass
class RW_sf_CreateEntity_Attribute:
    command: int
    data: bytes = b""

    def setString(self, content: str) -> None:
        data = content.encode("latin1") + b"\x00"
        data += b"\xbf" * (-len(data) % 4)  # Align to 4
        self.data = data

    def asString(self) -> str:
        return self.data.split(b"\x00", 1)[0].decode("latin1")

    def asTfbRef(self) -> RW_sf_CreateEntity_Attribute_TFBReference:
        """Decode this attribute into a reference.

        A snapshot, not a view -- editing the result does not touch the
        attribute.  Pass one back to `setTfbRef` to store it, or go through
        the `CProtoActor.setModelRef` / `setScriptRef` helpers.
        """
        parser = Parser(self.data)
        index = parser.readInt32()  # -1 = None

        guid_string = parser.readString(
            38
        )  # { + 32 bytes guid + 4 seperator bytes + } = 38 bytes
        guid = uuid.UUID(guid_string)

        parser.skip(2)  # Two spaces as seperators

        name = None
        if parser.remaining() > 0:
            name = parser.readPaddedCString()

        return RW_sf_CreateEntity_Attribute_TFBReference(index, guid, name)

    def setTfbRef(self, ref: RW_sf_CreateEntity_Attribute_TFBReference) -> None:
        buf = io.BytesIO()

        write_s32(buf, ref.index)  # -1 = None

        guid_string = "{" + str(ref.guid).upper() + "}"
        buf.write(guid_string.encode("latin1"))

        buf.write(b"  ")  # Two spaces as seperators

        if ref.name is not None:
            write_alignedString(buf, ref.name)

        self.data = buf.getvalue()


@dataclass
class RW_sf_CreateEntity_AttributeClass:
    class_name: str = ""
    attributes: list[RW_sf_CreateEntity_Attribute] = field(default_factory=list)

    def find_first_attribute(self, command: int) -> RW_sf_CreateEntity_Attribute | None:
        for attr in self.attributes:
            if attr.command == command:
                return attr
        return None

    def find_all_attributes(self, command: int) -> list[RW_sf_CreateEntity_Attribute]:
        return [attr for attr in self.attributes if attr.command == command]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "class_name": self.class_name,
            "attributes": [],
        }

        for attr in self.attributes:
            attr_dict = {
                "command": attr.command,
                "data": attr.data.hex(),
            }

            if self.class_name == "LevelHub" and attr.command == 1:
                attr_dict["_READONLY_LevelHub_cmd1_VALUE"] = int.from_bytes(
                    attr.data[:4], byteorder="little"
                )
                attr_dict["_READONLY_LevelHub_cmd1_TAG"] = "0x" + attr.data[4:8].hex()
                attr_dict["_READONLY_LevelHub_cmd1_NAME"] = (
                    attr.data[8:]
                    .decode("latin1", errors="replace")
                    .replace("\00", "")
                    .replace("\xbf", "")
                )

            out["attributes"].append(attr_dict)

        return out


@dataclass
class RW_sf_CreateEntity(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    behaviour: str = ""
    entityID: uuid.UUID = field(default=uuid.UUID(int=0))
    isGlobal: bool = False

    classes: list[RW_sf_CreateEntity_AttributeClass] = field(default_factory=list)

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_sf_CreateEntity":
        entity = cls()

        entity.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            entity.header,
            strfunc_func.sf_CreateEntity.value,
            "RW_sf_CreateEntity chunk type",
        )

        subparser = Parser(parser.readBytes(entity.header.size), endian="little")
        entity.isGlobal = subparser.readBool()

        current_class = None

        while subparser.canRead(4):
            packet_size = subparser.readUint32()
            if packet_size == 0:
                break

            command = subparser.readUint32()
            data_size = packet_size - 8

            if command == RWSPH_CLASSID:
                current_class = RW_sf_CreateEntity_AttributeClass(
                    class_name=subparser.readPaddedCString()
                )
                entity.classes.append(current_class)
                continue

            if command == RWSPH_INSTANCEID:
                entity.entityID = uuid.UUID(bytes_le=subparser.readBytes(16))
                continue

            if command == RWSPH_CREATECLASSID:
                entity.behaviour = subparser.readPaddedCString()
                continue

            if current_class is None:
                raise ValueError(
                    f"Attribute with command {command} found outside of a class"
                )

            current_class.attributes.append(
                RW_sf_CreateEntity_Attribute(
                    command=command,
                    data=subparser.readBytes(data_size),
                )
            )

        return entity

    @override
    def write(self, f, stamp):
        buf = io.BytesIO()

        write_bool(buf, self.isGlobal)

        # Behaviour (CreateClassID)
        if self.behaviour:
            behaviour_buf = io.BytesIO()
            write_alignedString(behaviour_buf, self.behaviour)
            behaviour_data = behaviour_buf.getvalue()

            write_u32(buf, len(behaviour_data) + 8)
            write_u32(buf, RWSPH_CREATECLASSID)
            buf.write(behaviour_data)

        # Entity UUID (InstanceID)
        if self.entityID.int != 0:
            write_u32(buf, 16 + 8)
            write_u32(buf, v=RWSPH_INSTANCEID)
            buf.write(self.entityID.bytes_le)

        # Classes and attributes
        for cls in self.classes:
            class_buf = io.BytesIO()
            write_alignedString(class_buf, cls.class_name)
            class_data = class_buf.getvalue()

            write_u32(buf, len(class_data) + 8)
            write_u32(buf, RWSPH_CLASSID)
            buf.write(class_data)

            for attr in cls.attributes:
                write_u32(buf, len(attr.data) + 8)
                write_u32(buf, attr.command)
                buf.write(attr.data)

        write_u32(buf, 0)  # because rw wants it
        write_u32(buf, 0)  # because rw wants it

        rw_header = RWHeader(
            type=strfunc_func.sf_CreateEntity.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def find_first_class(
        self, class_name: str
    ) -> RW_sf_CreateEntity_AttributeClass | None:
        for cls in self.classes:
            if cls.class_name == class_name:
                return cls
        return None

    def find_first_class_with_command(
        self, class_name: str, command: int
    ) -> RW_sf_CreateEntity_AttributeClass | None:
        for cls in self.classes:
            if cls.class_name == class_name:
                for attr in cls.attributes:
                    if attr.command == command:
                        return cls
        return None

    def duplicate(self) -> "RW_sf_CreateEntity":
        return copy.deepcopy(self)

    @property
    @override
    def streamfunc(self):
        return strfunc_func.sf_CreateEntity

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "behaviour": self.behaviour,
            "entityID": str(self.entityID),
            "isGlobal": self.isGlobal,
            "classes": [cls.to_dict() for cls in self.classes],
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        header = RWHeader.from_dict(content.get("header", {}))

        return cls(
            header=header,
            behaviour=content.get("behaviour", ""),
            entityID=uuid.UUID(
                content.get("entityID", "00000000-0000-0000-0000-000000000000")
            ),
            isGlobal=content.get("isGlobal", False),
            classes=[
                RW_sf_CreateEntity_AttributeClass(
                    class_name=cls.get("class_name", ""),
                    attributes=[
                        RW_sf_CreateEntity_Attribute(
                            command=attr.get("command", 0),
                            data=bytes.fromhex(attr.get("data", "")),
                        )
                        for attr in cls.get("attributes", [])
                    ],
                )
                for cls in content.get("classes", [])
            ],
        )

    def setAttribute(self, class_name: str, command: int, data: bytes) -> None:
        attr = self.getAttribute(class_name, command)
        attr.data = data

    def getAttributeSoft(
        self, class_name: str, command: int
    ) -> RW_sf_CreateEntity_Attribute | None:
        """Returns the first instace of a Classes command, for multiple attributes use getAttributes. Returns None if attribute isnt found"""
        for cls in self.classes:
            if cls.class_name != class_name:
                continue

            for attr in cls.attributes:
                if attr.command == command:
                    return attr

        return None

    def getAttribute(
        self, class_name: str, command: int
    ) -> RW_sf_CreateEntity_Attribute:
        """Returns the first instace of a Classes command, for multiple attributes use getAttributes. Raises if not found"""
        attr = self.getAttributeSoft(class_name, command)
        if attr is None:
            raise ValueError(
                "No matching class/attribute in entity "
                + f"with the name: {class_name}, and command: {command}"
            )
        return attr

    def getAttributeOrCreate(
        self, class_name: str, command: int, default_data: bytes = b""
    ) -> RW_sf_CreateEntity_Attribute:
        """Returns the first instace of a Classes command, for multiple attributes use getAttributes. If no attribute was found it gets created with default data."""
        attr = self.getAttributeSoft(class_name, command)
        if attr is None:
            attr = self.addAttribute(class_name, command, default_data)

        return attr

    def getAttributes(
        self, class_name: str, command: int
    ) -> list[RW_sf_CreateEntity_Attribute]:
        """Return all attributes matching the class name and command."""
        for cls in self.classes:
            if cls.class_name != class_name:
                continue

            return [attr for attr in cls.attributes if attr.command == command]

        raise ValueError(f"No matching class in entity with the name: {class_name}")

    def addAttribute(
        self, class_name: str, command: int, data: bytes
    ) -> RW_sf_CreateEntity_Attribute:
        """Adds an attribute to a specific class in the entity. Adds the class too if needed."""
        # First make the attribute
        attr = RW_sf_CreateEntity_Attribute(
            command,
            data,
        )

        # Next find the class to add the attribute to, or create it
        target_cls = next(
            (cls for cls in self.classes if cls.class_name == class_name), None
        )
        if (
            target_cls is None
        ):  # The class doesnt exist yet on the entity, so add it first
            target_cls = RW_sf_CreateEntity_AttributeClass(class_name)
            self.classes.append(target_cls)

        # Add attribute to class
        target_cls.attributes.append(attr)

        return attr

    def hasAttribute(self, class_name: str, command: int) -> bool:
        for cls in self.classes:
            if cls.class_name != class_name:
                continue

            for attr in cls.attributes:
                if attr.command == command:
                    return True

        return False

    def hasTransform(self) -> bool:
        return self.hasAttribute(
            "CSystemCommands",
            0x01,
        )

    def translate(self, x: float, y: float, z: float):
        attr = self.getAttribute(
            "CSystemCommands",
            0x01,
        )

        matrix = RW_Matrix4x4.read(Parser(attr.data))
        matrix.translate(x, y, z)

        self.setAttribute(
            "CSystemCommands",
            0x01,
            matrix.pack(),
        )

    def getMatrix(self) -> RW_Matrix4x4:
        attr = self.getAttribute(
            "CSystemCommands",
            0x01,
        )
        return RW_Matrix4x4.read(Parser(attr.data))

    def setMatrix(self, matrix: RW_Matrix4x4):
        self.setAttribute(
            "CSystemCommands",
            0x01,
            matrix.pack(),
        )

    def setTranslation(self, x: float, y: float, z: float):
        matrix = self.getMatrix()
        matrix.row4.x = x
        matrix.row4.y = y
        matrix.row4.z = z
        self.setMatrix(matrix)

    def setRotation(self, x: float, y: float, z: float):
        """Replace the rotation basis (rows 1-3) from Euler angles in degrees,
        applied in X, then Y, then Z order. Preserves position (row4)."""
        rx, ry, rz = math.radians(x), math.radians(y), math.radians(z)

        def matmul3(a, b):
            return tuple(
                tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
                for i in range(3)
            )

        mx = (
            (1.0, 0.0, 0.0),
            (0.0, math.cos(rx), math.sin(rx)),
            (0.0, -math.sin(rx), math.cos(rx)),
        )
        my = (
            (math.cos(ry), 0.0, -math.sin(ry)),
            (0.0, 1.0, 0.0),
            (math.sin(ry), 0.0, math.cos(ry)),
        )
        mz = (
            (math.cos(rz), math.sin(rz), 0.0),
            (-math.sin(rz), math.cos(rz), 0.0),
            (0.0, 0.0, 1.0),
        )

        right, up, forward = matmul3(matmul3(mx, my), mz)

        matrix = self.getMatrix()
        matrix.row1.x, matrix.row1.y, matrix.row1.z = right
        matrix.row2.x, matrix.row2.y, matrix.row2.z = up
        matrix.row3.x, matrix.row3.y, matrix.row3.z = forward

        self.setMatrix(matrix)

    def getRotation(self) -> tuple[float, float, float]:
        """Decompose the rotation basis (rows 1-3) back into Euler degrees --
        the inverse of `setRotation` (X, then Y, then Z order)."""
        matrix = self.getMatrix()
        m00, m01, m02 = matrix.row1.x, matrix.row1.y, matrix.row1.z
        m12, m22 = matrix.row2.z, matrix.row3.z

        ry = math.asin(max(-1.0, min(1.0, -m02)))
        rx = math.atan2(m12, m22)
        rz = math.atan2(m01, m00)

        return math.degrees(rx), math.degrees(ry), math.degrees(rz)

    def lookAt(
        self,
        x: float,
        y: float,
        z: float,
        lock_yaw: bool = False,
        lock_pitch: bool = False,
        lock_roll: bool = False,
    ) -> None:
        """Face this entity toward a world-space point.

        Yaw (turn left/right) and pitch (tilt up/down) come from the
        direction to the target. Roll can't be derived from a single point,
        so it defaults to 0 (level). Pass lock_yaw / lock_pitch / lock_roll
        to leave that axis at whatever rotation the entity already had
        instead of overwriting it -- e.g. lock_pitch=True keeps an actor
        level while it still turns to face the target horizontally.
        """
        ex, ey, ez = self.getTranslation()
        dx, dy, dz = x - ex, y - ey, z - ez
        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            return

        cur_x, cur_y, cur_z = self.getRotation()
        horizontal = math.hypot(dx, dz)

        pitch_deg = cur_x if lock_pitch else math.degrees(math.atan2(dy, horizontal))
        yaw_deg = cur_y if lock_yaw else math.degrees(math.atan2(dx, dz))
        roll_deg = cur_z if lock_roll else 0.0

        self.setRotation(pitch_deg, yaw_deg, roll_deg)

    def setScale(self, x: float, y: float, z: float):
        matrix = self.getMatrix()

        # Preserve rotation, replace scale
        row1_length = (matrix.row1.x**2 + matrix.row1.y**2 + matrix.row1.z**2) ** 0.5
        row2_length = (matrix.row2.x**2 + matrix.row2.y**2 + matrix.row2.z**2) ** 0.5
        row3_length = (matrix.row3.x**2 + matrix.row3.y**2 + matrix.row3.z**2) ** 0.5

        matrix.row1.x *= x / row1_length
        matrix.row1.y *= x / row1_length
        matrix.row1.z *= x / row1_length

        matrix.row2.x *= y / row2_length
        matrix.row2.y *= y / row2_length
        matrix.row2.z *= y / row2_length

        matrix.row3.x *= z / row3_length
        matrix.row3.y *= z / row3_length
        matrix.row3.z *= z / row3_length

        self.setMatrix(matrix)

    def getTranslation(self):
        attr = self.getAttribute(
            "CSystemCommands",
            0x01,
        )
        matrix = RW_Matrix4x4.read(Parser(attr.data))
        return (
            matrix.row4.x,
            matrix.row4.y,
            matrix.row4.z,
        )

    def print_matrix(self):
        attr = self.getAttribute(
            "CSystemCommands",
            0x01,
        )

        matrix = RW_Matrix4x4.read(Parser(attr.data))
        print(matrix)

    def setRandomEntityId(self):
        self.entityID = uuid.uuid4()

    def tfbSetName(self, name: str):
        self.getAttribute("CTFBCommand", 0x0).setString(name)

        if self.behaviour == "CTFBModel":
            self.getAttribute("CTFBModel", 0x0).setString(name)
        elif self.behaviour == "CProtoActor":
            self.getAttribute("CProtoActor", 0x0).setString(name)
        elif self.behaviour == "SpriteObject":
            self.getAttribute("SpriteObject", 0x0).setString(name)
        elif self.behaviour == "CTFBSound":
            self.getAttribute("CTFBSound", 0x0).setString(name)
        elif self.behaviour == "CameraData":
            self.getAttribute("CameraData", 0x0).setString(name)

    def tfbGetName(self) -> str:
        """Get object name from CTFBCommand"""
        data = self.getAttribute("CTFBCommand", 0x0).data
        data = data.replace(b"\xbf", b"").rstrip(b"\x00")
        return data.decode("latin1")
