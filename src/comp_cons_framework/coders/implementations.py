from comp_cons_framework.coders.bar_lev import BarLevReplacementCoder
from comp_cons_framework.coders.bit_stuffing import BitStuffingRLL02Coder
from comp_cons_framework.coders.gcr import GCR4B5BCoder
from comp_cons_framework.coders.ryabko import RyabkoUniversalRLL02Coder
from comp_cons_framework.coders.state_splitting import StateSplittingRLL02Coder
from comp_cons_framework.core.base import ConstrainedCoder


def make_coders() -> list[ConstrainedCoder]:
    return [
        StateSplittingRLL02Coder(6, 8),
        StateSplittingRLL02Coder(13, 16),
        GCR4B5BCoder(),
        RyabkoUniversalRLL02Coder(5, 6),
        RyabkoUniversalRLL02Coder(14, 16),
        BitStuffingRLL02Coder(),
        BarLevReplacementCoder(5),
    ]
