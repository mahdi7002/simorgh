from . import memory_graph

def find_cause(user_text):
    if "چرا" in user_text:
        rest = user_text.replace("چرا", "").strip()
        subject = rest.split()[0] if rest else rest
        cause_text = memory_graph.query_cause_graph(subject)
        if cause_text:
            return cause_text
        cause_text = memory_graph.query_cause_graph(rest)
        if cause_text:
            return cause_text
        return "علت در حافظه یافت نشد، نیاز به استدلال داریم."
    return ""
