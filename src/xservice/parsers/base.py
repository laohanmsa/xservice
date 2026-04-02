from typing import List, Protocol, TypeVar

from xservice.providers.models import SearchResult, Tweet, User

# Define generic type variables for input and output of the parsers.
# This allows for more specific and type-safe parser implementations.
T_in = TypeVar("T_in", contravariant=True)
T_out = TypeVar("T_out", covariant=True)


class ParsingError(Exception):
    """Raised when the input data for a parser is malformed."""


class Parser(Protocol[T_in, T_out]):
    """A generic protocol for a parser.

    A parser is responsible for converting raw data of type T_in
    into a structured model of type T_out.
    """

    def parse(self, data: T_in) -> T_out:
        """Parse the input data and return the structured model.

        Raises:
            ParsingError: If the data is malformed or a required key is missing.
        """
        ...


# Specific parser protocols for our data models.
# These provide clear contracts for what each parser is expected to do.
TweetParser = Parser[dict, Tweet]
UserParser = Parser[dict, User]
SearchResultParser = Parser[list, SearchResult]
TweetEntriesParser = Parser[list, List[Tweet]]
