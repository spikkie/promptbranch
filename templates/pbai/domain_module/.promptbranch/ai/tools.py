from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolRisk(str, Enum):
    READ = "read"


@dataclass(frozen=True)
class McpToolSpec:
    name: str
    risk: ToolRisk
    read_only: bool = True


# Domain modules expose only the Promptbranch tools they are contractually
# permitted to request. Promptbranch remains the runtime provider.
READ_ONLY_MCP_TOOLS = (
    McpToolSpec(name="filesystem.read", risk=ToolRisk.READ, read_only=True),
    McpToolSpec(name="filesystem.list", risk=ToolRisk.READ, read_only=True),
)
