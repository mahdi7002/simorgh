import os
import os
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    yaml = None
    _HAS_YAML = False
from . import simorgh_mirror

def load_agents():
    if not _HAS_YAML:
        raise RuntimeError("PyYAML is not installed (optional dependency)")
    agents = {}
    for f in os.listdir("agents"):
        if f.endswith(".yaml"):
            path = os.path.join("agents", f)
            with open(path) as file:
                agent = yaml.safe_load(file)
                agents[agent["name"]] = agent
    return agents

def deliberate(intent, context):
    agents = load_agents()
    answers = {}
    for name, agent in agents.items():
        for rule in agent.get("rules", []):
            if rule["condition"] == intent or (intent == "general" and rule["condition"] == "general"):
                try:
                    response = rule["response"].format(**context)
                except KeyError:
                    response = rule["response"]
                answers[name] = response
                break
    if answers:
        if context.get("emotion") == "دیده_شدن":
            return f"من کنارت هستم. {list(answers.values())[0]}"
        if intent == "general":
            archetype = simorgh_mirror.detect_archetype(context.get("understanding", ""))
            tone = simorgh_mirror.get_archetype_tone(archetype)
            return f"با نگاه {tone}: {list(answers.values())[0]}"
        return list(answers.values())[0]
    return "نیاز به LLM داریم."
