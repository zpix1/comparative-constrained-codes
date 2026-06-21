from abc import ABC, abstractmethod

from comp_cons_framework.core.constants import BitString
from comp_cons_framework.core.stats import Stats


class ConstrainedCoder(ABC):
    name: str
    input_block_size: int | None
    output_block_size: int | None

    @abstractmethod
    def encode(self, bits: BitString, stats: Stats) -> BitString:
        pass

    @abstractmethod
    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        pass

    @abstractmethod
    def memory_cells(self) -> int:
        pass

    def coded_blocks(self, encoded: BitString) -> list[BitString]:
        if self.output_block_size is None:
            return [encoded]
        return [
            encoded[index : index + self.output_block_size]
            for index in range(0, len(encoded), self.output_block_size)
        ]

    def _padded_blocks(self, bits: BitString, block_size: int) -> list[BitString]:
        remainder = len(bits) % block_size
        padding = 0 if remainder == 0 else block_size - remainder
        padded = bits + ("0" * padding)
        return [padded[index : index + block_size] for index in range(0, len(padded), block_size)]
