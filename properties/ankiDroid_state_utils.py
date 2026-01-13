from typing import Optional

from kea2.state import state
import random


def ensure_card_types_default() -> None:
    val = state.get('card_types')
    if not isinstance(val, list):
        state['card_types'] = ['Card 1']
    elif len(val) == 0:
        state['card_types'] = ['Card 1']


def add_card_type(name: Optional[str] = None) -> str:
    ensure_card_types_default()
    if name is None:
        # find next available integer suffix
        length = len(state['card_types'])
        # insert LEFT-TO-RIGHT ISOLATE (U+2068) before the number
        name = f'Card \u2068{length + 1}'
    state['card_types'].append(name)
    return name


def last_card_type() -> str:
    return state['card_types'][-1]


def pop_card_type(index: int = -1) -> str:
    """Remove and return a card type by index (default last)."""
    return state['card_types'].pop(index)


def clear_card_types() -> None:
    """Reset card_types to its default single-item list."""
    state['card_types'] = ['Card 1']

def get_random_new_card_limit():
    p = random.random()

    if p < 0.7:
        return random.randint(-10, 10)
    else:
        choice = random.choice([
            random.randint(-1000, -11),
            random.randint(11, 1000)
        ])
        return choice

