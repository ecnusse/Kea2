# state.py is used for stateful testing
#
# Supports defining complex state that can be shared across multiple test cases 
# to control test flow and dependencies
INVARIANT_MARKER = "_is_invariant"


class State(dict):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


state = State()


def invariant(f):
    setattr(f, INVARIANT_MARKER, True)
    return f
