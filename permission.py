nwc_permissions = {
    "pay": {
        "name": "Send payments",
        "methods": [
            "multi_pay_invoice",
            "pay_invoice",
            "pay_keysend",
            "multi_pay_keysend",
        ],
        "default": True,
    },
    "offer": {
        "name": "Create offer",
        "methods": ["make_offer"],
        "default": True,
    },
    "lookup_offer": {
        "name": "Lookup status of offer",
        "methods": ["lookup_offer"],
        "default": True,
    },
    "list_offers": {
        "name": "Read list of offers",
        "methods": ["list_offers"],
        "default": True,
    },
    "invoice": {
        "name": "Create invoices",
        "methods": ["make_invoice"],
        "default": True,
    },
    "lookup": {
        "name": "Lookup status of invoice",
        "methods": ["lookup_invoice"],
        "default": True,
    },
    "history": {
        "name": "Read transaction history",
        "methods": ["list_transactions"],
        "default": True,
    },
    "balance": {
        "name": "Read wallet balance",
        "methods": ["get_balance"],
        "default": True,
    },
    "info": {"name": "Read account info", "methods": ["get_info"], "default": True},
}
