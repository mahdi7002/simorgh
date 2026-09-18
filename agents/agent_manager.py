from agents.hakim import HakimAgent
from agents.nazer import NazerAgent
from agents.rahbar import RahbarAgent
from core.database_answer import build_database_answer
import logging

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        self.hakim = HakimAgent()
        self.nazer = NazerAgent()
        self.rahbar = RahbarAgent()
        logger.info("Agent Manager initialized")

    def consult(self, goal: str, obstacle: str, cause: str, query: str, *, return_metadata: bool = False):
        responses = []
        ai_generated = False

        if obstacle or cause:
            why_response = self.hakim.analyze(cause, obstacle)
            if why_response:
                responses.append(f"🔍 چرا: {why_response}")
                ai_generated = True

        if obstacle:
            what_response = self.nazer.analyze(obstacle, query)
            if what_response:
                responses.append(f"📌 چه اتفاقی افتاد: {what_response}")
                ai_generated = True

        if goal or obstacle:
            how_response = self.rahbar.suggest(goal, obstacle, cause)
            if how_response:
                responses.append(f"🎯 چه کاری انجام دهیم: {how_response}")
                ai_generated = True

        if responses:
            result = "\n".join(responses)
        else:
            result, _sources = build_database_answer(query)

        if return_metadata:
            return result, ai_generated
        return result
