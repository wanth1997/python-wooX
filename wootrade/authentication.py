import hashlib
import hmac


def signature(ts: str, secret: str, **kwargs):
    msg = ""
    sorted_arg = {key: value for key, value in sorted(kwargs.items())}
    for key, value in sorted_arg.items():
        if msg:
            msg += "&"
        msg += f"{key}={value}"
    msg += f"|{ts}"
    bytes_key = bytes(str(secret), "utf-8")
    bytes_msg = bytes(msg, "utf-8")
    signature = (
        hmac.new(bytes_key, msg=bytes_msg, digestmod=hashlib.sha256)
        .hexdigest()
        .upper()
    )
    return signature
