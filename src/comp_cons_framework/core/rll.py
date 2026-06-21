from comp_cons_framework.core.constants import BitString, RLL_MAX_ZERO_RUN
from comp_cons_framework.core.stats import Stats


def zero_run_prefix(word: BitString) -> int:
    return len(word) - len(word.lstrip("0"))


def zero_run_suffix(word: BitString) -> int:
    return len(word) - len(word.rstrip("0"))


def rll02_valid(bits: BitString) -> bool:
    return "000" not in bits


def valid_from_state(state: int, word: BitString) -> bool:
    zero_run = state
    for bit in word:
        if bit == "0":
            zero_run += 1
            if zero_run > RLL_MAX_ZERO_RUN:
                return False
        else:
            zero_run = 0
    return True


def next_state_after(state: int, word: BitString) -> int:
    zero_run = state
    for bit in word:
        zero_run = zero_run + 1 if bit == "0" else 0
    return zero_run


def int_to_bits(value: int, width: int) -> BitString:
    return format(value, f"0{width}b")


def bits_to_int(bits: BitString, stats: Stats) -> int:
    value = 0
    for bit in bits:
        value = value * 2
        if bit == "1":
            value = value + 1
    return value


def table_words(length: int, count: int) -> list[BitString]:
    words = []
    for value in range(2**length):
        word = int_to_bits(value, length)
        if rll02_valid(word) and zero_run_prefix(word) <= 1 and zero_run_suffix(word) <= 1:
            words.append(word)
        if len(words) == count:
            return words
    raise ValueError(f"not enough RLL(0,2) words of length {length} for {count} entries")
