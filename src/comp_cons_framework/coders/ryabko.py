from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString
from comp_cons_framework.core.rll import bits_to_int, int_to_bits
from comp_cons_framework.core.stats import Stats


class RyabkoUniversalRLL02Coder(ConstrainedCoder):
    constraint_name = "RLL(0,2) per block"

    def __init__(self, input_block_size: int = 14, output_block_size: int = 16) -> None:
        self.input_block_size = input_block_size
        self.output_block_size = output_block_size
        self.name = f"Ryabko universal DP RLL(0,2) {input_block_size}/{output_block_size}"
        self.states = ("", "0", "00")
        self.counts: dict[tuple[int, str], int] = {}
        for remaining in range(self.output_block_size + 1):
            for state in self.states:
                self.counts[(remaining, state)] = self._count(remaining, state)

    def _transition(self, state: str, bit: str) -> str | None:
        candidate = state + bit
        if "000" in candidate:
            return None
        return candidate[-2:] if candidate.endswith("0") else ""

    def _count(self, remaining: int, state: str) -> int:
        if remaining == 0:
            return 1
        total = 0
        for bit in ("0", "1"):
            next_state = self._transition(state, bit)
            if next_state is not None:
                total += self.counts.get((remaining - 1, next_state), 0)
        return total

    def _continuations(self, remaining: int, state: str, stats: Stats) -> int:
        return stats.lookup(self.counts, (remaining, state))

    def encode(self, bits: BitString, stats: Stats) -> BitString:
        encoded = []
        for block in self._padded_blocks(bits, self.input_block_size):
            encoded.append(self._unrank(bits_to_int(block, stats), stats))
        return "".join(encoded)

    def _unrank(self, index: int, stats: Stats) -> BitString:
        word = []
        state = ""
        for position in range(self.output_block_size):
            remaining_after_bit = self.output_block_size - position - 1
            zero_state = self._transition(state, "0")
            if zero_state is None:
                word.append("1")
                state = ""
                continue

            zero_count = self._continuations(remaining_after_bit, zero_state, stats)
            if stats.compare(index, "<", zero_count):
                word.append("0")
                state = zero_state
            else:
                index = stats.sub(index, zero_count)
                word.append("1")
                state = ""
        return "".join(word)

    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        decoded = []
        for block in self.coded_blocks(encoded):
            decoded.append(int_to_bits(self._rank(block, stats), self.input_block_size))
        return "".join(decoded)[:original_length]

    def _rank(self, word: BitString, stats: Stats) -> int:
        index = 0
        state = ""
        for position, bit in enumerate(word):
            remaining_after_bit = self.output_block_size - position - 1
            zero_state = self._transition(state, "0")
            if zero_state is None:
                state = ""
            elif stats.compare(bit, "==", "1"):
                index = stats.add(index, self._continuations(remaining_after_bit, zero_state, stats))
                state = ""
            else:
                state = zero_state
        return index

    def memory_cells(self) -> int:
        return len(self.counts)
