from collections.abc import Collection
from dataclasses import dataclass
from functools import partial
from typing import NamedTuple
import enum

_END_SYMBOL = object()
_MAP_SYMBOL = ':'


class ParserError(Exception):
    pass


class UnexpectedChar(ParserError):
    pass


class CanvasIndex(NamedTuple):
    row: int
    col: int

    def up(self):  # pylint: disable=invalid-name
        return CanvasIndex(row=self.row - 1, col=self.col)

    def down(self):
        return CanvasIndex(row=self.row + 1, col=self.col)

    def left(self):
        return CanvasIndex(row=self.row, col=self.col - 1)

    def right(self):
        return CanvasIndex(row=self.row, col=self.col + 1)


@dataclass(frozen=True, kw_only=True, slots=True)
class Node:
    canvas_indexes: Collection[CanvasIndex]
    attributes: dict[str, str]


@dataclass(frozen=True, kw_only=True, slots=True)
class Edge:
    canvas_indexes: Collection[CanvasIndex]
    sources: Collection[Node]
    destinations: Collection[Node]


class SecretiveList(list):

    def __repr__(self):
        if len(self) <= 3:
            return super().__repr__()
        return f'[{self[0]}, ... {len(self) - 2} items ..., {self[-1]}]'


def _canvas_indexes_in_rectangle(
        corner_min_inclusive, corner_max_inclusive):
    min_row, min_col = corner_min_inclusive
    max_row, max_col = corner_max_inclusive
    return SecretiveList(
        CanvasIndex(row, col)
        for row in range(min_row, max_row + 1)
        for col in range(min_col, max_col + 1)
    )


def _assert_char(actual, expected):
    if actual != expected:
        raise ValueError(
                f"Expected character: '{expected}', actual: '{actual}'")


def _get_corner(*, start_index, following_indexes, allowed_chars):
    last_index = start_index
    for index, char in following_indexes:
        if char in allowed_chars:
            last_index = index
        else:
            break
    return last_index


def parse_node(*, index, canvas):
    char = canvas[index]
    _assert_char(char, '+')
    top_left_corner = index

    corner = top_left_corner
    corners = []
    for following_indexes, allowed_chars in [
        (canvas.iter_right, '+-'),
        (canvas.iter_down, '+|'),
        (canvas.iter_left, '+-'),
        (canvas.iter_up, '+|'),
    ]:
        corner = _get_corner(
                start_index=corner,
                following_indexes=following_indexes(corner),
                allowed_chars=allowed_chars,
        )
        corners.append(corner)

    if top_left_corner != corner:
        raise ParserError()

    _, bottom_right_corner, _, top_left_corner = corners

    return Node(
        canvas_indexes=_canvas_indexes_in_rectangle(
            corner_min_inclusive=top_left_corner,
            corner_max_inclusive=bottom_right_corner,
        ),
        attributes=_parse_node_attributes(
                canvas,
                corner_min_exclusive=top_left_corner,
                corner_max_exclusive=bottom_right_corner,
        )
    )


class _NodeState(enum.Enum):
    START = enum.auto()
    NAME = enum.auto()
    NAME_DONE = enum.auto()
    VALUE = enum.auto()
    END = enum.auto()


def _start_transition(char, *, attr_name, **_):
    if char == _END_SYMBOL:
        return _NodeState.END
    if char.isspace():
        return _NodeState.START
    if char == _MAP_SYMBOL:
        raise UnexpectedChar(char)
    attr_name.append(char)
    return _NodeState.NAME


def _name_transition(char, *, attr_name, **_):
    if char.isspace():
        raise UnexpectedChar(char)
    if char == _MAP_SYMBOL:
        return _NodeState.NAME_DONE
    if char == _END_SYMBOL:
        raise UnexpectedChar(char)
    attr_name.append(char)
    return _NodeState.NAME


def _name_done_transition(char, *, attr_value, **_):
    if char.isspace():
        return _NodeState.NAME_DONE
    if char in (_MAP_SYMBOL, _END_SYMBOL):
        raise UnexpectedChar(char)
    attr_value.append(char)
    return _NodeState.VALUE


def _value_transition(char, *, attr_value, add_attr, **_):
    if char == _END_SYMBOL:
        add_attr()
        return _NodeState.END
    if char.isspace():
        add_attr()
        return _NodeState.START
    if char == _MAP_SYMBOL:
        raise UnexpectedChar(char)
    attr_value.append(char)
    return _NodeState.VALUE


_node_state_to_trans = {
    _NodeState.START: _start_transition,
    _NodeState.NAME: _name_transition,
    _NodeState.NAME_DONE: _name_done_transition,
    _NodeState.VALUE: _value_transition,
}


def _parse_node_attributes(
        canvas, *, corner_min_exclusive, corner_max_exclusive):
    min_row, min_col = corner_min_exclusive
    max_row, max_col = corner_max_exclusive

    attr_name: list[str] = []
    attr_value: list[str] = []

    attrs = {}

    def _add_attr():
        attrs[''.join(attr_name)] = ''.join(attr_value)
        attr_name.clear()
        attr_value.clear()

    state = _NodeState.START

    for row in range(min_row + 1, max_row):
        for col in range(min_col + 1, max_col):
            trans = _node_state_to_trans[state]
            state = trans(  # type: ignore [operator]
                    canvas[(row, col)],
                    attr_name=attr_name,
                    attr_value=attr_value,
                    add_attr=_add_attr,
            )

    trans = _node_state_to_trans[state]
    trans(  # type: ignore [operator]
            _END_SYMBOL,
            attr_name=attr_name,
            attr_value=attr_value,
            add_attr=_add_attr,
    )

    return attrs


