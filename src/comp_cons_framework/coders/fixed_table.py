from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString
from comp_cons_framework.core.rll import bits_to_int, int_to_bits, table_words
from comp_cons_framework.core.stats import Stats


class FixedTableBlockCoder(ConstrainedCoder):
    def __init__(
        self,
        name: str,
        input_block_size: int,
        output_block_size: int,
        codebook: dict[int, BitString] | None = None,
    ) -> None:
        self.name = name
        self.input_block_size = input_block_size
        self.output_block_size = output_block_size
        if codebook is None:
            words = table_words(output_block_size, 2**input_block_size)
            self.forward = {index: word for index, word in enumerate(words)}
        else:
            self.forward = dict(codebook)
        self.reverse = {word: index for index, word in self.forward.items()}

    def encode(self, bits: BitString, stats: Stats) -> BitString:
        encoded = []
        assert self.input_block_size is not None
        for block in self._padded_blocks(bits, self.input_block_size):
            index = bits_to_int(block, stats)
            encoded.append(stats.lookup(self.forward, index))
        return "".join(encoded)

    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        decoded = []
        assert self.input_block_size is not None
        for block in self.coded_blocks(encoded):
            index = stats.lookup(self.reverse, block)
            decoded.append(int_to_bits(index, self.input_block_size))
        return "".join(decoded)[:original_length]

    def memory_cells(self) -> int:
        return len(self.forward) + len(self.reverse)
