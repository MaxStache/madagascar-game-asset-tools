import io
from dataclasses import dataclass, field
from typing import Union
import uuid

from formats.lib.parser import Parser
from formats.lib.writer import _write_alignedString, _write_u32, _write_bool
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise

RWSPH_CLASSID = 0x80000000  # Class
RWSPH_INSTANCEID = 0x40000000  # Entity ID
RWSPH_CREATECLASSID = 0x20000000  # Behavior


@dataclass
class RW_sf_CreateEntity_Attribute:
    command: int
    data: bytes = b""


@dataclass
class RW_sf_CreateEntity_AttributeClass:
    class_name: str = ""
    attributes: list[RW_sf_CreateEntity_Attribute] = field(default_factory=list)

    def find_first_attribute(self, command: int) -> Union[bytes, None]:
        for attr in self.attributes:
            if attr.command == command:
                return attr
        return None

    def find_all_attributes(self, command: int) -> Union[bytes, None]:
        return [attr for attr in self.attributes if attr.command == command]


@dataclass
class RW_sf_CreateEntity(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    behaviour: str = ""
    entityID: uuid.UUID = uuid.UUID(int=0)
    isGlobal: bool = False

    classes: list[RW_sf_CreateEntity_AttributeClass] = field(default_factory=list)

    @staticmethod
    def read(parser: Parser) -> "RW_sf_CreateEntity":
        entity = RW_sf_CreateEntity()

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

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_bool(buf, this.isGlobal)

        # Behaviour (CreateClassID)
        if this.behaviour:
            behaviour_buf = io.BytesIO()
            _write_alignedString(behaviour_buf, this.behaviour)
            behaviour_data = behaviour_buf.getvalue()

            _write_u32(buf, len(behaviour_data) + 8)
            _write_u32(buf, RWSPH_CREATECLASSID)
            buf.write(behaviour_data)

        # Entity UUID (InstanceID)
        if this.entityID.int != 0:
            _write_u32(buf, 16 + 8)
            _write_u32(buf, v=RWSPH_INSTANCEID)
            buf.write(this.entityID.bytes_le)

        # Classes and attributes
        for cls in this.classes:
            class_buf = io.BytesIO()
            _write_alignedString(class_buf, cls.class_name)
            class_data = class_buf.getvalue()

            _write_u32(buf, len(class_data) + 8)
            _write_u32(buf, RWSPH_CLASSID)
            buf.write(class_data)

            for attr in cls.attributes:
                _write_u32(buf, len(attr.data) + 8)
                _write_u32(buf, attr.command)
                buf.write(attr.data)

        _write_u32(buf, 0) # because rw wants it
        _write_u32(buf, 0) # because rw wants it



        rw_header = RWHeader(
            type=strfunc_func.sf_CreateEntity.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def find_first_class(self, class_name: str) -> RW_sf_CreateEntity_AttributeClass:
        for cls in self.classes:
            if cls.class_name == class_name:
                return cls
        return None
    
    def find_first_class_with_command(self, class_name: str, command: int) -> RW_sf_CreateEntity_AttributeClass:
        for cls in self.classes:
            if cls.class_name == class_name:
                for attr in cls.attributes:
                    if attr.command == command:
                        return cls
        return None


    @property
    def streamfunc(self):
        return strfunc_func.sf_CreateEntity