class _EdgeBuilder:

    def __init__(self):
        self._path_indexes = []
        self._source_indexes = []
        self._destination_indexes = []

    def add_path(self, index):
        self._path_indexes.append(index)

    def add_source(self, index):
        self._source_indexes.append(index)

    def add_destination(self, index):
        self._destination_indexes.append(index)

    def get_built(self, nodes):
        return Edge(
                canvas_indexes=(
                    self._path_indexes
                    + self._source_indexes
                    + self._destination_indexes
                ),
                sources=tuple(nodes[index] for index in self._source_indexes),
                destinations=tuple(
                    nodes[index] for index in self._destination_indexes),
        )


def _pipe_or_hyphen_trans(
        idx,
        *,
        builder,
        canvas,
        peek_indexes,
        source_char,
):
    builder.add_path(idx)
    to_explore = []
    for peek_index in peek_indexes:
        char_peek = canvas[peek_index]
        if char_peek == source_char:
            builder.add_source(peek_index)
        else:
            to_explore.append(peek_index)
    return to_explore


def _pipe_trans(idx, *, builder, canvas):
    return _pipe_or_hyphen_trans(
            idx,
            builder=builder,
            canvas=canvas,
            peek_indexes=[idx.up(), idx.down()],
            source_char='-',
    )


def _hyphen_trans(idx, *, builder, canvas):
    return _pipe_or_hyphen_trans(
            idx,
            builder=builder,
            canvas=canvas,
            peek_indexes=[idx.left(), idx.right()],
            source_char='|',
    )


def _plus_trans(idx, *, builder, canvas):
    builder.add_path(idx)
    to_explore = []
    for next_idx, path_char, arrow_head in [
        (idx.up(), '|', '^'),
        (idx.down(), '|', 'v'),
        (idx.left(), '-', '<'),
        (idx.right(), '-', '>'),
    ]:
        next_char = canvas[next_idx]
        if next_char in (path_char, '+', arrow_head):
            to_explore.append(next_idx)
        else:
            _assert_char(next_char, ' ')

    return to_explore


_char_to_destination_and_direction = {
    'v': ('-', CanvasIndex.down),
    '^': ('-', CanvasIndex.up),
    '<': ('|', CanvasIndex.left),
    '>': ('|', CanvasIndex.right),
}


def _arrow_trans(idx, *, builder, canvas):
    dst_char, direction = _char_to_destination_and_direction[canvas[idx]]
    next_index = direction(idx)
    next_char = canvas[next_index]
    _assert_char(next_char, dst_char)
    builder.add_destination(next_index)
    return ()


def parse_edge(*, index, canvas, visited_indexes, nodes):
    builder = _EdgeBuilder()

    indexes_to_explore = set([index])

    transitions = {
        '|': partial(_pipe_trans, builder=builder, canvas=canvas),
        '-': partial(_hyphen_trans, builder=builder, canvas=canvas),
        '+': partial(_plus_trans, builder=builder, canvas=canvas),
        '^': (arr := partial(_arrow_trans, builder=builder, canvas=canvas)),
        'v': arr,
        '>': arr,
        '<': arr,
    }

    while indexes_to_explore:
        index = indexes_to_explore.pop()
        char = canvas[index]
        more_indexes: set[CanvasIndex] = set(
                filter(None, transitions[char](index)))
        visited_indexes.add(index)
        indexes_to_explore |= more_indexes - visited_indexes

    return builder.get_built(nodes)


class Canvas:

    def __init__(self, text):
        self._canvas = text.splitlines()
        self.all_indexes = [
                CanvasIndex(row_num, column_num)
                for row_num, row in enumerate(self._canvas)
                for column_num in range(len(row))
        ]

    def all_indexes_of(self, char):
        return [
            index for index in self.all_indexes
            if self[index] == char
        ]

    def __getitem__(self, index):
        row, col = index
        return self._canvas[row][col]

    def _iter_dir(self, index, *, row_offset=0, col_offset=0):
        while True:
            row, col = index
            index = CanvasIndex(row + row_offset, col + col_offset)
            try:
                yield index, self[index]
            except IndexError:
                return

    def iter_right(self, index):
        return self._iter_dir(index, col_offset=1)

    def iter_left(self, index):
        return self._iter_dir(index, col_offset=-1)

    def iter_down(self, index):
        return self._iter_dir(index, row_offset=1)

    def iter_up(self, index):
        return self._iter_dir(index, row_offset=-1)


def parse(definition):
    processed = set()
    nodes = []
    canvas = Canvas(definition)
    for index in canvas.all_indexes_of('+'):  # corner of a node
        if index in processed:
            continue

        try:
            node = parse_node(index=index, canvas=canvas)
        except ParserError:
            continue

        nodes.append(node)
        processed |= set(node.canvas_indexes)

    indexes_to_nodes = {
            index: node
            for node in nodes
            for index in node.canvas_indexes
    }

    edges = []

    for index in canvas.all_indexes:
        char = canvas[index]
        if not char.strip():
            processed.add(index)
        if index in processed:
            continue

        edge = parse_edge(
                index=index,
                canvas=canvas,
                visited_indexes=processed,
                nodes=indexes_to_nodes,
        )

        edges.append(edge)
        processed |= set(edge.canvas_indexes)

    return nodes, edges
