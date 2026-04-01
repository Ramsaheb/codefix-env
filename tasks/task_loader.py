from tasks.easy import get_task as easy
from tasks.medium import get_task as medium
from tasks.hard import get_task as hard

def load_task(name):
    return {
        "easy": easy,
        "medium": medium,
        "hard": hard
    }[name]()