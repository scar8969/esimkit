VALID_TRANSITIONS = {
    "installed": {"enabled", "deleted"},
    "enabled": {"disabled"},
    "disabled": {"enabled", "deleted"},
    "deleted": set(),
}


def can_transition(state: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(state, set())
