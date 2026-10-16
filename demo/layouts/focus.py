from calmline import dim, level


def context(d):
    used = (d.get("context_window") or {}).get("used_percentage")
    return None if used is None else dim("ctx ") + level(used, 40, 50)


SEGMENTS = {"context": context}

LINES = [
    ["git", "dir", "model", "context"],
    ["ponytail", "cost", "5h", "week"],
]
