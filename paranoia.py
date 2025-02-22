# Run-time hardening to detect unexpected inputs at the edges
from loguru import logger

ENABLE_HARDENING = True

def panic(reason:str):
    if not ENABLE_HARDENING:
        return
    logger.error(f"hardening:  {reason}")
    raise ValueError(f"hardening:  {reason}")
    
# Throw if string contains any non-printable characters
def assert_printable(v:str):
    if not ENABLE_HARDENING:
        return
    if not isinstance(v, str):
        panic("not a string "+str(v))
    if not v.isprintable():
        panic("string contains non-printable characters")
    
# Check if number is valid int and not NaN
def assert_valid_int(v:int):
    if not ENABLE_HARDENING:
        return
    if not isinstance(v, int):
        panic("number is not a valid int")
    
# Check if number is valid positive int
def assert_valid_positive_int(v:int):
    if not ENABLE_HARDENING:
        return
    assert_valid_int(v)
    if v < 0:
        panic("number is not positive")
    
# Check if number is a valid sats amount
def assert_valid_sats(v:int):
    if not ENABLE_HARDENING:
        return
    assert_valid_positive_int(v)
    max_sats_value = 10_000_000 
    if v >= max_sats_value:
        panic("sats amount looks too high")
    
# Check if number is a valid msats amount
def assert_valid_msats(v:int):
    if not ENABLE_HARDENING:
        return
    assert_valid_positive_int(v)
    max_msats_value = 10_000_000 * 1000
    if v >= max_msats_value:
        panic("msats amount looks too high")
    

# Check if string is a valid sha256 hash
def assert_valid_sha256(v:str):
    if not ENABLE_HARDENING:
        return
    assert_printable(v)
    if len(v) != 64 or not all(c in "0123456789abcdef" for c in v):
        panic("string is not a valid sha256 hash")

# Check if value is an hash of an unexpected input (eg. empty strings, booleans etc)
def assert_no_badhash(v:str):
    bad_hashes = [
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # empty string
        "36a9e7f1c95b82ffb99743e0c5c4ce95d83c9a430aac59f84ef3cbfab6145068", # 1 space string
        "c1c4b7fbd3e146bb14ec6258e5231c1ec703590721ff1e321b179a62b5857c9c", # None
        "cdca0b9bb2325fc8ed7eba7734a3a1f876d919221399b6587ae7d26305adee9d", # True
        "f9e08f8b038b1b401497f17da3adc120667ac742bf035657869a6ca1cd180e69", # False
    ]
    if v in bad_hashes:
        panic("bad hash detected")
    
# Check if valid nostr pubkey
def assert_valid_pubkey(v:str):
    if not ENABLE_HARDENING:
        return
    assert_valid_sha256(v)
    assert_no_badhash(v)
    

# Check if valid wallet id
def assert_valid_wallet_id(v:str):
    if not ENABLE_HARDENING:
        return
    assert_printable(v)
    if not v.isalnum():
        panic("string is not a valid wallet id")


# Check if valid timestamp in seconds
def assert_valid_timestamp_seconds(v:int):
    if not ENABLE_HARDENING:
        return
    assert_valid_positive_int(v)
    if v > 2**31:
        panic("timestamp is too high")


# Check if valid expiration in seconds
def assert_valid_expiration_seconds(v: int):
    if not ENABLE_HARDENING:
        return
    assert_valid_int(v)
    if v == -1:
        return
    if v < 0:
        panic("expiration is invalid")
    if v > 2**31:
        panic("expiration is too high")


# Check if string is within sane parameters
def assert_sane_string(v:str):
    if not ENABLE_HARDENING:
        return
    assert_printable(v)
    if len(v) > 1024:
        panic("string is too long")
    

# Check if string is a non-empty string
def assert_non_empty_string(v:str):
    if not ENABLE_HARDENING:
        return
    assert_printable(v)
    if len(v.strip()) == 0:
        panic("string is empty")
    
# Assert valid json
def assert_valid_json(v:str):
    if not ENABLE_HARDENING:
        return
    assert_non_empty_string(v)
    try:
        import json
        json.loads(v)
    except:
        panic("string is not valid json")

# Check if string is a valid bolt11 invoice
def assert_valid_bolt11(invoice:str):
    if not ENABLE_HARDENING:
        return
    assert_printable(invoice)
    
