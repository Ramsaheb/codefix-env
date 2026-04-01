def safe_exec(code):
    try:
        exec(code)
        return True
    except:
        return False