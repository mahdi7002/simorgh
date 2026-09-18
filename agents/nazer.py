import logging
from core.identity import ROLE_PROMPTS
from core.llm_local import generate

logger = logging.getLogger(__name__)


class NazerAgent:
    def __init__(self):
        logger.info(f"{NazerAgent} initialized")

    def analyze(self, *args, **kwargs):
        query = args[0] if args else "وضعیت فعلی"
        response = generate(ROLE_PROMPTS["nazer"], query)
        if response:
            return response
        logger.warning("NazerAgent model unavailable")
        return None

    def suggest(self, *args, **kwargs):
        return self.analyze(*args, **kwargs)
