import hashlib
import json
from pathlib import Path

import pytest
from coincurve import PrivateKey

from ... import nip44

# Official vectors: https://github.com/paulmillr/nip44 (nip44.vectors.json)
VECTORS = json.loads((Path(__file__).parent / "nip44.vectors.json").read_text())["v2"]
h = bytes.fromhex


def _xonly(sec: str) -> bytes:
    return PrivateKey(h(sec)).public_key_xonly.format()


@pytest.mark.parametrize("v", VECTORS["valid"]["get_conversation_key"])
def test_conversation_key(v):
    key = nip44.get_conversation_key(h(v["sec1"]), h(v["pub2"]))
    assert key.hex() == v["conversation_key"]


@pytest.mark.parametrize("v", VECTORS["valid"]["get_message_keys"]["keys"])
def test_message_keys(v):
    conv = h(VECTORS["valid"]["get_message_keys"]["conversation_key"])
    chacha_key, chacha_nonce, hmac_key = nip44.get_message_keys(conv, h(v["nonce"]))
    assert chacha_key.hex() == v["chacha_key"]
    assert chacha_nonce.hex() == v["chacha_nonce"]
    assert hmac_key.hex() == v["hmac_key"]


@pytest.mark.parametrize("v", VECTORS["valid"]["calc_padded_len"])
def test_calc_padded_len(v):
    assert nip44.calc_padded_len(v[0]) == v[1]


@pytest.mark.parametrize("v", VECTORS["valid"]["encrypt_decrypt"])
def test_encrypt_decrypt(v):
    conv = nip44.get_conversation_key(h(v["sec1"]), _xonly(v["sec2"]))
    assert conv.hex() == v["conversation_key"]
    assert nip44.get_conversation_key(h(v["sec2"]), _xonly(v["sec1"])) == conv
    assert nip44.encrypt(v["plaintext"], conv, h(v["nonce"])) == v["payload"]
    assert nip44.decrypt(v["payload"], conv) == v["plaintext"]


@pytest.mark.parametrize("v", VECTORS["valid"]["encrypt_decrypt_long_msg"])
def test_encrypt_decrypt_long_msg(v):
    plaintext = v["pattern"] * v["repeat"]
    assert hashlib.sha256(plaintext.encode()).hexdigest() == v["plaintext_sha256"]
    payload = nip44.encrypt(plaintext, h(v["conversation_key"]), h(v["nonce"]))
    assert hashlib.sha256(payload.encode()).hexdigest() == v["payload_sha256"]
    assert nip44.decrypt(payload, h(v["conversation_key"])) == plaintext


@pytest.mark.parametrize("length", VECTORS["invalid"]["encrypt_msg_lengths"])
def test_invalid_msg_lengths(length):
    with pytest.raises(nip44.Nip44Error):
        nip44.encrypt("a" * length, b"\x01" * 32)


@pytest.mark.parametrize("v", VECTORS["invalid"]["get_conversation_key"])
def test_invalid_conversation_key(v):
    with pytest.raises(nip44.Nip44Error):
        nip44.get_conversation_key(h(v["sec1"]), h(v["pub2"]))


@pytest.mark.parametrize("v", VECTORS["invalid"]["decrypt"])
def test_invalid_decrypt(v):
    with pytest.raises(nip44.Nip44Error):
        nip44.decrypt(v["payload"], h(v["conversation_key"]))


def test_is_nip04_payload():
    conv = b"\x01" * 32
    assert not nip44.is_nip04_payload(nip44.encrypt("hello", conv))
    assert nip44.is_nip04_payload("aGVsbG8=?iv=AAAAAAAAAAAAAAAAAAAAAA==")
