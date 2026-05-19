# Data models for your extension

import time
from sqlite3 import Row
from typing import Any

from pydantic import BaseModel


class NWCKey(BaseModel):
    pubkey: str
    wallet: str
    description: str
    expires_at: int
    permissions: str
    created_at: int
    last_used: int

    def get_permissions(self) -> list[str]:
        try:
            return self.permissions.split(" ")
        except Exception:
            return []

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "NWCKey":
        return cls(**row)


class NWCBudget(BaseModel):
    id: int
    pubkey: str
    budget_msats: int
    refresh_window: int
    created_at: int
    used_budget_msats: int = 0

    def get_timestamp_range(self) -> tuple[int, int]:
        c = int(time.time())
        if self.refresh_window <= 0:  # never refresh
            # return a timestamp in the future
            return self.created_at, c + 21000000
        # calculate the next refresh timestamp
        elapsed = c - self.created_at
        passed_cycles = elapsed // self.refresh_window
        last_cycle = self.created_at + (passed_cycles * self.refresh_window)
        next_cycle = last_cycle + self.refresh_window
        return last_cycle, next_cycle

    @classmethod
    def from_row(cls, row: Row) -> "NWCBudget":
        return cls(**dict(row))


class NWCNewBudget(BaseModel):
    pubkey: str | None
    budget_msats: int
    refresh_window: int
    created_at: int


# CRUD models
class CreateNWCKey(BaseModel):
    pubkey: str
    wallet: str
    description: str
    expires_at: int
    permissions: list[str]
    budgets: list[NWCNewBudget] | None = None


class DeleteNWC(BaseModel):
    pubkey: str
    wallet: str | None = None


class GetWalletNWC(BaseModel):
    wallet: str | None = None
    include_expired: bool | None = False


class GetNWC(BaseModel):
    pubkey: str
    wallet: str | None = None
    include_expired: bool | None = False
    refresh_last_used: bool | None = False


class GetBudgetsNWC(BaseModel):
    pubkey: str
    calculate_spent: bool | None = False


class TrackedSpendNWC(BaseModel):
    pubkey: str
    amount_msats: int


# API models
class NWCRegistrationRequest(BaseModel):
    permissions: list[str]
    description: str
    expires_at: int
    budgets: list[NWCNewBudget]


class NWCGetResponse(BaseModel):
    data: NWCKey
    budgets: list[NWCBudget]


class NWCConfig(BaseModel):
    key: str
    value: str
