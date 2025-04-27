from pydantic import BaseModel, Field, constr
from typing import Optional, List
from enum import Enum

class AnalysisType(str, Enum):
    QUICK = "quick"
    FULL = "full"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"

class AnalysisRequest(BaseModel):
    symbol: constr(min_length=1, max_length=10) = Field(..., description="Stock symbol")
    analysis_type: AnalysisType = Field(default=AnalysisType.FULL)
    categories: Optional[List[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "analysis_type": "full"
            }
        }
