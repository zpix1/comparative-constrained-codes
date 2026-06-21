from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString
from comp_cons_framework.core.rll import int_to_bits, rll02_valid
from comp_cons_framework.core.stats import Stats


class BarLevReplacementCoder(ConstrainedCoder):
    name = "Bar-Lev MSA replacement RLL(0,2) k=5"
    input_block_size = 5
    output_block_size = 6
    constraint_name = "RLL(0,2) per block"
    forbidden = "000"

    def __init__(self, input_block_size: int = 5) -> None:
        self.input_block_size = input_block_size
        self.output_block_size = input_block_size + 1
        position_count = self.output_block_size - len(self.forbidden) + 1
        self.position_bits = (position_count - 1).bit_length()
        self.short_representation_bits = len(self.forbidden) - self.position_bits - 1
        if self.short_representation_bits < 0:
            raise ValueError(
                f"Bar-Lev replacement for W={{000}} requires n <= 6; got n={self.output_block_size}"
            )
        self.short_representation = "1" * self.short_representation_bits
        self.name = f"Bar-Lev MSA replacement RLL(0,2) k={input_block_size}"

    def encode(self, bits: BitString, stats: Stats) -> BitString:
        encoded = []
        for block in self._padded_blocks(bits, self.input_block_size):
            y = list(block)
            stats.write_memory()
            y.append("1")
            while (index := self._find_forbidden(y, stats)) is not None:
                y = self._phi_at(y, index, stats)
            encoded.append("".join(y))
        return "".join(encoded)

    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        decoded = []
        for block in self.coded_blocks(encoded):
            y = list(block)
            while stats.compare(y[-1], "==", "0"):
                y = self._phi_inverse(y, stats)
            decoded.append("".join(y[:-1]))
        return "".join(decoded)[:original_length]

    def _find_forbidden(self, word: list[str], stats: Stats) -> int | None:
        zero_run = 0
        forbidden_length = len(self.forbidden)
        for index, bit in enumerate(word):
            if stats.compare(bit, "==", "0"):
                zero_run = stats.add(zero_run, 1)
                if stats.compare(zero_run, "==", forbidden_length):
                    return index - forbidden_length + 1
            else:
                zero_run = 0
        return None

    def _phi_at(self, word: list[str], index: int, stats: Stats) -> list[str]:
        stats.write_memory()
        prefix_suffix = word[:index] + word[index + len(self.forbidden) :]
        stats.write_memory()
        if self.short_representation_bits:
            stats.write_memory()
        stats.write_memory()
        return [
            *prefix_suffix,
            *int_to_bits(index, self.position_bits),
            *self.short_representation,
            "0",
        ]

    def _phi_inverse(self, word: list[str], stats: Stats) -> list[str]:
        payload = word[:-1]
        suffix_length = self.position_bits + self.short_representation_bits
        suffix = payload[-suffix_length:] if suffix_length else []
        index_bits = suffix[: self.position_bits]
        index = int("".join(index_bits), 2)
        prefix_suffix = payload[: -suffix_length] if suffix_length else payload
        stats.write_memory()
        return [*prefix_suffix[:index], *self.forbidden, *prefix_suffix[index:]]

    def memory_cells(self) -> int:
        return self.output_block_size

    def constraint_valid(self, encoded: BitString) -> bool:
        return all(rll02_valid(block) for block in self.coded_blocks(encoded))
