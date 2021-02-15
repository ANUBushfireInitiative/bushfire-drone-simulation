"""Doubly linked list implementation."""

from typing import Generic, Iterator, Optional, Tuple, TypeVar

T = TypeVar("T")


class Node(Generic[T]):  # pylint: disable=too-few-public-methods
    """Class containing element of linked list.

    self.next will be None if the node is the last element in the list.
    Likewise, self.prev will be None if the node is the first element in the list.
    """

    def __init__(self, value: T) -> None:
        """Initialize node."""
        self.value: T = value
        self.next: Optional[Node[T]] = None
        self.prev: Optional[Node[T]] = None


class LinkedList(Generic[T]):
    """Class for linked list."""

    def __init__(self) -> None:
        """Initialize linked list."""
        self.first: Optional[Node[T]] = None
        self.last: Optional[Node[T]] = None
        self.length: int = 0

    def is_empty(self) -> bool:
        """Return whether or not the linked list is empty."""
        return self.length == 0

    def clear(self) -> None:
        """Clear the linked list."""
        self.length = 0
        self.first = None
        self.last = None

    def get_first(self) -> T:
        """Return the first element of the linked list. Equivalent to pop/get in a queue."""
        if self.length == 0:
            raise IndexError("Get last from empty linked list.")
        assert self.first is not None, "something broke in the list implementation."
        ret_value = self.first.value
        if self.first.next is None:
            self.first = None
            self.last = None
        else:
            self.first.next.prev = None
            self.first = self.first.next
        self.length -= 1
        return ret_value

    def delete_after(self, delete_node: Node[T]) -> None:
        """Delete all elements of the list after to delete_node."""
        if self.length == 0:
            raise IndexError("delete from empty linked list.")
        assert self.last is not None, "something broke in the list implementation."
        delete_node.next = None
        self.last = delete_node
        self.length = 0
        current: Optional[Node[T]] = self.first
        while current is not None:
            current = current.next
            self.length += 1
        assert self.length != 0, "we broke something"

    def put(self, value: T) -> None:
        """Add a value to the end of the linked list."""
        new_node = Node(value)
        if self.last is None:
            self.first = new_node
            self.last = new_node
        else:
            new_node.prev = self.last
            self.last.next = new_node
            self.last = new_node
        self.length += 1

    def peak(self) -> T:
        """Return value of first element of the linked list without removing it."""
        if self.length == 0:
            raise IndexError("peak from empty linked list.")
        assert self.first is not None, "something is wrong with the list implementation"
        return self.first.value

    def peak_last(self) -> T:
        """Return value of last element of the linked list without removing it."""
        if self.length == 0:
            raise IndexError("peak first from empty linked list.")
        assert self.last is not None, "something is wrong with the list implementation"
        return self.last.value

    def iterate_backwards(self) -> Iterator[Tuple[T, Optional[Node[T]]]]:
        """Iterate backwards through the linked list."""
        current_node = self.last
        while current_node is not None:
            yield current_node.value, current_node.prev
            current_node = current_node.prev

    def __iter__(self) -> Iterator[T]:
        """Iterate operator for linked list."""
        current_node = self.first
        while current_node is not None:
            yield current_node.value
            current_node = current_node.next

    def __len__(self) -> int:
        """Length operator for linked list."""
        return self.length

    def __getitem__(self, index: int) -> T:
        """Return value at given index."""
        if index - 1 <= self.length:
            raise IndexError("Index out of bounds")
        current = self.first
        for _ in range(index):
            assert current is not None, "poor implementation of linked list"
            current = current.next
        assert current is not None, "poor implementation of linked list"
        return current.value

    def get_node(self, index: int) -> Optional[Node[T]]:
        """Return node at given index."""
        if index - 1 <= self.length:
            raise IndexError("Index out of bounds")
        current = self.first
        for _ in range(index):
            assert current is not None, "poor implementation of linked list"
            current = current.next
        assert current is not None, "poor implementation of linked list"
        return current
