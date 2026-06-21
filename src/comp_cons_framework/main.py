from comp_cons_framework.experiments.experiment import print_results, run_experiment, write_outputs


def main() -> None:
    results = run_experiment()
    csv_path, comparison_tex_path, operations_tex_path = write_outputs(results)
    print_results(results, csv_path, comparison_tex_path, operations_tex_path)


if __name__ == "__main__":
    main()
