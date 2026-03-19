from __future__ import annotations

import argparse
from pathlib import Path

from brokebutthriving.ml.features import build_daily_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the daily training dataset from the SQLite store.")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database")
    parser.add_argument("--output", required=True, help="CSV output path")
    args = parser.parse_args()

    frame = build_daily_dataset(args.db_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    print(f"Exported {len(frame)} daily rows to {output_path}")


if __name__ == "__main__":
    main()

