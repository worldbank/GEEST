import time
from collections import defaultdict
from functools import wraps
from geest.utilities import log_message
from typing import Dict, List, Optional, Any


class TimingNode:
    """A node in the timing tree representing a single timing operation."""

    def __init__(self, name: str, parent: Optional["TimingNode"] = None):
        self.name = name
        self.parent = parent
        self.children: Dict[str, "TimingNode"] = {}
        self.times: List[float] = []
        self.current_start: Optional[float] = None
        self.self_time: float = 0  # Time spent in this node excluding children
        self.child_time: float = 0  # Track time spent in children

    def add_time(self, duration: float, self_duration: float) -> None:
        """Add a timing measurement."""
        self.times.append(duration)
        self.self_time += self_duration

    def total_time(self) -> float:
        """Get total time spent in this operation."""
        return sum(self.times)

    def average_time(self) -> float:
        """Get average time per call."""
        return self.total_time() / len(self.times) if self.times else 0

    def call_count(self) -> int:
        """Get number of times this operation was called."""
        return len(self.times)

    def exclusive_time(self) -> float:
        """Get time exclusive to this node (not in children)."""
        return self.self_time

    def add_child(self, name: str) -> "TimingNode":
        """Add a child timing node."""
        if name not in self.children:
            self.children[name] = TimingNode(name, self)
        return self.children[name]

    def get_child(self, name: str) -> Optional["TimingNode"]:
        """Get a child node by name."""
        return self.children.get(name)

    def get_path(self) -> str:
        """Get the full path to this node."""
        if self.parent is None:
            return self.name
        return f"{self.parent.get_path()}/{self.name}"


class Timer:
    """
    🚀 Performance tracking utility for GEEST with pretty tree visualization.
    """

    _root = TimingNode("root")  # Root of the timing tree
    _current_stack: List[TimingNode] = []  # Stack of active timing nodes
    _timings = defaultdict(list)  # For backward compatibility

    @classmethod
    def get_timings(cls):
        """Returns a flat dictionary of all recorded timings (for backward compatibility)"""
        result = {}

        def collect_timings(node: TimingNode, prefix: str = "") -> None:
            node_name = f"{prefix}/{node.name}" if prefix else node.name
            if node.times:
                result[node_name] = node.times.copy()
                # Also maintain the old format for backward compatibility
                cls._timings[node_name].extend(node.times)
            for child in node.children.values():
                collect_timings(child, node_name)

        collect_timings(cls._root)
        return dict(cls._timings)

    @classmethod
    def get_timing_tree(cls) -> TimingNode:
        """Returns the root node of the timing tree."""
        return cls._root

    @classmethod
    def reset_timings(cls):
        """Clears all recorded timings"""
        cls._root = TimingNode("root")
        cls._current_stack = []
        cls._timings.clear()

    @classmethod
    def print_summary(cls):
        """Prints a beautiful tree summary of all timings to the log"""
        # Calculate the true root time for percentages
        total_time = cls._get_root_time()

        log_message("╭─────────────────────────────────────────╮")
        log_message("│  🚀 PERFORMANCE SUMMARY 📊              │")
        log_message("╰─────────────────────────────────────────╯")

        # Print tree structure - start with root's children
        sorted_children = sorted(
            cls._root.children.values(), key=lambda n: n.total_time(), reverse=True
        )

        for i, child in enumerate(sorted_children):
            is_last = i == len(sorted_children) - 1
            cls._print_node_summary(
                child,
                prefix="",
                is_last=is_last,
                root_time=total_time,
            )

        # Print overall time
        log_message("┌─────────────────────────────────────────┐")
        log_message(f"│  ⏱️  Total execution time: {total_time:.2f}s     │")
        log_message("└─────────────────────────────────────────┘")

    @classmethod
    def _get_root_time(cls) -> float:
        """Get the total time at the root level (for percentage calculations)."""
        total = 0
        for child in cls._root.children.values():
            total += child.total_time()
        return total if total > 0 else 1  # Avoid division by zero

    @classmethod
    def _print_node_summary(
        cls,
        node: TimingNode,
        prefix: str = "",
        is_last: bool = False,
        root_time: float = 1,
    ) -> None:
        """Recursively print timing summary for a node and its children with nice tree formatting."""
        total_time = node.total_time()
        calls = node.call_count()
        percent = (total_time / root_time * 100) if root_time > 0 else 0

        # Get the self time (time not in children)
        child_time_sum = sum(child.total_time() for child in node.children.values())
        self_time = total_time - child_time_sum
        self_percent = (self_time / total_time * 100) if total_time > 0 else 0

        # Select appropriate emoji based on performance
        if percent > 50:
            emoji = "🔥"  # Hot/slow
        elif percent > 20:
            emoji = "⏱️"  # Medium
        elif percent > 5:
            emoji = "⚡"  # Fast
        else:
            emoji = "🌱"  # Tiny

        # Print the node with correct tree connectors and self time
        connector = "└── " if is_last else "├── "
        log_message(
            f"{prefix}{connector}{emoji} {node.name}: {total_time:.2f}s ({percent:.1f}%) - {calls} calls"
        )

        # On a new line, show self time if there are children
        if node.children and self_time > 0.001:  # Only show if significant
            self_prefix = prefix + ("    " if is_last else "│   ")
            log_message(
                f"{self_prefix}↳ Self time: {self_time:.2f}s ({self_percent:.1f}%)"
            )

        # Prepare the next level prefix
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Sort children by total time (descending)
        sorted_children = sorted(
            node.children.values(), key=lambda n: n.total_time(), reverse=True
        )

        # Print all children
        for i, child in enumerate(sorted_children):
            is_child_last = i == len(sorted_children) - 1
            cls._print_node_summary(
                child, prefix=child_prefix, is_last=is_child_last, root_time=root_time
            )

    def __init__(self, name):
        """Initialize timer with operation name"""
        self.name = name
        self.node = None  # Will be set in __enter__

    def __enter__(self):
        """Start timing when entering context and establish parent/child relationship."""
        # Determine parent node
        parent_node = Timer._current_stack[-1] if Timer._current_stack else Timer._root

        # Create or get our node
        self.node = parent_node.add_child(self.name)

        # Set start time
        self.node.current_start = time.time()
        self.start = time.time()  # For backward compatibility

        # Add ourselves to the active stack
        Timer._current_stack.append(self.node)

        return self

    def __exit__(self, *args):
        """Record time when exiting context and update the timing tree."""
        elapsed = time.time() - self.start

        # Remove ourselves from the stack
        if Timer._current_stack and Timer._current_stack[-1] == self.node:
            current_node = Timer._current_stack.pop()

            # Record time for this node
            self_time = elapsed - sum(
                child.total_time() for child in current_node.children.values()
            )
            if self_time < 0:  # Sanity check
                self_time = 0

            current_node.add_time(elapsed, self_time)

            # Add our time to parent's child time if there's a parent
            if Timer._current_stack:
                parent_node = Timer._current_stack[-1]
                # No need to update child_time anymore as we calculate it on demand

        # For backward compatibility
        Timer._timings[self.name].append(elapsed)


def timed(func):
    """
    🚀 Decorator to time function execution and maintain hierarchical timing structure.

    Example:
        @timed
        def my_function():
            # Function code
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with Timer(func.__name__):
            return func(*args, **kwargs)

    return wrapper
