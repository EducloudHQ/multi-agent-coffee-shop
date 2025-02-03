from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Product(BaseModel):
    productId: str
    category: str
    createdDate: str
    description: str
    modifiedDate: str
    name: str
    package: str
    pictures: List[str]
    price: float
    tags: Optional[List[str]] = Field(default_factory=list)
