from dataclasses import dataclass

from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString, RLL_MAX_ZERO_RUN
from comp_cons_framework.core.rll import bits_to_int, int_to_bits
from comp_cons_framework.core.stats import Stats


@dataclass(frozen=True)
class GraphEdge:
    word: BitString
    target: int


@dataclass(frozen=True)
class SplitTransition:
    word: BitString
    next_state: str
    source_zero_run: int
    target_zero_run: int


class StateSplittingRLL02Coder(ConstrainedCoder):
    name = "State splitting FSTD RLL(0,2) 2/4"
    input_block_size = 2
    output_block_size = 4
    graph_power = 4
    split_state = 0
    required_outdegree = 2**input_block_size
    initial_state = "0a"

    def __init__(self, input_block_size: int = 2, output_block_size: int = 4) -> None:
        self.input_block_size = input_block_size
        self.output_block_size = output_block_size
        self.graph_power = output_block_size
        self.required_outdegree = 2**input_block_size
        self.name = (
            "State splitting FSTD RLL(0,2) "
            f"{input_block_size}/{output_block_size}"
        )
        self.graph_power_edges = self._construct_power_graph(self.graph_power)
        self.graph_degrees_before_split = {
            state: len(edges) for state, edges in self.graph_power_edges.items()
        }
        self.split_edges = self._split_graph(self.graph_power_edges, self.split_state)
        self.graph_degrees_after_split = {
            state: len(edges) for state, edges in self.split_edges.items()
        }
        self.forward = self._select_tagged_edges(self.split_edges)
        self.reverse = {
            state: {entry.word: (index, entry.next_state) for index, entry in enumerate(entries)}
            for state, entries in self.forward.items()
        }
        self.used_split = True

    def _base_successors(self, state: int) -> list[GraphEdge]:
        successors = [GraphEdge("1", 0)]
        if state < RLL_MAX_ZERO_RUN:
            successors.append(GraphEdge("0", state + 1))
        return successors

    def _construct_power_graph(self, power: int) -> dict[int, list[GraphEdge]]:
        paths = {state: [GraphEdge("", state)] for state in range(RLL_MAX_ZERO_RUN + 1)}
        for _ in range(power):
            next_paths: dict[int, list[GraphEdge]] = {state: [] for state in paths}
            for source, edges in paths.items():
                for edge in edges:
                    for successor in self._base_successors(edge.target):
                        next_paths[source].append(
                            GraphEdge(edge.word + successor.word, successor.target)
                        )
            paths = next_paths
        return {
            state: sorted(edges, key=lambda edge: (edge.word, edge.target))
            for state, edges in paths.items()
        }

    def _split_graph(
        self, graph: dict[int, list[GraphEdge]], split_state: int
    ) -> dict[str, list[SplitTransition]]:
        split_children = ("0a", "0b")
        split_edges = graph[split_state]
        split_point = len(split_edges) // 2
        outgoing_partitions = {
            split_children[0]: split_edges[:split_point],
            split_children[1]: split_edges[split_point:],
        }

        states = [*split_children, "1", "2"]
        result: dict[str, list[SplitTransition]] = {state: [] for state in states}
        for source, edges in graph.items():
            source_ids = split_children if source == split_state else (str(source),)
            for source_id in source_ids:
                source_edges = (
                    outgoing_partitions[source_id] if source == split_state else edges
                )
                for edge in source_edges:
                    target_ids = split_children if edge.target == split_state else (str(edge.target),)
                    for target_id in target_ids:
                        result[source_id].append(
                            SplitTransition(edge.word, target_id, source, edge.target)
                        )

        return {
            state: sorted(edges, key=lambda edge: (edge.word, edge.next_state))
            for state, edges in result.items()
        }

    def _select_tagged_edges(
        self, graph: dict[str, list[SplitTransition]]
    ) -> dict[str, tuple[SplitTransition, ...]]:
        selected: dict[str, tuple[SplitTransition, ...]] = {}
        for state, edges in graph.items():
            unique_edges = []
            used_words = set()
            for edge in edges:
                if edge.word in used_words:
                    continue
                unique_edges.append(edge)
                used_words.add(edge.word)
                if len(unique_edges) == self.required_outdegree:
                    break
            if len(unique_edges) < self.required_outdegree:
                raise ValueError(
                    f"state {state} has only {len(unique_edges)} unique edges after splitting"
                )
            selected[state] = tuple(unique_edges)
        return selected

    def _encode_transition(self, state: str, index: int, stats: Stats) -> SplitTransition:
        stats.memory_accesses += 1
        return self.forward[state][index]

    def _decode_transition(self, state: str, word: BitString, stats: Stats) -> tuple[int, str]:
        stats.memory_accesses += 1
        return self.reverse[state][word]

    def encode(self, bits: BitString, stats: Stats) -> BitString:
        encoded = []
        state = self.initial_state
        for block in self._padded_blocks(bits, self.input_block_size):
            index = bits_to_int(block, stats)
            transition = self._encode_transition(state, index, stats)
            encoded.append(transition.word)
            state = transition.next_state
        return "".join(encoded)

    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        decoded = []
        state = self.initial_state
        for block in self.coded_blocks(encoded):
            index, next_state = self._decode_transition(state, block, stats)
            decoded.append(int_to_bits(index, self.input_block_size))
            state = next_state
        return "".join(decoded)[:original_length]

    def memory_cells(self) -> int:
        encode_entries = sum(len(edges) for edges in self.forward.values())
        decode_entries = sum(len(entries) for entries in self.reverse.values())
        state_register = 1
        return encode_entries + decode_entries + state_register
