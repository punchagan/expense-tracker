class Source:
    name = "base"
    columns = {}


class AxisStatement(Source):
    name = "axis"
    columns = {
        "date": "Tran Date",
        "details": "PARTICULARS",
        "credit": "CR",
        "debit": "DR",
        "amount": None,
    }


class AxisCCStatement(Source):
    name = "axis-cc"
    columns = {
        "date": "Transaction Date",
        "details": "Transaction Details",
        "credit": "CR",
        "debit": "DR",
        "amount": "Amount in INR",
    }


class SBIStatement(Source):
    name = "sbi"
    columns = {
        "date": "Txn Date",
        "details": "Description",
        "credit": "Credit",
        "debit": "Debit",
        "amount": None,
    }


class Cash(Source):
    name = "cash"
    columns = {
        "date": "Timestamp",
        "details": "Details",
        "credit": None,
        "debit": None,
        "amount": "Amount",
    }


CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
