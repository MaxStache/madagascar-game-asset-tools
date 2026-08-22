import copy
import io
from dataclasses import dataclass, field
from typing import Any, override
import uuid

from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_alignedString, write_u32, write_bool
from madagascar.lib.rwConstants import strfunc_func
from madagascar.lib.rw_basics import (
    RW_Matrix4x4,
    RW_StreamFunc,
    RWHeader,
    expect_chunk_type_or_raise,
)

RWSPH_CLASSID = 0x80000000  # Class
RWSPH_INSTANCEID = 0x40000000  # Entity ID
RWSPH_CREATECLASSID = 0x20000000  # Behavior


@dataclass
class RW_sf_CreateEntity_Attribute:
    command: int
    data: bytes = b""

    def setString(self, content: str) -> None:
        data = content.encode("latin1") + b"\x00"
        data += b"\xbf" * (-len(data) % 4)  # Align to 4
        self.data = data


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
        return {
            "class_name": self.class_name,
            "attributes": [
                {"command": attr.command, "data": attr.data.hex()}
                for attr in self.attributes
            ],
        }


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

    def getAttribute(
        self, class_name: str, command: int
    ) -> RW_sf_CreateEntity_Attribute:
        for cls in self.classes:
            if cls.class_name != class_name:
                continue

            for attr in cls.attributes:
                if attr.command == command:
                    return attr

        raise ValueError(
            "No matching class/attribute in entity "
            + f"with the name: {class_name}, and command: {command}"
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
