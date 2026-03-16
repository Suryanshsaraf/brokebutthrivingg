from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class DatasetAsset:
    filename: str
    url: str


@dataclass(frozen=True)
class DatasetSource:
    name: str
    description: str
    source_page: str
    assets: tuple[DatasetAsset, ...]
    access: str = "direct_download"


SOURCE_REGISTRY: dict[str, DatasetSource] = {
    "cfpb_mem": DatasetSource(
        name="cfpb_mem",
        description="CFPB Making Ends Meet public-use samples and user guide.",
        source_page="https://www.consumerfinance.gov/data-research/making-ends-meet-survey-data/public-data/",
        assets=(
            DatasetAsset(
                filename="cfpb_making-ends-meet_user-guide.pdf",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf",
            ),
            DatasetAsset(
                filename="cfpb_making-ends-meet_sample-1.zip",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-1.zip",
            ),
            DatasetAsset(
                filename="cfpb_making-ends-meet_sample-3.zip",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-3.zip",
            ),
            DatasetAsset(
                filename="cfpb_making-ends-meet_sample-4.zip",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-4.zip",
            ),
            DatasetAsset(
                filename="cfpb_making-ends-meet_sample-5.zip",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-5.zip",
            ),
            DatasetAsset(
                filename="cfpb_making-ends-meet_sample-6.zip",
                url="https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-6.zip",
            ),
        ),
    ),
    "cfpb_fwb": DatasetSource(
        name="cfpb_fwb",
        description="CFPB National Financial Well-Being Survey public-use file and codebook.",
        source_page="https://www.consumerfinance.gov/data-research/financial-well-being-survey-data/",
        assets=(
            DatasetAsset(
                filename="cfpb_nfwbs_2016_data.csv",
                url="https://www.consumerfinance.gov/documents/5614/NFWBS_PUF_2016_data.csv",
            ),
            DatasetAsset(
                filename="cfpb_nfwbs_codebook.pdf",
                url="https://www.consumerfinance.gov/documents/5586/cfpb_nfwbs-puf-codebook.pdf",
            ),
        ),
    ),
    "fed_shed": DatasetSource(
        name="fed_shed",
        description="Federal Reserve SHED public CSV ZIP files for 2013-2024.",
        source_page="https://www.federalreserve.gov/consumerscommunities/shed_data.htm",
        assets=tuple(
            DatasetAsset(
                filename=f"shed_{year}.zip",
                url=url,
            )
            for year, url in (
                (2024, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2024_(CSV).zip"),
                (2023, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2023_(CSV).zip"),
                (2022, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2022_(CSV).zip"),
                (2021, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2021_(CSV).zip"),
                (2020, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2020_(CSV).zip"),
                (2019, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2019_(CSV).zip"),
                (2018, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2018_(CSV).zip"),
                (2017, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2017_(CSV).zip"),
                (2016, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2016_(CSV).zip"),
                (2015, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2015_(CSV).zip"),
                (2014, "https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2014_(CSV).zip"),
                (2013, "https://www.federalreserve.gov/consumerscommunities/files/SHED_data_2013_(CSV).zip"),
            )
        )
        + (
            DatasetAsset(
                filename="shed_2019_supplement_apr2020.zip",
                url="https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2019_supplemental_survey_april_2020_(CSV).zip",
            ),
            DatasetAsset(
                filename="shed_2019_supplement_sep2020.zip",
                url="https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2019_supplemental_survey_sept_2020_(CSV).zip",
            ),
        ),
    ),
    "bls_cex_interview_recent": DatasetSource(
        name="bls_cex_interview_recent",
        description="BLS Consumer Expenditure Survey Interview PUMD CSV ZIP files for 2021-2024.",
        source_page="https://www.bls.gov/cex/pumd.htm",
        assets=tuple(
            DatasetAsset(
                filename=f"intrvw{yy}.zip",
                url=f"https://www.bls.gov/cex/pumd/data/csv/intrvw{yy}.zip",
            )
            for yy in ("21", "22", "23", "24")
        ),
    ),
    "nces_npsas_manual": DatasetSource(
        name="nces_npsas_manual",
        description="NCES NPSAS access is via DataLab and should be treated as manual benchmarking acquisition.",
        source_page="https://nces.ed.gov/surveys/npsas/availabledata.asp",
        assets=(),
        access="manual_download",
    ),
}


def _download_asset(asset: DatasetAsset, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / asset.filename
    if destination.exists():
        return destination

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "https://www.bls.gov/cex/pumd.htm",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with requests.get(asset.url, headers=headers, timeout=300, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return destination


def _list_sources() -> list[dict[str, object]]:
    return [
        {
            "name": source.name,
            "description": source.description,
            "source_page": source.source_page,
            "access": source.access,
            "asset_count": len(source.assets),
        }
        for source in SOURCE_REGISTRY.values()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download official public datasets used by the project.")
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Dataset key to download. Repeat the flag for multiple datasets.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/external",
        help="Root directory for downloaded public datasets.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available public sources and exit.",
    )
    args = parser.parse_args()

    if args.list:
        print(json.dumps(_list_sources(), indent=2))
        return

    datasets = args.datasets or ["cfpb_mem", "cfpb_fwb", "fed_shed"]
    output_root = Path(args.output_dir)
    summary: dict[str, dict[str, object]] = {}

    for dataset_name in datasets:
        source = SOURCE_REGISTRY.get(dataset_name)
        if source is None:
            raise SystemExit(f"Unknown dataset key: {dataset_name}")
        if source.access != "direct_download":
            summary[dataset_name] = {
                "status": "manual",
                "source_page": source.source_page,
                "message": source.description,
            }
            continue

        dataset_dir = output_root / dataset_name
        downloaded_files = []
        for asset in source.assets:
            destination = _download_asset(asset, dataset_dir)
            downloaded_files.append(str(destination))

        summary[dataset_name] = {
            "status": "downloaded",
            "source_page": source.source_page,
            "files": downloaded_files,
        }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
