from env.state import CodeState

def get_task():
    return CodeState(
        code='def sum(a,b): print(a-b',
        error="MultipleErrors"
    )