import os
SECRET_KEY = os.environ.get("SIMORGH_KEY", "simorgh123")
def verify_token(token: str) -> bool:
    return token == SECRET_KEY
