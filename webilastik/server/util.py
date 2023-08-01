from base64 import urlsafe_b64decode as urlsafe_b64decode_padded


def urlsafe_b64decode(payload: str) -> "bytes | Exception":
    num_missing_bytes = 4 - (len(payload) % 4)
    payload = payload + (num_missing_bytes * "=")
    try:
        return urlsafe_b64decode_padded(payload)
    except Exception as e:
        return e