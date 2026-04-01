from env.state import CodeState

def get_task():
    return CodeState(
        code='def add(a,b): return a-b',
        error="LogicError"
    )