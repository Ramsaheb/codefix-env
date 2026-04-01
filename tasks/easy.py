from env.state import CodeState

def get_task():
    return CodeState(
        code='print("Hello',
        error="SyntaxError"
    )