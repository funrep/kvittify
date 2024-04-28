from typing import Optional, List
from datetime import date
from enum import Enum

from pydantic import BaseModel

class FoodType(Enum):
    VEGETABLES = 'Vegetables'
    MEAT = 'Meat'
    DAIRY = 'Dairy'
    CANDY = 'Candy'
    BEVERAGE = 'Beverage'
    OTHER = 'Other'

class Item(BaseModel):
    product: str
    price: float
    food_type: FoodType
    discount: Optional[float] = None
    quantity: Optional[int] = None
    quantity_kg: Optional[float] = None
    price_per_kg: Optional[float] = None

    class Config:
        use_enum_values = True

class Order(BaseModel):
    items: List[Item]
    date: date