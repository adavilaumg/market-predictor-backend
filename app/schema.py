from pydantic import BaseModel 
 
class InputData(BaseModel): 
    tenure: int 
    monthlycharges: float 
    contract: int  # 0: Month-to-month, 1: One year, 2: Two year