from pydantic import BaseModel

class StepRequest(BaseModel):
    action: str