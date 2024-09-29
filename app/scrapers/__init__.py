from .axis import AxisCCStatement, AxisStatement
from .base import Source
from .cash import CashStatement
from .sbi import SBIStatement

ALL_SCRAPERS = {kls.name: kls for kls in Source.__subclasses__()}

__all__ = ["ALL_SCRAPERS", "AxisCCStatement", "AxisStatement", "CashStatement", "SBIStatement"]
