def apply_action(code, action):
    if action == "fix_syntax":
        return code.replace('print("Hello', 'print("Hello")')
    
    if action == "fix_logic":
        return code.replace("a-b", "a+b")

    return code