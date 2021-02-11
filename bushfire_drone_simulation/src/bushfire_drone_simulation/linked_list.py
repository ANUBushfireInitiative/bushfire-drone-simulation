"""Doubly linked list implementation."""

from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class Node(Generic[T]):  # pylint: disable=too-few-public-methods
    """Class containing element of linked list."""

    def __init__(self, value: T):
        """Initialize node."""
        self.value: T = value
        self.next: Optional[Node] = None
        self.prev: Optional[Node] = None


class LinkedList(Generic[T]):
    """Class for linked list."""

    def __init__(self):
        """Initialize linked list."""
        self.first: Optional[Node] = None
        self.last: Optional[Node] = None
        self.length: int = 0

    def insert_after(self, prev_node: Node, new_value: T) -> None:
        """Insert new_value after prev_node in the linked list."""
        new_node = Node(new_value)
        new_node.prev = prev_node
        if prev_node.next is None:
            self.last = new_node
        else:
            new_node.next = prev_node.next
            new_node.next.prev = new_node
        prev_node.next = new_node
        self.length += 1

    def empty(self):
        """Return whether or not the linked list is empty."""
        return self.length == 0

    def clear(self) -> None:
        """Clear the linked list."""
        self.length = 0
        self.first = None
        self.last = None

    def get_last(self) -> T:
        """Return the final element of the linked list. Equivalent to pop/get in a queue."""
        assert self.length != 0, "get_last called on empty list"
        assert self.last is not None, "something broke in the list implementation."
        ret_value = self.last.value
        if self.last.prev is None:
            self.first = None
        else:
            self.last.prev.next = None
            self.last = self.last.prev
        self.length -= 1
        return ret_value

    def delete_from(self, delete_node: Node) -> None:
        """Delete all elements of the list prior to delete_node."""
        assert self.length != 0, "get_last called on empty list"
        assert self.first is not None, "something broke in the list implementation."
        delete_node.prev = None
        self.first = delete_node
        self.length = 0
        current: Optional[Node[T]] = self.first
        while current is not None:
            current = current.next
            self.length += 1
        assert self.length != 0, "we broke something"

    def put(self, value: T) -> None:
        """Add a value to the front of the linked list."""
        new_node = Node(value)
        if self.first is None:
            self.first = new_node
            self.last = new_node
        else:
            new_node.next = self.first
            self.first.prev = new_node
            self.first = new_node
        self.length += 1

    def peak(self) -> T:
        """Return value of last element of the linked list without removing it."""
        assert self.length != 0, "peak called on empty list"
        assert self.last is not None, "something is wrong with the list implementation"
        return self.last.value

    def peak_first(self) -> T:
        """Return value of first element of the linked list without removing it."""
        assert self.length != 0, "first called on empty list"
        assert self.first is not None, "something is wrong with the list implementation"
        return self.first.value

    def __iter__(self):
        """Iterate operator for linked list."""
        current_node = self.first
        while current_node is not None:
            if current_node.next is not None:
                yield current_node.value, current_node.next
            else:
                yield current_node.value, None
            current_node = current_node.next

    def __len__(self) -> int:
        """Length operator for linked list."""
        return self.length

    def __getitem__(self, idx: int):
        """Return value at given index."""
        assert idx - 1 <= self.length, "get_node: Index out of bounds"
        current = self.first
        for _ in range(idx):
            assert current is not None, "poor implementation of linked list"
            current = current.next
        assert current is not None, "poor implementation of linked list"
        return current.value

    def get_node(self, index: int) -> Optional[Node]:
        """Return node at given index."""
        assert index - 1 <= self.length, "get_node: Index out of bounds"
        current = self.first
        for _ in range(index):
            assert current is not None, "poor implementation of linked list"
            current = current.next
        assert current is not None, "poor implementation of linked list"
        return current
