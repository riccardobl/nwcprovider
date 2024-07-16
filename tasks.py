import asyncio

from loguru import logger

from lnbits.core.models import Payment
from lnbits.core.services import create_invoice, pay_invoice, check_transaction_status, PaymentError
from bolt11 import decode as bolt11_decode
from lnbits.core.crud import get_wallet_payment, get_payments, get_wallet
from .crud import get_nwc, tracked_spend_nwc, log_nwc, get_config_nwc
from . import execution_queue
from .NWCServiceProvider import NWCServiceProvider
from typing import Dict, List, Tuple
from math import ceil
import time
from lnbits.db import  Filters
from .models import NWCKey
from typing import Optional
from .permission import nwc_permissions
from lnbits.settings import settings

async def _check(nwc: Optional[NWCKey], method: str, payload: Dict):
    # check
    if not nwc:
        return  {
            "code": "UNAUTHORIZED",
            "message": "This public key has no wallet connected."
        }
    # check permissions
    allowed = False
    permissions = nwc.getPermissions()
    for p in permissions:
        allowed_methods = nwc_permissions.get(p, {}).get("methods", [])
        if method in allowed_methods:
            allowed = True
            break
    if not allowed:
        return {
            "code": "RESTRICTED",
            "message": "This public key is not allowed to do this operation."
        }
    return None
    


async def _process_invoice(wallet_id:str, pubkey:str, invoice:str, amount_msats:int, description:Optional[str]=None):
    async def execute_payment():
        return await pay_invoice(wallet_id=wallet_id, payment_request=invoice,
                                  max_sat=int(ceil(amount_msats/1000)),
                                 description=description or ""
                )
    payment_hash = None
    try:
        in_budget, payment_hash = await tracked_spend_nwc(pubkey, amount_msats, execute_payment)
        if not in_budget:
            error = {
                "code":"QUOTA_EXCEEDED",
                "message": "The wallet has exceeded its spending quota."
            }
            return {
                "error": error,
                "in_budget": False
            }
    except PaymentError as e:
        status = e.status 
        message = e.message
        if status == "failed":
            error = {
                "code": "PAYMENT_FAILED",
                "message": message
            }
            return {
                "error": error,
                "in_budget": False
            }
        else:
            raise e
    if not payment_hash:
        raise Exception("Payment hash not found")
    wait_for_preimage = True # currently required by nip 47 specs, might change in future
    payment_status = None
    while wait_for_preimage:
        payment_status = await check_transaction_status(wallet_id, payment_hash)
        if payment_status.success:
            break
        await asyncio.sleep(0.05)
    return {
        "preimage":  payment_status.preimage or "0000000000000000000000000000000000000000000000000000000000000000",
        "fee_msats": payment_status.fee_msat,
        "paid": payment_status.paid,
        "payment_hash": payment_hash,
        "in_budget": in_budget

    }


async def _on_pay_invoice(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "pay_invoice", payload)
    if error: 
        return [(None,error, [])]
    params = payload.get("params", {})
    invoice = params.get("invoice", None)
    # Ensures invoice is provided
    if not invoice: 
        raise Exception("Missing invoice")
    invoice_data = bolt11_decode(invoice)
    amount_msats = invoice_data.amount_msat
    res = await _process_invoice(nwc.wallet, pubkey, invoice, amount_msats, invoice_data.description)
    error = res.get("error")
    if error:
        return [(None, error, [])]
    preimage = res.get("preimage")
    out = {
        "preimage": preimage,
    }
    await log_nwc(pubkey, payload)
    return [(out,None, [])]


async def _on_multi_pay_invoice(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "multi_pay_invoice", payload)
    if error:
        return [(None, error, [])]
    params = payload.get("params", {})
    invoices = params.get("invoices", [])
    results = []

    # Ensures all invoices are provided
    for i in invoices:
        invoice = i.get("invoice",None)
        if not invoice:
            raise Exception("Missing invoice")

    for i in invoices:
        try:
            id = i.get("id", None)
            invoice = i.get("invoice", None)
            invoice_data = bolt11_decode(invoice)
            amount_msats = invoice_data.amount_msat
            res = await _process_invoice(nwc.wallet, pubkey, invoice, amount_msats, invoice_data.description)
            error = res.get("error")
            if error:
                results.append((None, error, []))
            else:
                r = (
                {
                    "preimage": res.get("preimage"),
                },
                None,
                {
                    "d": id if id else res.get("payment_hash"),
                })
                results.append(r)
        except Exception as e:
            results.append((None, {
                "code": "INTERNAL",
                "message": str(e)
            }))   
    await log_nwc(pubkey, payload)
    return results


async def _on_make_invoice(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "make_invoice", payload)
    if error:
        return [(None, error, [])]
    params = payload.get("params", {})
    amount_msats = params.get("amount", None)
    # Ensures amount is provided
    if not amount_msats: 
        raise Exception("Missing amount")
    description = params.get("description", "")
    description_hash = params.get("description_hash", None)
    expiry = params.get("expiry" , None)
    payment_hash, payment_request = await create_invoice(
        wallet_id=nwc.wallet, 
        amount=int(amount_msats/1000), 
        currency="sat", 
        memo=description,
        description_hash=bytes.fromhex(description_hash) if description_hash else None,
        unhashed_description=description.encode("utf-8"),
        expiry=expiry)
    payment_status = await check_transaction_status(wallet_id=nwc.wallet, payment_hash=payment_hash)
    preimage = payment_status.preimage    
    res = {
        "type": "incoming",
        "invoice": payment_request,
        "description": description,
        "description_hash": description_hash,  
        "preimage": preimage,
        "payment_hash": payment_hash,
        "amount": amount_msats,
        #"fees_paid":None,
        "created_at": int(time.time()),
        "metadata": {}
    }
    if expiry:
        res["expires_at"] = int(time.time()) + int(expiry)
    await log_nwc(pubkey, payload)
    return [(res, None, [])]


