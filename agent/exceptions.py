class AstraDraftError(Exception):
    pass


class CADParseError(AstraDraftError):
    pass


class ConversionError(AstraDraftError):
    pass


class QueryError(AstraDraftError):
    pass
