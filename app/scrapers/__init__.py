from .base import Source
from .axis import AxisStatement, AxisCCStatement
from .cash import CashStatement
from .sbi import SBIStatement

CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
