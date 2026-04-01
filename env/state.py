class CodeState:
    def __init__(self, code, error, step_count=0, history=None):
        self.code = code
        self.error = error
        self.step_count = step_count
        self.history = history or []