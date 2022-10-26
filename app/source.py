from dataclasses import dataclass
import os
import re


@dataclass
class Transaction:
    transaction_id: str = ""
    transaction_type: str = ""
    counterparty_name: str = ""
    counterparty_type: str = ""
    counterparty_bank: str = ""
    remarks: str = ""
    ignore: bool = False


class Source:
    name = "base"
    columns = {}

    @staticmethod
    def parse_details(row, country, cities):
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

    @staticmethod
    def parse_details(row, country, cities):
        details = row["details"]
        axis_id = os.getenv("AXIS_CUSTOMID", "")
        if details.startswith("UPIRECONP2PM/"):
            _, transaction_id, _ = [each.strip() for each in details.split("/", 2)]
            transaction = Transaction(
                transaction_type="UPI",
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
        elif details.startswith(("UPI/", "IMPS/")):
            transaction_type, to_type, transaction_id, to_name, extra = [
                each.strip() for each in details.split("/", 4)
            ]
            if to_name == axis_id:
                to_name = ""
                to_bank = ""
                remarks = extra
            else:
                to_bank, remarks = extra.split("/")

            to_type = "Merchant" if to_type == "P2M" else "Person"
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title(),
                counterparty_type=to_type,
                counterparty_bank=to_bank,
                remarks=remarks,
            )
        elif details.startswith("ECOM PUR/"):
            transaction_type, to_name, _ = [
                each.strip() for each in details.split("/", 2)
            ]
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
            _, counterparty_name = [
                each.strip() for each in details.split("PAID TO", 1)
            ]
            transaction = Transaction(
                transaction_type="CHQ", counterparty_name=counterparty_name
            )
        elif (
            re.search(
                "(Consolidated|GST|Dr Card|Excess).*Charge",
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
        elif axis_id and details.startswith(f"{axis_id}:"):
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details[len(axis_id) + 1 :],
            )
        else:
            raise RuntimeError(f"Unknown Transaction Type: {details}")

        return transaction


class AxisCCStatement(Source):
    name = "axis-cc"
    columns = {
        "date": "Transaction Date",
        "details": "Transaction Details",
        "credit": "CR",
        "debit": "DR",
        "amount": "Amount in INR",
    }

    @staticmethod
    def parse_details(row, country, cities):
        details = row["details"]
        m = re.match("(.*?)(?: #\w+)* #(\d+)", details)
        merchant_place, transaction_id = m.groups()
        merchant_place = country.sub("", merchant_place)
        merchant = cities.sub("", merchant_place)
        ignore = details.startswith("MB PAYMENT")
        return Transaction(
            transaction_id=transaction_id,
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


class Cash(Source):
    name = "cash"
    columns = {
        "date": "Timestamp",
        "details": "Details",
        "credit": None,
        "debit": None,
        "amount": "Amount",
    }

    @staticmethod
    def parse_details(row, country, cities):
        details = row["details"]
        assert details.startswith("Cash/")
        transaction_type, remarks = [each.strip() for each in details.split("/")]
        return Transaction(transaction_type=transaction_type, remarks=remarks)


CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
