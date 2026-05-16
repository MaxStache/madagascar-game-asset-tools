import struct

_STEP_TABLE = [
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    16,
    17,
    19,
    21,
    23,
    25,
    28,
    31,
    34,
    37,
    41,
    45,
    50,
    55,
    60,
    66,
    73,
    80,
    88,
    97,
    107,
    118,
    130,
    143,
    157,
    173,
    190,
    209,
    230,
    253,
    279,
    307,
    337,
    371,
    408,
    449,
    494,
    544,
    598,
    658,
    724,
    796,
    876,
    963,
    1060,
    1166,
    1282,
    1411,
    1552,
    1707,
    1878,
    2066,
    2272,
    2499,
    2749,
    3024,
    3327,
    3660,
    4026,
    4428,
    4871,
    5358,
    5894,
    6484,
    7132,
    7845,
    8630,
    9493,
    10442,
    11487,
    12635,
    13899,
    15289,
    16818,
    18500,
    20350,
    22385,
    24623,
    27086,
    29794,
    32767,
]
_INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]


def _decode_nibble(nibble, pred, idx):
    step = _STEP_TABLE[idx]
    diff = step >> 3
    if nibble & 4:
        diff += step
    if nibble & 2:
        diff += step >> 1
    if nibble & 1:
        diff += step >> 2
    pred = pred - diff if (nibble & 8) else pred + diff
    pred = max(-32768, min(32767, pred))
    idx = max(0, min(88, idx + _INDEX_TABLE[nibble]))
    return pred, idx


def bytes_to_samples(data_bytes: int, channels: int) -> int:
    """Total individual PCM samples (all channels) for Xbox IMA ADPCM data."""
    block_align = 0x24 * channels
    if channels <= 0:
        return 0
    complete_blocks = data_bytes // block_align
    mod = data_bytes % block_align
    # Each block: 1 header sample + 63 nibble samples = 64 per channel (last nibble skipped)
    result = complete_blocks * (0x24 - 4) * 2 * channels
    if mod > 4 * channels:
        nibble_bytes = mod - 4 * channels
        nibble_samples = min(nibble_bytes * 2, (0x24 - 4) * 2 - 1) * channels
        result += channels + nibble_samples  # header samples + nibble samples
    elif mod >= 4 * channels:
        result += channels  # header samples only
    return result


def decode(data: bytes, channels: int, block_size: int) -> bytes:
    """Decode Xbox IMA ADPCM blocks to interleaved PCM16 bytes.

    Xbox IMA layout: each channel occupies a contiguous slice of the block
    (ch0 header + ch0 nibbles, then ch1 header + ch1 nibbles, ...).
    This differs from standard MS IMA which byte-interleaves channels.
    """
    all_samples = []
    offset = 0
    chan_block = block_size // channels

    while offset + block_size <= len(data):
        ch_samples = []
        for ch in range(channels):
            chan_off = offset + ch * chan_block
            pred, idx = struct.unpack_from("<hB", data, chan_off)
            idx = max(0, min(88, idx))
            samples = [pred]  # header predictor is sample 0
            total_nibbles = (chan_block - 4) * 2
            nibble_idx = 0
            for i in range(chan_block - 4):
                byte = data[chan_off + 4 + i]
                for nibble in (byte & 0xF, byte >> 4):
                    nibble_idx += 1
                    if nibble_idx == total_nibbles:  # skip last nibble slot
                        break
                    pred, idx = _decode_nibble(nibble, pred, idx)
                    samples.append(pred)
            ch_samples.append(samples)

        n = min(len(s) for s in ch_samples)
        for i in range(n):
            for ch in range(channels):
                all_samples.append(ch_samples[ch][i])

        offset += block_size

    return struct.pack(f"<{len(all_samples)}h", *all_samples)