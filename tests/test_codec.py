"""Tests for CDAB codec."""

import pytest
from triton2.codec import (
    decode_float_cdab,
    encode_float_cdab,
    decode_uint32_cdab,
    decode_floats_cdab,
)


def test_decode_float_cdab_roundtrip():
    for value in [0.0, 1.0, -1.0, 3.14, 100.0, 1e-6]:
        words = encode_float_cdab(value)
        assert len(words) == 2
        decoded = decode_float_cdab(words)
        assert decoded == pytest.approx(value, rel=1e-6)


def test_decode_float_cdab_known():
    # 1.0 in IEEE 754 big-endian: 0x3F80_0000 -> words [0x3F80, 0x0000]
    words = [0x3F80, 0x0000]
    assert decode_float_cdab(words) == pytest.approx(1.0, rel=1e-6)


def test_encode_float_cdab_known():
    words = encode_float_cdab(1.0)
    assert words == [0x3F80, 0x0000]


def test_decode_float_cdab_insufficient_words():
    with pytest.raises(ValueError, match="at least 2 words"):
        decode_float_cdab([0x3F80])


def test_decode_uint32_cdab():
    # 0x0001_0002 -> high=0x0001, low=0x0002
    assert decode_uint32_cdab([1, 2]) == 0x00010002
    assert decode_uint32_cdab([0xFFFF, 0xFFFF]) == 0xFFFFFFFF


def test_decode_uint32_cdab_insufficient_words():
    with pytest.raises(ValueError, match="at least 2 words"):
        decode_uint32_cdab([1])


def test_decode_floats_cdab():
    # Four floats: 1.0, 2.0, 3.0, 4.0
    words = [0x3F80, 0x0000, 0x4000, 0x0000, 0x4040, 0x0000, 0x4080, 0x0000]
    out = decode_floats_cdab(words, 4)
    assert len(out) == 4
    assert out[0] == pytest.approx(1.0, rel=1e-6)
    assert out[1] == pytest.approx(2.0, rel=1e-6)
    assert out[2] == pytest.approx(3.0, rel=1e-6)
    assert out[3] == pytest.approx(4.0, rel=1e-6)


def test_decode_floats_cdab_partial():
    words = [0x3F80, 0x0000, 0x4000, 0x0000]
    out = decode_floats_cdab(words, 3)
    assert len(out) == 2  # only 2 complete floats
