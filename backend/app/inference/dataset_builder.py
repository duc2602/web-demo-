"""Build paired clean/degraded handwriting samples for restoration experiments."""

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from app.inference.degradations import degrade_image

DEGRADATION_MODES = ("synthetic_noise", "blur", "broken", "missing", "occlusion")
STRENGTHS = (20, 40, 60, 80, 100)


def _load_unique_sources(paths: list[Path]) -> list[dict]:
    sources: dict[str, dict] = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Source image not found: {path}")
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        digest = hashlib.sha256(
            image.width.to_bytes(4, "big") + image.height.to_bytes(4, "big") + image.tobytes()
        ).hexdigest()
        sources.setdefault(
            digest,
            {
                "digest": digest,
                "image": image.copy(),
                "source_filename": path.name,
                "source_id": digest[:12],
            },
        )
    return [sources[digest] for digest in sorted(sources)]


def _split_sources(sources: list[dict]) -> dict[str, str]:
    assignments = {source["digest"]: "train" for source in sources}
    if len(sources) == 2:
        assignments[sources[-1]["digest"]] = "validation"
    elif len(sources) >= 3:
        assignments[sources[-2]["digest"]] = "validation"
        assignments[sources[-1]["digest"]] = "test"
    return assignments


def build_dataset(source_paths: list[Path], output_dir: Path) -> int:
    sources = _load_unique_sources(source_paths)
    if not sources:
        raise ValueError("Provide at least one clean source image.")

    clean_dir = output_dir / "clean"
    degraded_dir = output_dir / "degraded"
    clean_dir.mkdir(parents=True, exist_ok=True)
    degraded_dir.mkdir(parents=True, exist_ok=True)
    assignments = _split_sources(sources)
    manifest_path = output_dir / "manifest.csv"
    rows = []

    for source in sources:
        source_id = source["source_id"]
        clean_path = clean_dir / f"{source_id}.png"
        source["image"].save(clean_path)
        image_array = np.asarray(source["image"])

        for mode in DEGRADATION_MODES:
            for strength in STRENGTHS:
                seed_text = f"{source['digest']}:{mode}:{strength}"
                seed = int(hashlib.sha256(seed_text.encode("ascii")).hexdigest()[:8], 16)
                noise_sigma = max(5, strength // 2)
                degraded = degrade_image(
                    image_array,
                    mode,
                    noise_sigma=noise_sigma,
                    strength=strength,
                    seed=seed,
                )
                sample_id = f"{source_id}_{mode}_{strength:03d}"
                degraded_path = degraded_dir / f"{sample_id}.png"
                Image.fromarray(degraded).save(degraded_path)
                rows.append(
                    {
                        "sample_id": sample_id,
                        "source_filename": source["source_filename"],
                        "source_sha256": source["digest"],
                        "mode": mode,
                        "strength": strength,
                        "noise_sigma": noise_sigma if mode == "synthetic_noise" else "",
                        "seed": seed,
                        "split": assignments[source["digest"]],
                        "clean_path": clean_path.relative_to(output_dir).as_posix(),
                        "degraded_path": degraded_path.relative_to(output_dir).as_posix(),
                    }
                )

    fieldnames = (
        "sample_id",
        "source_filename",
        "source_sha256",
        "mode",
        "strength",
        "noise_sigma",
        "seed",
        "split",
        "clean_path",
        "degraded_path",
    )
    with manifest_path.open("w", newline="", encoding="utf-8") as manifest:
        writer = csv.DictWriter(manifest, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main() -> None:
    default_output = Path(__file__).resolve().parents[2] / "datasets" / "handwriting_pairs"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, action="append", required=True, help="Clean image; repeat for more images.")
    parser.add_argument("--output", type=Path, default=default_output)
    arguments = parser.parse_args()

    count = build_dataset(arguments.source, arguments.output)
    unique_sources = len(_load_unique_sources(arguments.source))
    print(f"Generated {count} paired samples from {unique_sources} unique clean source image(s).")
    print(f"Dataset: {arguments.output.resolve()}")
    if unique_sources < 3:
        print("Only the train split is available; add distinct clean pages for validation/test splits.")


if __name__ == "__main__":
    main()