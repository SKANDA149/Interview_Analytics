"""Interview Analytics CLI — canonical entry point.

Usage:
    python cli.py --input data/input/sample.mp4
    python cli.py --input video.mp4 --diarization data/diarization/segments.json
    python cli.py --input video.mp4 --output-dir results/run1
    python cli.py --help
"""
import argparse
import sys
from pathlib import Path


def _resolve_project_root() -> Path:
    """Return the project root (the directory containing cli.py)."""
    return Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        description="Interview Analytics Pipeline — offline video analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py --input data/input/sample.mp4\n"
            "  python cli.py --input video.mp4 --diarization segments.json\n"
            "  python cli.py --input video.mp4 --output-dir results/run1\n"
        ),
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        help="Path to the input interview video (e.g. data/input/sample.mp4)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help="Base output directory for all pipeline artifacts. "
             "Defaults to data/ under the project root.",
    )
    parser.add_argument(
        "--diarization", "-d",
        type=Path,
        default=None,
        help="Path to a pre-computed diarization segments JSON file. "
             "If not provided, diarization will be automatically generated.",
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=10,
        help="Duration of each video chunk in seconds (default: 10).",
    )

    args = parser.parse_args()

    # Resolve paths relative to CWD (user expectation)
    input_video = args.input.resolve()
    if not input_video.exists():
        print(f"[ERROR] Input video not found: {input_video}", file=sys.stderr)
        sys.exit(1)

    project_root = _resolve_project_root()

    output_dir = args.output_dir.resolve() if args.output_dir else project_root / "data"
    diarization_path = args.diarization.resolve() if args.diarization else None

    if diarization_path and not diarization_path.exists():
        print(f"[ERROR] Diarization file not found: {diarization_path}", file=sys.stderr)
        sys.exit(1)

    # Import pipeline here (after validation) so heavy model imports only
    # happen when we're actually going to run.
    from interview_pipeline.src.pipeline import run_pipeline

    run_pipeline(
        input_video=input_video,
        output_dir=output_dir,
        diarization_path=diarization_path,
        project_root=project_root,
        chunk_duration=args.chunk_duration,
    )


if __name__ == "__main__":
    main()