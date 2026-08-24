import logging
from core.identity import ROLE_PROMPTS
from core.llm_local import generate

logger = logging.getLogger(__name__)


class HakimAgent:
    def __init__(self):
        logger.info(f"{HakimAgent} initialized")

    def analyze(self, *args, **kwargs):
        query = args[0] if args else "وضعیت فعلی"
        response = generate(ROLE_PROMPTS["hakim"], query)
        if response:
            return response
        return f"تحلیل {query} توسط عامل Hakim"

    def suggest(self, *args, **kwargs):
        return self.analyze(*args, **kwargs)
