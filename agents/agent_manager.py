from agents.hakim import HakimAgent
from agents.nazer import NazerAgent
from agents.rahbar import RahbarAgent
import logging

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        self.hakim = HakimAgent()
        self.nazer = NazerAgent()
        self.rahbar = RahbarAgent()
        logger.info("Agent Manager initialized")

    def consult(self, goal: str, obstacle: str, cause: str, query: str) -> str:
        responses = []

        if obstacle or cause:
            why_response = self.hakim.analyze(cause, obstacle)
            if why_response:
                responses.append(f"🔍 چرا: {why_response}")

        if obstacle:
            what_response = self.nazer.analyze(obstacle, query)
            if what_response:
                responses.append(f"📌 چه اتفاقی افتاد: {what_response}")

        if goal or obstacle:
            how_response = self.rahbar.suggest(goal, obstacle, cause)
            if how_response:
                responses.append(f"🎯 چه کاری انجام دهیم: {how_response}")

        if not responses:
            return "متوجه نشدم. لطفاً توضیح بیشتری بدهید."
        return "\n".join(responses)
