"""
IEEE 754 float32 and uint32 codec for Modbus CDAB word order.
CDAB: first register = high 16 bits, second = low 16 bits (big-endian).
"""

import struct
from typing import List


def decode_float_cdab(words: List[int]) -> float:
    """Decode two 16-bit Modbus registers (CDAB order) to one float32."""
    if len(words) < 2:
        raise ValueError("Need at least 2 words for float32")
    high, low = words[0] & 0xFFFF, words[1] & 0xFFFF
    u32 = (high << 16) | low
    return struct.unpack(">f", u32.to_bytes(4, "big"))[0]


def encode_float_cdab(value: float) -> List[int]:
    """Encode one float32 to two 16-bit words in CDAB order."""
    b = struct.pack(">f", value)
    high = int.from_bytes(b[0:2], "big")
    low = int.from_bytes(b[2:4], "big")
    return [high, low]


def decode_uint32_cdab(words: List[int]) -> int:
    """Decode two 16-bit registers (high, low) to one uint32."""
    if len(words) < 2:
        raise ValueError("Need at least 2 words for uint32")
    high, low = words[0] & 0xFFFF, words[1] & 0xFFFF
    return (high << 16) | low


def decode_floats_cdab(words: List[int], count: int) -> List[float]:
    """Decode a contiguous block of float32 values (2 words each) in CDAB order."""
    out: List[float] = []
    for i in range(count):
        if 2 * (i + 1) > len(words):
            break
        out.append(decode_float_cdab(words[2 * i : 2 * i + 2]))
    return out
