from ..source import Source
from .axis import AxisStatement, AxisCCStatement

CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
