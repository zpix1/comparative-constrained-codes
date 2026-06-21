from numbers import Integral, Real
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from comp_cons_framework.coders.implementations import make_coders
from comp_cons_framework.core.base import ConstrainedCoder
from comp_cons_framework.core.constants import BitString, EXPERIMENT_BITS, RANDOM_SEED, RLL_MAX_ZERO_RUN
from comp_cons_framework.core.rll import (
    int_to_bits,
    rll02_valid,
    zero_run_prefix,
    zero_run_suffix,
)
from comp_cons_framework.core.stats import Stats


DISPLAY_COLUMNS = [
    "coder",
    "block_size",
    "input_block_size",
    "output_block_size",
    "rate",
    "encoded_bits",
    "redundancy_bits",
    "encode_ops_per_bit",
    "encode_additions_per_bit",
    "encode_multiplications_per_bit",
    "encode_divisions_per_bit",
    "encode_divmods_per_bit",
    "encode_comparisons_per_bit",
    "encode_memory_accesses_per_bit",
    "encode_memory_writes_per_bit",
    "decode_ops_per_bit",
    "decode_additions_per_bit",
    "decode_multiplications_per_bit",
    "decode_divisions_per_bit",
    "decode_divmods_per_bit",
    "decode_comparisons_per_bit",
    "decode_memory_accesses_per_bit",
    "decode_memory_writes_per_bit",
    "memory_cells",
    "correct",
    "constraint_internal_blocks",
    "constraint_boundaries",
    "constraint_whole_stream",
]


def random_bits(length: int) -> BitString:
    rng = np.random.default_rng(RANDOM_SEED)
    return "".join(str(bit) for bit in rng.integers(0, 2, length, dtype=np.int8))


def boundary_valid(coder: ConstrainedCoder, encoded: BitString) -> bool:
    if hasattr(coder, "stream_valid"):
        return bool(coder.stream_valid(encoded))
    if coder.output_block_size is None:
        return True
    blocks = coder.coded_blocks(encoded)
    for left, right in zip(blocks, blocks[1:]):
        if zero_run_suffix(left) + zero_run_prefix(right) > RLL_MAX_ZERO_RUN:
            return False
    return True


def internal_blocks_valid(coder: ConstrainedCoder, encoded: BitString) -> bool:
    if hasattr(coder, "constraint_valid"):
        return bool(coder.constraint_valid(encoded))
    return all(rll02_valid(block) for block in coder.coded_blocks(encoded))


def stream_valid(coder: ConstrainedCoder, encoded: BitString) -> bool:
    if hasattr(coder, "stream_valid"):
        return bool(coder.stream_valid(encoded))
    return rll02_valid(encoded)


def operation_rates(prefix: str, stats: Stats, input_length: int) -> dict[str, float]:
    denominator = max(input_length, 1)
    return {
        f"{prefix}_{operation}_per_bit": count / denominator
        for operation, count in stats.operation_counts().items()
    }


def exercise_coder(coder: ConstrainedCoder, bits: BitString) -> dict[str, object]:
    encode_stats = Stats()
    decode_stats = Stats()

    start = perf_counter()
    encoded = coder.encode(bits, encode_stats)
    encode_seconds = perf_counter() - start

    start = perf_counter()
    decoded = coder.decode(encoded, len(bits), decode_stats)
    decode_seconds = perf_counter() - start

    correct = decoded == bits
    whole_constraint = stream_valid(coder, encoded)
    internal_constraint = internal_blocks_valid(coder, encoded)
    boundary_constraint = boundary_valid(coder, encoded)

    row = {
        "coder": coder.name,
        "block_size": coder_block_size(coder),
        "input_block_size": coder.input_block_size if coder.input_block_size is not None else "stream",
        "output_block_size": coder.output_block_size if coder.output_block_size is not None else "variable",
        "input_bits": len(bits),
        "encoded_bits": len(encoded),
        "rate": len(bits) / len(encoded),
        "redundancy_bits": len(encoded) - len(bits),
        "encode_ops_per_bit": encode_stats.total / len(bits),
        "decode_ops_per_bit": decode_stats.total / len(bits),
        "encode_ops_total": encode_stats.total,
        "decode_ops_total": decode_stats.total,
        "memory_cells": coder.memory_cells(),
        "encode_ms": encode_seconds * 1000,
        "decode_ms": decode_seconds * 1000,
        "correct": correct,
        "constraint_internal_blocks": internal_constraint,
        "constraint_boundaries": boundary_constraint,
        "constraint_whole_stream": whole_constraint,
    }
    row.update(operation_rates("encode", encode_stats, len(bits)))
    row.update(operation_rates("decode", decode_stats, len(bits)))
    return row


