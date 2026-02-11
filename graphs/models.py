"""Data models for dependency graph analysis."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class GraphNode:
    """A node in the dependency graph (a package)."""
    id: str
    name: str
    path: Optional[str] = None
    version: Optional[str] = None
    is_external: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != {}}


@dataclass
class GraphEdge:
    """An edge in the dependency graph."""
    from_node: str
    to_node: str
    weight: int = 1
    edge_type: str = "import"  # import | dependency | dev_dependency | override
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != {}}


@dataclass
class DependencyGraph:
    """Complete dependency graph with nodes and edges."""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    external_packages: List[str] = field(default_factory=list)
    graph_type: str = "import"  # import | pubspec

    def to_dict(self) -> dict:
        return {
            "graph_type": self.graph_type,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "external_packages": self.external_packages,
        }

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
