from dataclasses import dataclass


OPERATION_FIELDS = (
    "additions",
    "multiplications",
    "divisions",
    "divmods",
    "comparisons",
    "memory_accesses",
    "memory_writes",
)


@dataclass
class Stats:
    additions: int = 0
    multiplications: int = 0
    divisions: int = 0
    divmods: int = 0
    comparisons: int = 0
    memory_accesses: int = 0
    memory_writes: int = 0

    def add(self, left: int, right: int) -> int:
        self.additions += 1
        return left + right

    def sub(self, left: int, right: int) -> int:
        self.additions += 1
        return left - right

    def mul(self, left: int, right: int) -> int:
        self.multiplications += 1
        return left * right

    def divide(self, left: int, right: int) -> float:
        self.divisions += 1
        return left / right

    def divmod(self, left: int, right: int) -> tuple[int, int]:
        self.divmods += 1
        return divmod(left, right)

    def compare(self, left: int | str, op: str, right: int | str) -> bool:
        self.comparisons += 1
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        raise ValueError(f"unsupported comparison operator: {op}")

    def lookup(self, table, key):
        self.memory_accesses += 1
        return table[key]

    def write_memory(self, cells: int = 1) -> None:
        self.memory_writes += cells

    @property
    def total(self) -> int:
        return (
            self.additions
            + self.multiplications
            + self.divisions
            + self.divmods
            + self.comparisons
            + self.memory_accesses
            + self.memory_writes
        )

    def operation_counts(self) -> dict[str, int]:
        return {field: getattr(self, field) for field in OPERATION_FIELDS}
