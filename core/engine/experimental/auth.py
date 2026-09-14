import os


_SECRET_KEY = os.environ.get("SIMORGH_KEY")


def verify_token(token: str) -> bool:
    """Verify a token only when an explicit secret is configured.

    SIMORGH must never ship with a usable default authentication secret.
    """
    if not _SECRET_KEY:
        return False
    return token == _SECRET_KEY
