from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString, RLL_MAX_ZERO_RUN
from comp_cons_framework.core.stats import Stats


class BitStuffingRLL02Coder(ConstrainedCoder):
    name = "Bit stuffing RLL(0,2)"
    input_block_size = None
    output_block_size = None

    def encode(self, bits: BitString, stats: Stats) -> BitString:
        encoded = []
        zero_run = 0
        for bit in bits:
            encoded.append(bit)
            if stats.compare(bit, "==", "0"):
                zero_run = stats.add(zero_run, 1)
                if stats.compare(zero_run, "==", RLL_MAX_ZERO_RUN):
                    encoded.append("1")
                    zero_run = 0
            else:
                zero_run = 0
        return "".join(encoded)

    def decode(self, encoded: BitString, original_length: int, stats: Stats) -> BitString:
        decoded = []
        zero_run = 0
        index = 0
        while index < len(encoded) and len(decoded) < original_length:
            bit = encoded[index]
            index += 1
            decoded.append(bit)
            if stats.compare(bit, "==", "0"):
                zero_run = stats.add(zero_run, 1)
                if stats.compare(zero_run, "==", RLL_MAX_ZERO_RUN):
                    index += 1
                    zero_run = 0
            else:
                zero_run = 0
        return "".join(decoded)

    def memory_cells(self) -> int:
        return 1