def coder_block_size(coder: ConstrainedCoder) -> str:
    if coder.input_block_size is None or coder.output_block_size is None:
        return "stream/variable"
    return f"{coder.input_block_size}/{coder.output_block_size}"


def run_correctness_tests(coders: list[ConstrainedCoder]) -> None:
    cases = [
        "",
        "0",
        "1",
        "00",
        "000",
        "111111",
        "000000000000",
        "010101010101",
        "001001001001",
        "1100010011110000",
        random_bits(257),
        random_bits(4099),
    ]
    for coder in coders:
        for bits in cases:
            encoded = coder.encode(bits, Stats())
            decoded = coder.decode(encoded, len(bits), Stats())
            assert decoded == bits, f"{coder.name}: decode(encode(bits)) != bits for length {len(bits)}"
            assert internal_blocks_valid(coder, encoded), f"{coder.name}: block-internal RLL(0,2) failed"
        run_exhaustive_block_tests(coder)


def run_exhaustive_block_tests(coder: ConstrainedCoder) -> None:
    if coder.input_block_size is None:
        for length in range(13):
            for value in range(2**length):
                bits = int_to_bits(value, length)
                encoded = coder.encode(bits, Stats())
                decoded = coder.decode(encoded, len(bits), Stats())
                assert decoded == bits, f"{coder.name}: exhaustive stream test failed for {bits!r}"
                assert internal_blocks_valid(coder, encoded), f"{coder.name}: exhaustive stream output violates its constraint"
        return

    if coder.input_block_size > 16:
        return

    for value in range(2**coder.input_block_size):
        bits = int_to_bits(value, coder.input_block_size)
        encoded = coder.encode(bits, Stats())
        decoded = coder.decode(encoded, len(bits), Stats())
        assert decoded == bits, f"{coder.name}: exhaustive block test failed for {bits!r}"
        assert internal_blocks_valid(coder, encoded), f"{coder.name}: exhaustive block output violates its constraint"


def format_number(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, Integral):
        return str(value)
    if isinstance(value, Real):
        text = f"{float(value):.3g}"
        return "0" if text == "-0" else text
    return str(value)


LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: object) -> str:
    text = str(value)
    return "".join(LATEX_ESCAPES.get(character, character) for character in text)


LATEX_CODER_NAMES = {
    "Ryabko universal DP RLL(0,2) 5/6": "Рябко 5/6",
    "Ryabko universal DP RLL(0,2) 14/16": "Рябко 14/16",
    "Bit stuffing RLL(0,2)": "Вставка битов",
    "GCR 4B/5B table RLL(0,2)": "GCR 4B/5B",
    "Bar-Lev MSA replacement RLL(0,2) k=5": "Бар-Лев 5/6",
    "State splitting FSTD RLL(0,2) 6/8": "Разделение состояний 6/8",
    "State splitting FSTD RLL(0,2) 13/16": "Разделение состояний 13/16",
}


def latex_value(column: str, value: object) -> str:
    if isinstance(value, bool):
        return "да" if value else "нет"
    if column == "coder":
        return latex_escape(LATEX_CODER_NAMES.get(str(value), str(value)))
    if column == "block_size" and value == "stream/variable":
        return "поток"
    if isinstance(value, Real):
        return format_number(value)
    return latex_escape(value)


