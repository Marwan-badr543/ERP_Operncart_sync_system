
from typing import Any, Dict
from pydantic import BaseModel

MianPayload = Dict[str, Any]


class UpdatePrice(BaseModel):
    price_list_rate : int
    price_list : str
    item_code : str
    
class UpdateQuantity(BaseModel):
    item_code : str
    
    
    
    