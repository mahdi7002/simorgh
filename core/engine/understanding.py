import re
from . import memory_graph

def extract_entities(text):
    entities = memory_graph.search_nodes_by_keyword(text)
    if not entities:
        for w in text.split():
            if len(w) > 2:
                res = memory_graph.search_nodes_by_keyword(w)
                for r in res:
                    if r not in entities:
                        entities.append(r)
    if not entities:
        devices = ["تلویزیون", "کولر", "لامپ", "پرینتر", "فر", "اینترنت", "کامپیوتر"]
        for d in devices:
            if d in text:
                entities.append({"name": d, "type": "device"})
    return entities

def find_goal_and_obstacle(text):
    entities = extract_entities(text)
    if not entities:
        return {"intent":"general","goal":"understand","obstacle":None,"description":text,"reasoning_path":[],"confidence":0.1}
    best, best_conf = None, 0.0
    for entity in entities:
        name = entity["name"]
        blocks = memory_graph.find_related_nodes(name, relation="Blocks", direction="incoming", max_depth=1)
        if blocks:
            obstacle = blocks[0]["source"]
            wants = memory_graph.find_related_nodes(name, relation="Wants", direction="outgoing", max_depth=2)
            if wants:
                goal = wants[0]["target"]
                path = [obstacle,"Blocks",name,"Wants",goal]
                deeper = memory_graph.find_related_nodes(goal, relation="Supports", direction="outgoing", max_depth=1)
                if deeper:
                    goal = deeper[0]["target"]
                    path += ["Supports", goal]
                conf = 0.7 if deeper else 0.5
                if len(path) > 4: conf -= 0.1
                if conf > best_conf:
                    best_conf = conf
                    best = {"intent":_guess_intent(goal),"goal":goal,"obstacle":obstacle,"description":text,"reasoning_path":path,"confidence":round(conf,2)}
            continue
        wants = memory_graph.find_related_nodes(name, relation="Wants", direction="outgoing", max_depth=2)
        if wants:
            goal = wants[0]["target"]
            path = [name,"Wants",goal]
            blocks_goal = memory_graph.find_related_nodes(goal, relation="Blocks", direction="incoming", max_depth=1)
            obstacle = blocks_goal[0]["source"] if blocks_goal else None
            if obstacle: path = [obstacle,"Blocks",goal] + path
            deeper = memory_graph.find_related_nodes(goal, relation="Supports", direction="outgoing", max_depth=1)
            if deeper:
                goal = deeper[0]["target"]
                path += ["Supports", goal]
            conf = 0.6 if obstacle else 0.4
            if len(path) > 5: conf -= 0.1
            if conf > best_conf:
                best_conf = conf
                best = {"intent":_guess_intent(goal),"goal":goal,"obstacle":obstacle,"description":text,"reasoning_path":path,"confidence":round(conf,2)}
    return best if best else {"intent":"general","goal":"understand","obstacle":None,"description":text,"reasoning_path":[],"confidence":0.2}

def _guess_intent(goal):
    m = {"Relaxation":"entertainment","Work":"productivity","Health":"health","Build Simorgh":"development","Watch Movie":"entertainment","Print Document":"productivity","Cook Food":"cooking","Learn":"education","Comfort":"comfort"}
    return m.get(goal, "general")
