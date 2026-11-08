import copy
import io
import json
import struct
from pathlib import Path

import pytest

from madformats.lib.parser import Parser
from madformats.lib.rw_basics import RwBool
from madformats.lib.rwConstants import DEFAULT_VERSION_STAMP
from madformats.stream.file import RW_StreamFile
from madformats.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity


def _write(entity: RW_sf_CreateEntity) -> bytes:
    buf = io.BytesIO()
    entity.write(buf, DEFAULT_VERSION_STAMP)
    return buf.getvalue()


def _stored(chunk: bytes) -> int:
    """The u32 right after the 12 byte chunk header."""
    return struct.unpack_from("<I", chunk, 12)[0]


@pytest.mark.parametrize("raw", [0, 1, 2, 0xFFFFFFFF])
def test_entity_keeps_raw_value_through_binary(raw: int) -> None:
    chunk = _write(RW_sf_CreateEntity(isGlobal=RwBool(raw)))

    assert _stored(chunk) == raw
    assert _write(RW_sf_CreateEntity.read(Parser(chunk, endian="little"))) == chunk


@pytest.mark.parametrize("raw", [0, 1, 0xFFFFFFFF])
def test_entity_keeps_raw_value_through_json(raw: int) -> None:
    content = json.loads(json.dumps(RW_sf_CreateEntity(isGlobal=RwBool(raw)).to_dict()))

    assert _stored(_write(RW_sf_CreateEntity.from_dict(content))) == raw


@pytest.mark.parametrize(("value", "raw"), [(False, 0), (True, 1)])
def test_entity_accepts_plain_bools(value: bool, raw: int) -> None:
    entity = RW_sf_CreateEntity()
    entity.isGlobal = value

    assert _stored(_write(entity)) == raw


def test_entity_defaults_to_false() -> None:
    assert not RW_sf_CreateEntity().isGlobal


def test_comparisons_use_truth_value_in_both_directions() -> None:
    all_bits = RwBool(0xFFFFFFFF)

    assert all_bits == True
    assert all_bits == True
    assert all_bits == RwBool(1)
    assert all_bits == RwBool(1)
    assert all_bits != RwBool(0)
    assert hash(all_bits) == hash(True)


def test_negative_input_maps_to_u32() -> None:
    assert RwBool(-1).raw == 0xFFFFFFFF


def test_text_shows_raw_value_only_when_unusual() -> None:
    assert f"{RwBool(0)}" == "False"
    assert f"{RwBool(1)}" == "True"
    assert f"{RwBool(0xFFFFFFFF)}" == "True (0xffffffff)"


def test_deepcopy_keeps_raw_value() -> None:
    assert copy.deepcopy(RwBool(0xFFFFFFFF)).raw == 0xFFFFFFFF


@pytest.mark.gamedata
def test_every_stock_level_round_trips(levels_dir: Path) -> None:
    for path in sorted(levels_dir.glob("*.stream")):
        data = path.read_bytes()
        stamp = struct.unpack_from("<I", data, 8)[0]
        stream = RW_StreamFile.read(Parser(data, endian="little"))

        assert stream.toBytes(stamp) == data, path.name
