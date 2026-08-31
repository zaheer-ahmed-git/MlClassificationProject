"""Command-line interface for public-corpus construction."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

from .ahs import DATASET_RELEASE as AHS_DATASET_RELEASE
from .ahs import harmonize as harmonize_ahs
from .ahs_gate import assess_ahs_gate
from .ahs_split import SPLIT_ID as AHS_SPLIT_ID
from .ahs_split import assign_ahs_splits, audit_ahs_split
from .audit import audit_release
from .common import sha256_file
from .registry import find_source, load_registry
from .rhfs import DATASET_RELEASE as RHFS_DATASET_RELEASE
from .rhfs import harmonize as harmonize_rhfs
from caip_maintenance.features.ahs_preprocessing import (
    PREPROCESSOR_ID as AHS_PREPROCESSOR_ID,
    audit_ahs_preprocessing,
    build_ahs_preprocessing,
)
from caip_maintenance.modeling.ahs_experiment import (
    EXPERIMENT_ID as AHS_EXPERIMENT_ID,
    audit_ahs_experiment,
    build_ahs_experiment,
)
from caip_maintenance.modeling.ahs_xgboost_experiment import (
    EXPERIMENT_ID as AHS_XGBOOST_EXPERIMENT_ID,
    FEATURE_ENGINEERING_EXPERIMENT_ID as AHS_XGBOOST_FE_EXPERIMENT_ID,
    audit_ahs_xgboost_experiment,
    build_ahs_xgboost_experiment,
)
from caip_maintenance.modeling.ahs_xgboost_robust_loss_experiment import (
    EXPERIMENT_ID as AHS_XGBOOST_ROBUST_EXPERIMENT_ID,
    audit_ahs_xgboost_robust_loss_experiment,
    build_ahs_xgboost_robust_loss_experiment,
)
from caip_maintenance.modeling.ahs_xgboost_tuning_experiment import (
    EXPERIMENT_ID as AHS_XGBOOST_TUNING_EXPERIMENT_ID,
    audit_ahs_xgboost_tuning_experiment,
    build_ahs_xgboost_tuning_experiment,
)
from caip_maintenance.evaluation.ahs_feature_audit import (
    AUDIT_ID as AHS_FEATURE_AUDIT_ID,
    build_ahs_feature_audit,
)
from caip_maintenance.modeling.ahs_ablation_experiment import (
    EXPERIMENT_ID as AHS_ABLATION_EXPERIMENT_ID,
    audit_ahs_ablation_experiment,
    build_ahs_ablation_experiment,
)
from caip_maintenance.modeling.ahs_robust_loss_experiment import (
    EXPERIMENT_ID as AHS_ROBUST_LOSS_EXPERIMENT_ID,
    audit_ahs_robust_loss_experiment,
    build_ahs_robust_loss_experiment,
)
from caip_maintenance.modeling.ahs_tuning_experiment import (
    EXPERIMENT_ID as AHS_TUNING_EXPERIMENT_ID,
    audit_ahs_tuning_experiment,
    build_ahs_tuning_experiment,
)
from caip_maintenance.evaluation.ahs_diagnostic_review import (
    REVIEW_ID as AHS_REVIEW_ID,
    audit_ahs_diagnostic_review,
    build_ahs_diagnostic_review,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("register-sources", help="validate and summarize source registry")

    fetch = subparsers.add_parser("fetch", help="download immutable registered artifacts")
    fetch.add_argument("--source", required=True)
    fetch.add_argument("--release", required=True)

    validate = subparsers.add_parser("validate-raw", help="verify registered raw artifacts")
    validate.add_argument("--source", required=True)

    subparsers.add_parser(
        "assess-ahs", help="run the aggregate AHS longitudinal go/no-go gate"
    )

    build = subparsers.add_parser("harmonize", help="build a local harmonized release")
    build.add_argument("--release", default=RHFS_DATASET_RELEASE)

    audit = subparsers.add_parser("audit-release", help="audit a harmonized release")
    audit.add_argument("--release", default=RHFS_DATASET_RELEASE)

    assign = subparsers.add_parser(
        "assign-splits", help="build the frozen AHS unit-grouped temporal split"
    )
    assign.add_argument("--release", default=AHS_DATASET_RELEASE)
    assign.add_argument("--split", default=AHS_SPLIT_ID)

    split_audit = subparsers.add_parser(
        "audit-split", help="audit AHS split isolation and temporal contracts"
    )
    split_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    split_audit.add_argument("--split", default=AHS_SPLIT_ID)

    preprocess = subparsers.add_parser(
        "preprocess-ahs", help="fit training-only AHS preprocessing artifacts"
    )
    preprocess.add_argument("--release", default=AHS_DATASET_RELEASE)
    preprocess.add_argument("--split", default=AHS_SPLIT_ID)
    preprocess.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)

    preprocessing_audit = subparsers.add_parser(
        "audit-preprocessing", help="audit AHS preprocessing and leakage boundaries"
    )
    preprocessing_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    preprocessing_audit.add_argument("--split", default=AHS_SPLIT_ID)
    preprocessing_audit.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)

    feature_audit = subparsers.add_parser(
        "audit-ahs-features",
        help="audit harmonized and derived AHS candidate features on training rows",
    )
    feature_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    feature_audit.add_argument("--split", default=AHS_SPLIT_ID)
    feature_audit.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    feature_audit.add_argument("--audit", default=AHS_FEATURE_AUDIT_ID)

    train_experiment = subparsers.add_parser(
        "train-ahs-experiment",
        help="fit the fixed AHS baselines and models on training rows only",
    )
    train_experiment.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_experiment.add_argument("--split", default=AHS_SPLIT_ID)
    train_experiment.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    train_experiment.add_argument("--experiment", default=AHS_EXPERIMENT_ID)

    experiment_audit = subparsers.add_parser(
        "audit-experiment",
        help="audit AHS fit isolation, metrics, checksums, and model reloads",
    )
    experiment_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    experiment_audit.add_argument("--split", default=AHS_SPLIT_ID)
    experiment_audit.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    experiment_audit.add_argument("--experiment", default=AHS_EXPERIMENT_ID)

    train_xgboost = subparsers.add_parser(
        "train-ahs-xgboost",
        help="fit frozen baselines and XGBoost on AHS training rows only",
    )
    train_xgboost.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_xgboost.add_argument("--split", default=AHS_SPLIT_ID)
    train_xgboost.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    train_xgboost.add_argument("--experiment", default=AHS_XGBOOST_EXPERIMENT_ID)

    xgboost_audit = subparsers.add_parser(
        "audit-ahs-xgboost",
        help="audit AHS XGBoost fit isolation, metrics, checksums, and model reload",
    )
    xgboost_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    xgboost_audit.add_argument("--split", default=AHS_SPLIT_ID)
    xgboost_audit.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    xgboost_audit.add_argument("--experiment", default=AHS_XGBOOST_EXPERIMENT_ID)

    train_xgboost_tuning = subparsers.add_parser(
        "train-ahs-xgboost-tuning",
        help="fit XGBoost with validation-only hyperparameter selection",
    )
    train_xgboost_tuning.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_xgboost_tuning.add_argument("--split", default=AHS_SPLIT_ID)
    train_xgboost_tuning.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    train_xgboost_tuning.add_argument("--experiment", default=AHS_XGBOOST_TUNING_EXPERIMENT_ID)

    xgboost_tuning_audit = subparsers.add_parser(
        "audit-ahs-xgboost-tuning",
        help="audit AHS XGBoost validation-only tuning artifacts",
    )
    xgboost_tuning_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    xgboost_tuning_audit.add_argument("--split", default=AHS_SPLIT_ID)
    xgboost_tuning_audit.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    xgboost_tuning_audit.add_argument("--experiment", default=AHS_XGBOOST_TUNING_EXPERIMENT_ID)

    train_xgboost_robust = subparsers.add_parser(
        "train-ahs-xgboost-robust-loss",
        help="compare XGBoost objective functions on engineered AHS features",
    )
    train_xgboost_robust.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_xgboost_robust.add_argument("--split", default=AHS_SPLIT_ID)
    train_xgboost_robust.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    train_xgboost_robust.add_argument("--experiment", default=AHS_XGBOOST_ROBUST_EXPERIMENT_ID)

    xgboost_robust_audit = subparsers.add_parser(
        "audit-ahs-xgboost-robust-loss",
        help="audit AHS XGBoost robust-loss experiment artifacts",
    )
    xgboost_robust_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    xgboost_robust_audit.add_argument("--split", default=AHS_SPLIT_ID)
    xgboost_robust_audit.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    xgboost_robust_audit.add_argument("--experiment", default=AHS_XGBOOST_ROBUST_EXPERIMENT_ID)

    train_tuning = subparsers.add_parser(
        "train-ahs-tuning",
        help="fit AHS models with validation-only hyperparameter selection",
    )
    train_tuning.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_tuning.add_argument("--split", default=AHS_SPLIT_ID)
    train_tuning.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    train_tuning.add_argument("--experiment", default=AHS_TUNING_EXPERIMENT_ID)

    tuning_audit = subparsers.add_parser(
        "audit-ahs-tuning",
        help="audit AHS validation-only tuning artifacts",
    )
    tuning_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    tuning_audit.add_argument("--split", default=AHS_SPLIT_ID)
    tuning_audit.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    tuning_audit.add_argument("--experiment", default=AHS_TUNING_EXPERIMENT_ID)

    train_robust = subparsers.add_parser(
        "train-ahs-robust-loss",
        help="compare gradient boosting loss functions on engineered AHS features",
    )
    train_robust.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_robust.add_argument("--split", default=AHS_SPLIT_ID)
    train_robust.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    train_robust.add_argument("--experiment", default=AHS_ROBUST_LOSS_EXPERIMENT_ID)

    robust_audit = subparsers.add_parser(
        "audit-ahs-robust-loss",
        help="audit AHS robust-loss experiment artifacts",
    )
    robust_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    robust_audit.add_argument("--split", default=AHS_SPLIT_ID)
    robust_audit.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    robust_audit.add_argument("--experiment", default=AHS_ROBUST_LOSS_EXPERIMENT_ID)

    train_ablation = subparsers.add_parser(
        "train-ahs-ablation",
        help="run AHS feature-group ablation with gradient boosting",
    )
    train_ablation.add_argument("--release", default=AHS_DATASET_RELEASE)
    train_ablation.add_argument("--split", default=AHS_SPLIT_ID)
    train_ablation.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    train_ablation.add_argument("--experiment", default=AHS_ABLATION_EXPERIMENT_ID)

    ablation_audit = subparsers.add_parser(
        "audit-ahs-ablation",
        help="audit AHS feature-group ablation artifacts",
    )
    ablation_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    ablation_audit.add_argument("--split", default=AHS_SPLIT_ID)
    ablation_audit.add_argument("--preprocessor", default="ahs-feature-engineering-v1")
    ablation_audit.add_argument("--experiment", default=AHS_ABLATION_EXPERIMENT_ID)

    review = subparsers.add_parser(
        "review-ahs-diagnostics",
        help="build residual/subgroup/weight/utility review without fitting models",
    )
    review.add_argument("--release", default=AHS_DATASET_RELEASE)
    review.add_argument("--split", default=AHS_SPLIT_ID)
    review.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    review.add_argument("--experiment", default=AHS_EXPERIMENT_ID)
    review.add_argument("--review", default=AHS_REVIEW_ID)

    review_audit = subparsers.add_parser(
        "audit-diagnostic-review",
        help="audit AHS diagnostic review checksums and non-promotion bounds",
    )
    review_audit.add_argument("--release", default=AHS_DATASET_RELEASE)
    review_audit.add_argument("--split", default=AHS_SPLIT_ID)
    review_audit.add_argument("--preprocessor", default=AHS_PREPROCESSOR_ID)
    review_audit.add_argument("--experiment", default=AHS_EXPERIMENT_ID)
    review_audit.add_argument("--review", default=AHS_REVIEW_ID)

    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    registry_path = root / "configs" / "sources.toml"

    try:
        if args.command == "register-sources":
            registry = load_registry(registry_path)
            print(
                json.dumps(
                    {
                        "registry_version": registry["registry_version"],
                        "source_count": len(registry["sources"]),
                        "approved_core": [
                            source["source_id"]
                            for source in registry["sources"]
                            if source["status"] == "approved_core"
                        ],
                        "approved_proxy": [
                            source["source_id"]
                            for source in registry["sources"]
                            if source["status"] == "approved_proxy"
                        ],
                        "candidate_count": sum(
                            source["status"] not in {"approved_core", "approved_proxy"}
                            for source in registry["sources"]
                        ),
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "fetch":
            registry = load_registry(registry_path)
            source = find_source(registry, args.source)
            if source["release"] != args.release:
                raise ValueError(
                    f"registered release for {args.source} is {source['release']!r}"
                )
            result = _fetch_source(root, source)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "validate-raw":
            registry = load_registry(registry_path)
            result = _validate_raw(root, find_source(registry, args.source))
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.command == "assess-ahs":
            result = assess_ahs_gate(root)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["decision"] == "go" else 1
        if args.command == "harmonize":
            builders = {
                RHFS_DATASET_RELEASE: harmonize_rhfs,
                AHS_DATASET_RELEASE: harmonize_ahs,
            }
            if args.release not in builders:
                raise ValueError(f"unsupported dataset release: {args.release}")
            output = builders[args.release](root, args.release)
            print(json.dumps({"status": "built", "release_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-release":
            release_dir = root / "data" / "processed" / "releases" / args.release
            report = audit_release(release_dir)
            (release_dir / "qa_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "assign-splits":
            output = assign_ahs_splits(root, args.release, args.split)
            print(json.dumps({"status": "built", "split_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-split":
            split_dir = (
                root / "data" / "processed" / "splits" / args.release / args.split
            )
            report = audit_ahs_split(root, split_dir)
            (split_dir / "qa_split_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "preprocess-ahs":
            output = build_ahs_preprocessing(
                root, args.release, args.split, args.preprocessor
            )
            print(
                json.dumps(
                    {"status": "built", "preprocessing_path": str(output)}, indent=2
                )
            )
            return 0
        if args.command == "audit-preprocessing":
            output_dir = (
                root
                / "data"
                / "processed"
                / "preprocessing"
                / args.release
                / args.split
                / args.preprocessor
            )
            report = audit_ahs_preprocessing(root, output_dir)
            (output_dir / "qa_preprocessing_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "audit-ahs-features":
            output = build_ahs_feature_audit(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.audit,
            )
            print(json.dumps({"status": "built", "feature_audit_path": str(output)}, indent=2))
            return 0
        if args.command == "train-ahs-experiment":
            output = build_ahs_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(
                json.dumps(
                    {"status": "built", "experiment_path": str(output)}, indent=2
                )
            )
            return 0
        if args.command == "audit-experiment":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_experiment(root, output_dir)
            (output_dir / "qa_experiment_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-xgboost":
            output = build_ahs_xgboost_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(
                json.dumps(
                    {"status": "built", "experiment_path": str(output)}, indent=2
                )
            )
            return 0
        if args.command == "audit-ahs-xgboost":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_xgboost_experiment(root, output_dir)
            (output_dir / "qa_xgboost_experiment_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-xgboost-tuning":
            output = build_ahs_xgboost_tuning_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(json.dumps({"status": "built", "experiment_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-ahs-xgboost-tuning":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_xgboost_tuning_experiment(root, output_dir)
            (output_dir / "qa_xgboost_tuning_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-xgboost-robust-loss":
            output = build_ahs_xgboost_robust_loss_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(json.dumps({"status": "built", "experiment_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-ahs-xgboost-robust-loss":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_xgboost_robust_loss_experiment(root, output_dir)
            (output_dir / "qa_xgboost_robust_loss_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-tuning":
            output = build_ahs_tuning_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(json.dumps({"status": "built", "experiment_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-ahs-tuning":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_tuning_experiment(root, output_dir)
            (output_dir / "qa_tuning_experiment_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-robust-loss":
            output = build_ahs_robust_loss_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(json.dumps({"status": "built", "experiment_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-ahs-robust-loss":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_robust_loss_experiment(root, output_dir)
            (output_dir / "qa_robust_loss_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "train-ahs-ablation":
            output = build_ahs_ablation_experiment(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
            )
            print(json.dumps({"status": "built", "experiment_path": str(output)}, indent=2))
            return 0
        if args.command == "audit-ahs-ablation":
            output_dir = (
                root
                / "artifacts"
                / "experiments"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
            )
            report = audit_ahs_ablation_experiment(root, output_dir)
            (output_dir / "qa_ablation_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "review-ahs-diagnostics":
            output = build_ahs_diagnostic_review(
                root,
                args.release,
                args.split,
                args.preprocessor,
                args.experiment,
                args.review,
            )
            print(
                json.dumps(
                    {"status": "built", "review_path": str(output)}, indent=2
                )
            )
            return 0
        if args.command == "audit-diagnostic-review":
            output_dir = (
                root
                / "artifacts"
                / "reviews"
                / args.release
                / args.split
                / args.preprocessor
                / args.experiment
                / args.review
            )
            report = audit_ahs_diagnostic_review(root, output_dir)
            (output_dir / "qa_diagnostic_review_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report["summary"] | {"status": report["status"]}, indent=2))
            return 0 if report["status"] == "passed" else 1
    except (FileNotFoundError, FileExistsError, KeyError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _fetch_source(root: Path, source: dict[str, object]) -> dict[str, object]:
    artifacts = source.get("artifacts", [])
    if not artifacts:
        raise ValueError(f"source {source['source_id']} has no approved artifacts")
    destination = (
        root / "data" / "raw" / "public" / str(source["source_id"]) / str(source["release"])
    )
    destination.mkdir(parents=True, exist_ok=True)
    statuses = []
    for artifact in artifacts:
        path = destination / artifact["name"]
        if path.exists():
            if sha256_file(path) != artifact["sha256"]:
                raise ValueError(f"existing raw artifact has checksum drift: {path}")
            statuses.append({"artifact": path.name, "status": "already_present_verified"})
            continue
        temporary = path.with_suffix(path.suffix + ".partial")
        try:
            with urlopen(artifact["url"], timeout=120) as response, temporary.open("wb") as out:
                shutil.copyfileobj(response, out)
            if sha256_file(temporary) != artifact["sha256"]:
                raise ValueError(f"downloaded artifact has unexpected checksum: {path.name}")
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()
        statuses.append({"artifact": path.name, "status": "downloaded_verified"})
    return {
        "source_id": source["source_id"],
        "release": source["release"],
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": statuses,
    }


def _validate_raw(root: Path, source: dict[str, object]) -> dict[str, object]:
    raw_dir = (
        root / "data" / "raw" / "public" / str(source["source_id"]) / str(source["release"])
    )
    checks = []
    for artifact in source.get("artifacts", []):
        path = raw_dir / artifact["name"]
        actual_hash = sha256_file(path) if path.is_file() else None
        actual_bytes = path.stat().st_size if path.is_file() else None
        passed = actual_hash == artifact["sha256"] and actual_bytes == artifact["bytes"]
        checks.append(
            {
                "artifact": artifact["name"],
                "status": "passed" if passed else "failed",
                "expected_sha256": artifact["sha256"],
                "actual_sha256": actual_hash,
                "expected_bytes": artifact["bytes"],
                "actual_bytes": actual_bytes,
            }
        )
    return {
        "source_id": source["source_id"],
        "release": source["release"],
        "status": "passed" if checks and all(c["status"] == "passed" for c in checks) else "failed",
        "checks": checks,
    }


if __name__ == "__main__":
    raise SystemExit(main())