async def _on_lookup_invoice(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "lookup_invoice", payload)
    if error:
        return [(None, error, [])]
    params = payload.get("params", {})
    payment_hash = params.get("payment_hash", None)
    invoice = params.get("invoice", None)
    # Ensure payment_hash or invoice are provided
    if not payment_hash and not invoice:
        raise Exception("Missing payment_hash or invoice")
    # Extract hash from invoice if not provided
    if not payment_hash:
        invoice_data = bolt11_decode(invoice)
        payment_hash = invoice_data.payment_hash
    # Get payment data
    payment = await get_wallet_payment(nwc.wallet, payment_hash)
    if not payment:
        raise Exception("Payment not found")
    invoice_data = bolt11_decode(payment.bolt11)
    is_settled = not payment.pending
    res = {
        "type": "outgoing" if payment.is_out else "incoming",
        "invoice": payment.bolt11,
        "description": invoice_data.description if invoice_data.description else payment.memo,
        "preimage": payment.preimage if is_settled or payment.is_in else None,
        "payment_hash": payment.payment_hash,
        "amount": abs(payment.msat),
        "fees_paid": abs(payment.fee),
        "created_at": payment.time,
        "expires_at": payment.time+payment.expiry,
        "settled_at": payment.time if is_settled else None,
        "metadata": {}
    }
    if invoice_data.description_hash:
        res["description_hash"] = invoice_data.description_hash
    await log_nwc(pubkey, payload)
    return [(res, None, [])]


async def _on_list_transactions(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "list_transactions", payload)
    if error:
        return [(None, error, [])]
    tfrom = payload.get("from", 0)
    tto = payload.get("to", int(time.time()))
    limit = payload.get("limit", 10)
    offset = payload.get("offset", 0)
    unpaid = payload.get("unpaid", False)
    type = payload.get("type", None)
    values = []
    filters = Filters()
    filters.where("time <= ?")
    values.append(tto)
    filters.values(values)
    history = await get_payments(
        wallet_id=nwc.wallet,
        complete=True, 
        pending = unpaid, 
        outgoing=not type or type == "outgoing",
        incoming =not type or type=="incoming",
        since=tfrom,
        exclude_uncheckable=False,
        filters=filters,
        limit=limit,
        offset=offset
    )
    transactions = []
    for p in history:
        p: Payment
        invoice_data = bolt11_decode(p.bolt11)
        is_settled = not p.pending
        transactions.append({
            "type": "outgoing" if p.is_out else "incoming",
            "invoice": p.bolt11,
            "description": invoice_data.description,
            "description_hash": invoice_data.description_hash,
            "preimage": p.preimage if is_settled or p.is_in else None,
            "payment_hash": p.payment_hash,
            "amount": abs(p.msat),
            "fees_paid": p.fee,
            "created_at": p.time,
            "settled_at": p.time if is_settled else None,
            "metadata": {}
        })       
    await log_nwc(pubkey, payload)
    return [({
        "transactions": transactions
    }, None, [])]


async def _on_get_balance(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "get_balance", payload)
    if error:
        return [(None, error, [])]
    balance = 0
    wallet = await get_wallet(nwc.wallet)
    if not wallet:
        raise Exception("Wallet not found")
    balance = wallet.balance_msat
    await log_nwc(pubkey, payload)
    return [({
        "balance": balance
    }, None, [])]


async def _on_get_info(sp: NWCServiceProvider, pubkey: str, payload: Dict) -> List[Tuple[Dict, Dict]]:
    nwc = await get_nwc(pubkey, None, False, True)
    error = await _check(nwc, "get_info", payload)
    if error:
        return [(None, error, [])]
    sp_methods = sp.getSupportedMethods()
    permissions = nwc.getPermissions()
    account_methods = []
    for spm in sp_methods:
        for p in permissions:
            allowed_methods = nwc_permissions.get(p, {}).get("methods", [])
            if spm in allowed_methods:
                account_methods.append(spm)
                break  
    await log_nwc(pubkey, payload)
    return [({
        "alias": settings.lnbits_site_title,
        "color": "",
        "network": "mainnet",
        "block_height": 0,
        "block_hash": "",
        "methods": account_methods
    }, None, [])]




async def handle_nwc():
    priv_key = await get_config_nwc("provider_key")
    relay =  await  get_config_nwc("relay")
    nwcsp = NWCServiceProvider(priv_key, relay)
    nwcsp.addRequestListener("pay_invoice", _on_pay_invoice)
    nwcsp.addRequestListener("multi_pay_invoice", _on_multi_pay_invoice)
    nwcsp.addRequestListener("make_invoice", _on_make_invoice)
    nwcsp.addRequestListener("lookup_invoice", _on_lookup_invoice)
    nwcsp.addRequestListener("list_transactions", _on_list_transactions)
    nwcsp.addRequestListener("get_balance", _on_get_balance)
    nwcsp.addRequestListener("get_info", _on_get_info)
    # currently not supported by lnbits
    # nwcsp.addRequestListener("pay_keysend", _on_pay_keysend)
    # nwcsp.addRequestListener("multi_pay_keysend", _on_multi_pay_keysend)
    ###
    await nwcsp.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await nwcsp.cleanup()
        raise  


async def handle_execution_queue():
    while True:
        try:
            task = await execution_queue.get()
            action = task.get("action")
            future = task.get("future")
            try:
                res = await action()
                future.set_result(res)
            except Exception as e:
                future.set_exception(e)
        except Exception as e:
            logger.error(str(e))
