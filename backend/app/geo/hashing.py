import hashlib

from app.config import settings


def hash_ip(ip: str) -> str:
    if not settings.ip_hash_salt:
        raise RuntimeError("IP_HASH_SALT is not set — refusing to hash IPs with an empty salt")
    return hashlib.sha256(f"{ip}{settings.ip_hash_salt}".encode()).hexdigest()
