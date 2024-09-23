from .base import Source

ALL_SCRAPERS = {kls.name: kls for kls in Source.__subclasses__()}