def dataframe_to_latex(
    frame: pd.DataFrame,
    columns: list[str],
    headers: list[str],
    caption: str,
    label: str,
) -> str:
    alignment = "l" + "r" * (len(columns) - 1)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{2pt}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular*}}{{\linewidth}}{{@{{\extracolsep{{\fill}}}}{alignment}@{{}}}}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        values = [latex_value(column, row[column]) for column in columns]
        lines.append(" & ".join(values) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular*}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def active_operation_columns(results: pd.DataFrame) -> list[str]:
    operations = [
        "additions",
        "multiplications",
        "divisions",
        "divmods",
        "comparisons",
        "memory_accesses",
        "memory_writes",
    ]
    columns = []
    for operation in operations:
        encode_column = f"encode_{operation}_per_bit"
        decode_column = f"decode_{operation}_per_bit"
        if results[[encode_column, decode_column]].astype(float).to_numpy().max() > 0:
            columns.extend([encode_column, decode_column])
    return columns


def write_latex_tables(results: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    comparison_path = output_dir / "comparison.tex"
    operations_path = output_dir / "operation_breakdown.tex"

    comparison_columns = [
        "coder",
        "block_size",
        "rate",
        "encode_ops_per_bit",
        "decode_ops_per_bit",
        "memory_cells",
        "constraint_boundaries",
    ]
    comparison_headers = [
        "Кодер",
        "Блок",
        "$R$",
        "Код., оп./бит",
        "Дек., оп./бит",
        "Память",
        "Межбл.?",
    ]
    comparison_path.write_text(
        dataframe_to_latex(
            results,
            comparison_columns,
            comparison_headers,
            "Результаты экспериментального анализа кодеров для RLL(0, 2) ограничения.",
            "tab:coder-comparison",
        ),
        encoding="utf-8",
    )

    operation_columns = ["coder", *active_operation_columns(results)]
    operation_names = {
        "additions": "слож.",
        "multiplications": "умнож.",
        "divisions": "дел.",
        "divmods": "divmod",
        "comparisons": "сравн.",
        "memory_accesses": "пам.",
        "memory_writes": "зап.",
    }
    operation_headers = [
        "Кодер",
        *[
            (
                ("К." if column.startswith("encode_") else "Д.")
                + operation_names[column.removeprefix("encode_").removeprefix("decode_").removesuffix("_per_bit")]
            )
            for column in operation_columns[1:]
        ],
    ]
    operations_path.write_text(
        dataframe_to_latex(
            results,
            operation_columns,
            operation_headers,
            "Число операций на входной бит.",
            "tab:operation-breakdown",
        ),
        encoding="utf-8",
    )
    return comparison_path, operations_path


def write_outputs(results: pd.DataFrame) -> tuple[Path, Path, Path]:
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / "comparison.csv"

    results.to_csv(csv_path, index=False)
    comparison_tex_path, operations_tex_path = write_latex_tables(results, output_dir)
    return csv_path, comparison_tex_path, operations_tex_path


def run_experiment() -> pd.DataFrame:
    coders = make_coders()
    run_correctness_tests(coders)

    bits = random_bits(EXPERIMENT_BITS)
    rows = [exercise_coder(coder, bits) for coder in coders]
    return pd.DataFrame(rows).sort_values("rate", ascending=False)


def print_results(
    results: pd.DataFrame,
    csv_path: Path,
    comparison_tex_path: Path,
    operations_tex_path: Path,
) -> None:
    print("Correctness tests: passed")
    print(f"Input bits: {EXPERIMENT_BITS}")
    print(
        "Results written to: "
        f"{csv_path}, {comparison_tex_path}, and {operations_tex_path}"
    )
    print(results[DISPLAY_COLUMNS].to_string(index=False))
