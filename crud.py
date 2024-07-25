from typing import  Optional, Any, List
from . import db
from .models import NWCKey, NWCBudget, NWCLog, NWCNewBudget
import time
from . import enqueue
import json

async def create_nwc(
        pubkey: str,
        wallet_id:str,
        description: str,
        expires_at: int ,
        permissions:List[str] ,
        budgets: Optional[List[NWCNewBudget]] = None
) -> NWCKey:
    # Check if the key already exists
    if await get_nwc(pubkey, None, True):
        raise Exception("Public key already used")
    # If not, create it
    now=int(time.time())
    await db.execute(
        """
        INSERT INTO nwcprovider.keys (pubkey, wallet, description,  permissions, created_at, expires_at, last_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (pubkey, wallet_id, description, " ".join(permissions), now,int(expires_at) if expires_at else 0, now)
    )
    # Add budgets
    if budgets:
        for budget in budgets:
            await db.execute(
                """
                INSERT INTO nwcprovider.budgets (pubkey, budget_msats, refresh_window, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (pubkey, budget.budget_msats, budget.refresh_window, budget.created_at)
            )
    # Return the created key
    return NWCKey(
        pubkey=pubkey, 
        wallet=wallet_id, 
        description=description, 
        expires_at=expires_at, 
        permissions=" ".join(permissions),
        created_at=now,
        last_used=now
    )


async def delete_nwc(
        pubkey: str,
        wallet_id:str
):
    nwc = await get_nwc(pubkey, wallet_id)
    if not nwc:
        raise Exception("Public key does not exist")
    await db.execute(
        """
        DELETE FROM nwcprovider.keys WHERE pubkey = ? AND wallet = ?
        """,
        (pubkey, wallet_id)
    )
    


async def get_wallet_nwcs(
        wallet_id: str,
        include_expired: Optional[bool] = False
) -> List[NWCKey]:
    rows = await db.fetchall(
        "SELECT * FROM nwcprovider.keys WHERE wallet = ? AND (expires_at = 0 OR expires_at > ?)", (wallet_id, int(time.time()) if not include_expired else -1 )
    )
    return [NWCKey(**row) for row in rows]


async def get_nwc(
        pubkey: str,
        wallet_id: Optional[str] = None,
        include_expired: Optional[bool] = False,
        refresh_last_used: Optional[bool] = False
) -> Optional[NWCKey]:
    # expires_at = 0 means it never expires
    if wallet_id:
        row = await db.fetchone(
            "SELECT * FROM nwcprovider.keys WHERE pubkey = ? AND wallet = ? AND (expires_at = 0 OR expires_at > ?)", (pubkey, wallet_id, int(time.time()) if not include_expired else -1 )
        )
    else:
        row = await db.fetchone(
            "SELECT * FROM nwcprovider.keys WHERE pubkey = ? AND (expires_at = 0 OR expires_at > ?)", (pubkey, int(time.time()) if not include_expired else -1 )
        )
    if not row:
        return None
    if refresh_last_used:
        await db.execute(
            """
            UPDATE nwcprovider.keys SET last_used = ? WHERE pubkey = ?
            """,
            (int(time.time()), pubkey)
        )
    return NWCKey(**row)
    

async def get_budgets_nwc(pubkey, calculate_spent=False):
    rows = await db.fetchall(
        "SELECT * FROM nwcprovider.budgets WHERE pubkey = ?", (pubkey)
    )
    budgets = [NWCBudget(**row) for row in rows]
    if calculate_spent:
        for budget in budgets:
            last_cycle, next_cycle = budget.get_timestamp_range()
            tot_spent_in_range_msats = await db.fetchone(
                """
                SELECT SUM(amount_msats) FROM nwcprovider.spent WHERE pubkey = ? AND created_at >= ? AND created_at < ?
                """,
                (pubkey, last_cycle, next_cycle)
            )
            tot_spent_in_range_msats = tot_spent_in_range_msats[0] or 0
            budget.used_budget_msats = tot_spent_in_range_msats        
    return budgets


# async def log_nwc(
#         pubkey: str,
#         payload:Optional[Any] = None
# ):
#     if not payload: payload=""
#     payload = json.dumps(payload)
#     await db.execute(
#         """
#         INSERT INTO nwcprovider.logs (pubkey, payload, created_at)
#         VALUES (?, ?, ?)
#         """,
#         (pubkey, payload, int(time.time()))
#     )

     
async def tracked_spend_nwc(
    pubkey: str,
    amount_msats: int,
    action
):
    async def r():
        created_at = int(time.time())
        budgets = await get_budgets_nwc(pubkey)
        in_budget = True
        for budget in budgets:
            last_cycle, next_cycle = budget.get_timestamp_range()
            tot_spent_in_range_msats =(await db.fetchone(
                """
                SELECT SUM(amount_msats) FROM nwcprovider.spent WHERE pubkey = ? AND created_at >= ? AND created_at < ?
                """,
                (pubkey, last_cycle, next_cycle)
            ))[0] or 0  
            if tot_spent_in_range_msats + amount_msats > budget.budget_msats:
                in_budget = False
                break
        if not in_budget:
            return False, None
        out = await action()
        await db.execute(
            """
            INSERT INTO nwcprovider.spent (pubkey, amount_msats, created_at)
            VALUES (?, ?, ?)
            """,
            (pubkey, amount_msats, created_at)
        )
        return True, out
    return await enqueue(r)

     

async def get_config_nwc(key:str):
    row = await db.fetchone(
        "SELECT * FROM nwcprovider.config WHERE key = ?", (key)
    )
    if not row:
        return None
    return row["value"]

async def get_all_config_nwc():
    rows = await db.fetchall(
        "SELECT * FROM nwcprovider.config"
    )
    return {row["key"]:row["value"] for row in rows}

async def set_config_nwc(key:str, value:str):
    await db.execute(
        """
        DELETE FROM nwcprovider.config
        WHERE key = ?
        """,
        (key,)
    )
    await db.execute(
        """
        INSERT INTO nwcprovider.config (key, value)
        VALUES (?, ?)
        """,
        (key, value)
    )

