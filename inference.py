import requests

BASE_URL = "http://localhost:7860"

state = requests.post(f"{BASE_URL}/reset").json()

done = False

while not done:
    action = {"action": "fix_syntax"}
    res = requests.post(f"{BASE_URL}/step", json=action).json()
    
    print(res)
    
    done = res["done"]