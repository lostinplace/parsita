__all__ = ["RegexParser", "reg"]

import re
from typing import Generic, Optional, TypeVar

from .. import options
from ..state import Continue, Reader, State
from ._base import Parser

StringType = TypeVar("StringType", str, bytes)


class RegexParser(Generic[StringType], Parser[StringType, StringType]):
    # Python lacks type of compiled regex so use str
    def __init__(self, pattern: StringType, whitespace: Optional[Parser[StringType, None]] = None):
        super().__init__()
        self.whitespace = whitespace
        self.pattern = re.compile(pattern)

    def consume(self, state: State[StringType], reader: Reader[StringType]):
        if self.whitespace is not None:
            status = self.whitespace.cached_consume(state, reader)
            reader = status.remainder

        match = self.pattern.match(reader.source, reader.position)

        if match is None:
            state.register_failure(f"r'{self.pattern.pattern}'", reader)
            return None
        else:
            value = reader.source[match.start() : match.end()]
            reader = reader.drop(len(value))

            if self.whitespace is not None:
                status = self.whitespace.cached_consume(state, reader)
                reader = status.remainder

            return Continue(reader, value)

    def __repr__(self):
        return self.name_or_nothing() + f"reg(r'{self.pattern.pattern}')"


def reg(pattern: StringType) -> RegexParser[StringType]:
    """Match with a regular expression.

    This matches the text with a regular expression. The regular expressions is
    treated as greedy. Backtracking in the parser combinators does not flow into
    regular expression backtracking. This is only valid in the ``TextParsers``
    context and not in the ``GeneralParsers`` context because regular
    expressions only operate on text.

    Args:
        pattern: str or python regular expression.
    """
    return RegexParser(pattern, options.whitespace)
