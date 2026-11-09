"""
NIP-44 v2 encryption (https://github.com/nostr-protocol/nips/blob/master/44.md).

Uses only libraries LNbits already ships with: coincurve (secp256k1 ECDH)
and cryptography (ChaCha20). HKDF and HMAC come from the standard library.
"""

import base64
import hashlib
import hmac
import secrets

from coincurve import PrivateKey as SecpPrivateKey
from coincurve import PublicKey as SecpPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

VERSION = 2
SALT = b"nip44-v2"
MIN_PLAINTEXT_SIZE = 1
MAX_PLAINTEXT_SIZE = 65535
# secp256k1 group order
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


class Nip44Error(ValueError):
    pass


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    out = b""
    block = b""
    counter = 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def get_conversation_key(private_key: bytes, public_key_xonly: bytes) -> bytes:
    """ECDH (unhashed shared x coordinate) + HKDF-extract with salt 'nip44-v2'."""
    if len(private_key) != 32:
        raise Nip44Error("invalid private key length")
    d = int.from_bytes(private_key, "big")
    if d == 0 or d >= _N:
        raise Nip44Error("invalid private key")
    if len(public_key_xonly) != 32:
        raise Nip44Error("invalid public key length")
    try:
        point = SecpPublicKey(b"\x02" + public_key_xonly)
        shared = point.multiply(SecpPrivateKey(private_key).secret)
    except Exception as e:
        raise Nip44Error("invalid public key") from e
    shared_x = shared.format(compressed=True)[1:33]
    return _hkdf_extract(SALT, shared_x)


def get_message_keys(
    conversation_key: bytes, nonce: bytes
) -> tuple[bytes, bytes, bytes]:
    if len(conversation_key) != 32:
        raise Nip44Error("invalid conversation key length")
    if len(nonce) != 32:
        raise Nip44Error("invalid nonce length")
    keys = _hkdf_expand(conversation_key, nonce, 76)
    return keys[0:32], keys[32:44], keys[44:76]


def calc_padded_len(unpadded_len: int) -> int:
    if unpadded_len <= 0:
        raise Nip44Error("expected positive integer")
    if unpadded_len <= 32:
        return 32
    next_power = 1 << ((unpadded_len - 1).bit_length())
    chunk = 32 if next_power <= 256 else next_power // 8
    return chunk * (((unpadded_len - 1) // chunk) + 1)


def _pad(plaintext: str) -> bytes:
    unpadded = plaintext.encode("utf-8")
    length = len(unpadded)
    if length < MIN_PLAINTEXT_SIZE or length > MAX_PLAINTEXT_SIZE:
        raise Nip44Error("invalid plaintext length")
    prefix = length.to_bytes(2, "big")
    suffix = b"\x00" * (calc_padded_len(length) - length)
    return prefix + unpadded + suffix


def _unpad(padded: bytes) -> str:
    length = int.from_bytes(padded[0:2], "big")
    unpadded = padded[2 : 2 + length]
    if (
        length < MIN_PLAINTEXT_SIZE
        or length > MAX_PLAINTEXT_SIZE
        or len(unpadded) != length
        or len(padded) != 2 + calc_padded_len(length)
    ):
        raise Nip44Error("invalid padding")
    try:
        return unpadded.decode("utf-8")
    except UnicodeDecodeError as e:
        raise Nip44Error("invalid utf-8 plaintext") from e


def _chacha20(key: bytes, nonce12: bytes, data: bytes) -> bytes:
    # cryptography's ChaCha20 takes a 16-byte nonce:
    # 4-byte little-endian counter (0) + the 12-byte NIP-44 nonce
    cipher = Cipher(algorithms.ChaCha20(key, b"\x00\x00\x00\x00" + nonce12), mode=None)
    return cipher.encryptor().update(data)


def _hmac_aad(key: bytes, message: bytes, aad: bytes) -> bytes:
    if len(aad) != 32:
        raise Nip44Error("AAD associated data must be 32 bytes")
    return hmac.new(key, aad + message, hashlib.sha256).digest()


def encrypt(plaintext: str, conversation_key: bytes, nonce: bytes | None = None) -> str:
    if nonce is None:
        nonce = secrets.token_bytes(32)
    chacha_key, chacha_nonce, hmac_key = get_message_keys(conversation_key, nonce)
    padded = _pad(plaintext)
    ciphertext = _chacha20(chacha_key, chacha_nonce, padded)
    mac = _hmac_aad(hmac_key, ciphertext, nonce)
    return base64.b64encode(bytes([VERSION]) + nonce + ciphertext + mac).decode()


def _decode_payload(payload: str) -> tuple[bytes, bytes, bytes]:
    plen = len(payload)
    if plen == 0 or payload[0] == "#":
        raise Nip44Error("unknown version")
    if plen < 132 or plen > 87472:
        raise Nip44Error("invalid payload size")
    try:
        data = base64.b64decode(payload, validate=True)
    except Exception as e:
        raise Nip44Error("invalid base64") from e
    dlen = len(data)
    if dlen < 99 or dlen > 65603:
        raise Nip44Error("invalid data size")
    if data[0] != VERSION:
        raise Nip44Error("unknown version " + str(data[0]))
    return data[1:33], data[33 : dlen - 32], data[dlen - 32 :]


def decrypt(payload: str, conversation_key: bytes) -> str:
    nonce, ciphertext, mac = _decode_payload(payload)
    chacha_key, chacha_nonce, hmac_key = get_message_keys(conversation_key, nonce)
    calculated_mac = _hmac_aad(hmac_key, ciphertext, nonce)
    if not hmac.compare_digest(calculated_mac, mac):
        raise Nip44Error("invalid MAC")
    padded = _chacha20(chacha_key, chacha_nonce, ciphertext)
    return _unpad(padded)


def is_nip04_payload(content: str) -> bool:
    """NIP-04 payloads are '<base64 ciphertext>?iv=<base64 iv>'."""
    return "?iv=" in content
