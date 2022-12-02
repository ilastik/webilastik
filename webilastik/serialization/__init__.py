class BadUtf8DataException(Exception):
    pass

def decode_as_utf8(data: bytes) -> "str | BadUtf8DataException":
    try:
        return data.decode("utf8")
    except Exception:
        return BadUtf8DataException()