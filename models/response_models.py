from pydantic import BaseModel

class StepResponse(BaseModel):
    state: dict
    reward: float
    done: bool