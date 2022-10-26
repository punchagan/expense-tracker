from dataclasses import dataclass
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
        if details.startswith("UPI"):
            (
                transaction_type,
                to_type,
                transaction_id,
                to_name,
                to_bank,
                remarks,
            ) = [each.strip() for each in details.split("/")]
            to_type = "Merchant" if to_type == "P2M" else "Person"
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title(),
                counterparty_type=to_type,
                counterparty_bank=to_bank,
                remarks=remarks,
            )
        else:
            if re.search("(Consolidated|GST).*Charge", details) is not None:
                transaction = Transaction(
                    transaction_type="AC",
                    counterparty_name="Axis Bank",
                    counterparty_type="Merchant",
                    remarks=details,
                )
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
        return Transaction(
            transaction_id=transaction_id,
            transaction_type="CC",
            counterparty_name=merchant.title(),
            counterparty_type="Merchant",
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
