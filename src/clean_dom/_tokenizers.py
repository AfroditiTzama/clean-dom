"""Internal adapters for optional tokenizers."""

from functools import lru_cache
from typing import Protocol, Sequence, Union


class Tokenizer(Protocol):
    """Minimal interface accepted by the cleaning report API."""

    def encode(self, text: str) -> Sequence[object]:
        """Return the tokens for a text string."""
        ...


def count_tokens(text: str, tokenizer: Union[str, Tokenizer]) -> int:
    """Count tokens using a named optional tokenizer or an encoder object."""
    if tokenizer == "tiktoken":
        return len(_get_tiktoken_encoder().encode(text))

    if isinstance(tokenizer, str):
        raise TypeError(f"Unsupported tokenizer: {tokenizer!r}.")

    return len(tokenizer.encode(text))


@lru_cache(maxsize=1)
def _get_tiktoken_encoder() -> Tokenizer:
    try:
        import tiktoken
    except ImportError as exc:
        raise ImportError(
            "Token counting with tiktoken requires the optional dependency. "
            'Install it with: pip install "clean-dom[tokens]"'
        ) from exc

    return tiktoken.get_encoding("cl100k_base")
