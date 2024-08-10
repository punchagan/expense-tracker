import os
import re
from dataclasses import dataclass


@dataclass
class Transaction:
    transaction_id: str = ""
    transaction_type: str = ""
    counterparty_name: str = ""
    counterparty_type: str = ""
    counterparty_bank: str = ""
    remarks: str = ""
    category_name: str = ""
    ignore: bool = False


class Source:
    name = "base"
    columns = {}
    date_format = None

    @staticmethod
    def parse_details(expense, country, cities):
        return Transaction()


class AxisStatement(Source):
    name = "axis"
    columns = {
        "date": "Tran Date",
        "details": "PARTICULARS",
        "credit": "CR",
        "debit": "DR",
        "amount": None,
    }
    date_format = "%d-%m-%Y"
    dtypes = {"DR": "float64", "CR": "float64"}

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        axis_id = os.getenv("AXIS_CUSTOMID", "")
        if details.startswith("UPIRECONP2PM/"):
            _, transaction_id, _ = [each.strip() for each in details.split("/", 2)]
            transaction = Transaction(
                transaction_type="UPI",
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("TIPS/"):
            transaction_id = details.split("/")[3] if details.count("/") == 5 else ""
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type="SCG",
                counterparty_type="Merchant",
                remarks=details.rsplit("/", 1)[0],
            )
        elif details.startswith("CTF "):
            extra = details.split()[-1]
            to_name = re.search("[A-Z]+", extra)
            to_name = to_name.group() if to_name else ""
            transaction_id = re.search("[0-9]+", extra)
            transaction_id = transaction_id.group() if transaction_id else ""
            transaction = Transaction(
                transaction_type="UPI",
                transaction_id=transaction_id,
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("UPI/CRADJ/"):
            _, _, transaction_id, _ = [each.strip() for each in details.split("/", 3)]
            transaction = Transaction(
                transaction_type="UPI",
                transaction_id=transaction_id,
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith(("UPI/", "IMPS/", "NEFT/", "RTGS/", "NBSM/")):
            if details.count("/") == 3:
                transaction_type, transaction_id, to_name, _ = [
                    each.strip() for each in details.split("/", 3)
                ]
                to_type = "P2M"
                extra = " / "
            else:
                transaction_type, to_type, transaction_id, to_name, extra = [
                    each.strip() for each in details.split("/", 4)
                ]
            if to_type not in {"P2M", "P2A", "MB"}:
                to_bank = to_name
                to_name = transaction_id
                transaction_id = to_type
                to_type = "P2A"
                remarks = extra.strip("/")
            elif to_name == axis_id:
                to_name = ""
                to_bank = ""
                remarks = extra
            else:
                if "/" in extra:
                    to_bank, remarks = [each.strip() for each in extra.split("/", 1)]
                else:
                    to_bank = ""
                    remarks = extra.strip()

            to_type = "Person" if to_type == "P2A" else "Merchant"
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title(),
                counterparty_type=to_type,
                counterparty_bank=to_bank,
                remarks=remarks,
            )
        elif details.startswith("ECOM PUR/"):
            transaction_type, to_name, _ = [each.strip() for each in details.split("/", 2)]
            transaction = Transaction(
                transaction_type="ECOM",
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
            )
        elif details.startswith("POS/"):
            transaction_type, to_name, transaction_id, _ = [
                each.strip() for each in details.split("/", 3)
            ]
            transaction = Transaction(
                transaction_type="POS",
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
            )
        elif details.startswith("ATM-CASH"):
            _, remarks = [each.strip() for each in details.split("/", 1)]
            transaction = Transaction(
                transaction_type="ATM",
                counterparty_name="ATM",
                remarks=remarks,
            )
        elif details.startswith("BRN-CLG-CHQ"):
            _, counterparty_name = [each.strip() for each in details.split("PAID TO", 1)]
            transaction = Transaction(transaction_type="CHQ", counterparty_name=counterparty_name)
        elif (
            re.search(
                "(SMS Alerts|Monthly|Consolidated|GST|Dr Card|Excess).*(Chrg|Charge|Service Fee)",
                details,
                flags=re.IGNORECASE,
            )
            is not None
        ):
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("CreditCard Payment"):
            transaction = Transaction(
                transaction_type="AC",
                transaction_id=details.rsplit("#", 1)[-1],
                counterparty_name="CreditCard Payment",
                counterparty_type="Merchant",
                ignore=True,
            )
        elif axis_id and f"{axis_id}:" in details:
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details[len(axis_id) + 1 :],
            )
        elif details.startswith("BRN-PYMT-CARD"):
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details,
                ignore=True,
            )
        else:
            # FIXME: Leave this in for debugging, with a commandline arg
            # import pdb
            # pdb.set_trace()
            raise RuntimeError(f"Unknown Transaction Type: {details}")

        return transaction


class AxisCCStatement(Source):
    name = "axis-cc"
    columns = {
        "date": "Date",
        "details": "Transaction Details",
        "credit": "Credit",
        "debit": "Debit",
        "amount": None,
    }
    date_format = "%d %b '%y"
    dtypes = {"Debit": "float64", "Credit": "float64"}

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        merchant = details.split(",", 1)[0]
        ignore = details.startswith("MB PAYMENT")
        return Transaction(
            transaction_type="CC",
            counterparty_name=merchant.title(),
            counterparty_type="Merchant",
            ignore=ignore,
        )


class SBIStatement(Source):
    name = "sbi"
    columns = {
        "date": "Txn Date",
        "details": "Description",
        "credit": "Credit",
        "debit": "Debit",
        "amount": None,
    }
    date_format = "%d %b %Y"
    dtypes = {"Debit": "float64", "Credit": "float64"}


class Cash(Source):
    name = "cash"
    columns = {
        "date": "Timestamp",
        "details": ["Details", "Category"],
        "credit": None,
        "debit": None,
        "amount": "Amount",
    }
    date_format = "%d/%m/%Y %H:%M:%S"
    dtypes = {"Amount": "float64"}

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        remarks, category_name = [each.strip() for each in details.split("/")]
        return Transaction(
            transaction_type="Cash",
            remarks=remarks,
            category_name=category_name,
        )


CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
