import os
import time
import uuid


def generate_uuid7() -> str:
    """Generate RFC 9562 compliant UUID v7."""
    timestamp_ms = int(time.time() * 1000)
    random_bytes = bytearray(os.urandom(10))

    uuid_bytes = bytearray(16)
    uuid_bytes[0:6] = timestamp_ms.to_bytes(6, byteorder='big')
    uuid_bytes[6:16] = random_bytes

    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80

    return str(uuid.UUID(bytes=bytes(uuid_bytes)))


def validate_uuid7(uuid_str: str) -> bool:
    """Validate UUID format."""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False

