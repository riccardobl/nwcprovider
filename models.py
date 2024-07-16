# Data models for your extension

from sqlite3 import Row
from pydantic import BaseModel, Field
import time
import json
from typing import List, Dict, Any
from pydantic import BaseModel



class NWCKey(BaseModel):
    pubkey: str 
    wallet: str
    description: str 
    expires_at: int
    permissions: str
    created_at: int 
    last_used: int 
    
    def getPermissions(cls) -> List[str]:
        try:
            return cls.permissions.split(" ")
        except:
            # TODO: log error
            return []



    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "NWCKey":
        return cls(**row)

class NWCBudget(BaseModel):
    id: int 
    pubkey: str 
    budget_msats: int 
    refresh_window: int 
    created_at: int 
    used_budget_msats: int = 0

    def get_timestamp_range(cls):
        c = int(time.time())
        if cls.refresh_window <= 0:  # never refresh
            # return a timestamp in the future
            return c + 21000000        
        # calculate the next refresh timestamp 
        elapsed = c - cls.created_at
        passed_cycles = elapsed // cls.refresh_window
        last_cycle = cls.created_at + (passed_cycles * cls.refresh_window)
        next_cycle = last_cycle + cls.refresh_window
        return last_cycle, next_cycle
    
    
    @classmethod
    def from_row(cls, row: Row) -> "NWCBudget":
        return cls(**dict(row))


class NWCLog(BaseModel):
    id: int
    pubkey: str
    payload: str
    created_at: int

    @classmethod
    def from_row(cls, row: Row) -> "NWCLog":
        return cls(**dict(row))



class NWCNewBudget(BaseModel):
    budget_msats: int
    refresh_window: int
    created_at: int

class NWCRegistrationRequest(BaseModel):
    permissions: List[str]
    description: str
    expires_at: int
    budgets: List[NWCNewBudget]


class NWCGetResponse(BaseModel):
    data: NWCKey
    budgets: List[NWCBudget]


