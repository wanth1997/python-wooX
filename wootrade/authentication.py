import hashlib
import hmac


def signature(msg, secret):
    key_bytes = bytes(secret, "utf-8")
    data_bytes = bytes(msg, "utf-8")
    return hmac.new(key_bytes, data_bytes, hashlib.sha256).hexdigest()
