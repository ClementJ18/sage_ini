"""Source positions: every node and diagnostic carries a Span so lint output and error
messages always point at file:line."""

from dataclasses import dataclass

__all__ = ["Span"]


@dataclass(frozen=True, slots=True)
class Span:
    file: str
    line_start: int  # 1-based, inclusive
    line_end: int  # 1-based, inclusive

    def __post_init__(self):
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError(f"invalid span: {self.line_start}..{self.line_end}")

    def __str__(self) -> str:
        if self.line_start == self.line_end:
            return f"{self.file}:{self.line_start}"
        return f"{self.file}:{self.line_start}-{self.line_end}"

    def merge(self, other: "Span") -> "Span":
        """Smallest span covering both; spans must be in the same file."""
        if other.file != self.file:
            raise ValueError(f"cannot merge spans across files: {self.file} vs {other.file}")
        return Span(
            self.file,
            min(self.line_start, other.line_start),
            max(self.line_end, other.line_end),
        )
