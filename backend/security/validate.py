from pydantic import BaseModel, constr


class SymbolRequest(BaseModel):
    symbol: constr(pattern="^[A-Z0-9.\-]{1,10}$")  # NSE/BSE compatible
