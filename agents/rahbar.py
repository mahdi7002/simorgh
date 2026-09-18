import logging
from core.identity import ROLE_PROMPTS
from core.llm_local import generate

logger = logging.getLogger(__name__)


class RahbarAgent:
    def __init__(self):
        logger.info(f"{RahbarAgent} initialized")

    def suggest(self, *args, **kwargs):
        query = args[0] if args else "وضعیت فعلی"
        response = generate(ROLE_PROMPTS["rahbar"], query)
        if response:
            return response
        logger.warning("RahbarAgent model unavailable")
        return None

    def analyze(self, *args, **kwargs):
        return self.suggest(*args, **kwargs)
