"""Data models shared by conversation report modules."""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ReportHeader:
    """Metadata from the first JSONL record."""

    version: str
    session_id: str


@dataclass(frozen=True)
class RecordedCall:
    """One tool invocation recorded in source order."""

    id: str
    position: int
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ConversationReport:
    """A validated version-1 conversation report."""

    header: ReportHeader
    calls: tuple[RecordedCall, ...]


ReplayStatus = Literal["success", "error", "skipped"]


@dataclass
class ReplayedCall:
    """A recorded call enriched with fields and a replay outcome."""

    source: RecordedCall
    status: ReplayStatus
    text_output: list[str] = field(default_factory=list)
    structured_output: Any = None
    message: str | None = None


@dataclass(frozen=True)
class ReplayResult:
    """Replay call results with their overall status."""

    calls: tuple[ReplayedCall, ...]
    status: Literal["success", "partial", "failed", "empty"]
