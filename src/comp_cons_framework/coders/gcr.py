from comp_cons_framework.coders.fixed_table import FixedTableBlockCoder


GCR_4B5B_CODEBOOK = {
    0x0: "11001",
    0x1: "11011",
    0x2: "10010",
    0x3: "10011",
    0x4: "11101",
    0x5: "10101",
    0x6: "10110",
    0x7: "10111",
    0x8: "11010",
    0x9: "01001",
    0xA: "01010",
    0xB: "01011",
    0xC: "11110",
    0xD: "01101",
    0xE: "01110",
    0xF: "01111",
}


class GCR4B5BCoder(FixedTableBlockCoder):
    def __init__(self) -> None:
        super().__init__("GCR 4B/5B table RLL(0,2)", 4, 5, GCR_4B5B_CODEBOOK)
