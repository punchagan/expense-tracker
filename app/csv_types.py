AXIS_COLUMNS = {
    "date": "Tran Date",
    "details": "PARTICULARS",
    "credit": "CR",
    "debit": "DR",
    "amount": None,
}

AXIS_CC_COLUMNS = {
    "date": "Transaction Date",
    "details": "Transaction Details",
    "credit": "CR",
    "debit": "DR",
    "amount": "Amount in INR",
}

SBI_COLUMNS = {
    "date": "Txn Date",
    "details": "Description",
    "credit": "Credit",
    "debit": "Debit",
    "amount": None,
}

CASH_COLUMNS = {
    "date": "Timestamp",
    "details": "Details",
    "credit": None,
    "debit": None,
    "amount": "Amount",
}

CSV_TYPES = {
    "axis-cc": AXIS_CC_COLUMNS,
    "axis": AXIS_COLUMNS,
    "sbi": SBI_COLUMNS,
    "cash": CASH_COLUMNS,
}
