"""
train_model.py
==============
CLI script to train the ScouterFRC prediction model and save it to disk.

Usage (from backend/):
    python -m scripts.train_model
    python -m scripts.train_model --min-samples 5 --verbose

Can also be run directly:
    python scripts/train_model.py

Requires POSTGRES_URL (or DATABASE_URL) in environment / .env.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure app package is importable when run from backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_model")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train ScouterFRC gradient boosting prediction model."
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=10,
        help="Minimum number of training samples required (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build feature matrix and report stats without training",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("ScouterFRC Prediction Model Trainer")
    logger.info("=" * 50)

    # ── Import after sys.path patch ───────────────────────────────────────────
    try:
        from app.db.session import SessionLocal
        from app.tasks.prediction_tasks import _build_training_data
        from app.services.predictor import MODEL_PATH, save_model, build_match_feature_row
    except ImportError as e:
        logger.error("Import failed — are you running from the backend/ directory? %s", e)
        return 1

    # ── Load data ─────────────────────────────────────────────────────────────
    logger.info("Connecting to database and loading training data...")
    t0 = time.perf_counter()

    try:
        with SessionLocal() as db:
            X_raw, y = _build_training_data(db)
    except Exception as e:
        logger.error("Database error: %s", e)
        return 1

    elapsed = time.perf_counter() - t0
    logger.info("Loaded %d training samples in %.2fs", len(X_raw), elapsed)

    if not X_raw:
        logger.warning("No training data found. Process some match videos first.")
        return 1

    import numpy as np
    y_arr = np.array(y)
    logger.info(
        "Class balance — red wins: %d (%.1f%%) | blue wins: %d (%.1f%%)",
        int(y_arr.sum()), 100 * float(y_arr.mean()),
        int((1 - y_arr).sum()), 100 * (1 - float(y_arr.mean())),
    )

    if args.dry_run:
        logger.info("Dry run complete. Feature matrix shape: (%d, %d)", len(X_raw), len(X_raw[0]))
        return 0

    if len(X_raw) < args.min_samples:
        logger.error(
            "Only %d samples available — need at least %d. "
            "Increase data or lower --min-samples.",
            len(X_raw), args.min_samples,
        )
        return 1

    # ── Train ─────────────────────────────────────────────────────────────────
    logger.info("Training GradientBoostingClassifier...")
    t1 = time.perf_counter()

    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score, StratifiedKFold
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        X = np.array(X_raw)

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.85,
                min_samples_leaf=2,
                random_state=42,
            )),
        ])

        # Cross-validation
        if len(X) >= 20:
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X, y_arr, cv=cv, scoring="roc_auc")
            logger.info(
                "5-fold CV ROC-AUC: %.4f ± %.4f (min=%.4f, max=%.4f)",
                cv_scores.mean(), cv_scores.std(), cv_scores.min(), cv_scores.max(),
            )

            acc_scores = cross_val_score(model, X, y_arr, cv=cv, scoring="accuracy")
            logger.info(
                "5-fold CV Accuracy: %.4f ± %.4f",
                acc_scores.mean(), acc_scores.std(),
            )
        else:
            logger.warning("< 20 samples — skipping cross-validation, training on full set.")

        # Final fit
        model.fit(X, y_arr)
        elapsed_train = time.perf_counter() - t1
        logger.info("Training complete in %.2fs", elapsed_train)

    except Exception as e:
        logger.error("Training failed: %s", e)
        return 1

    # ── Save ──────────────────────────────────────────────────────────────────
    try:
        save_model(model)
        size_kb = MODEL_PATH.stat().st_size / 1024
        logger.info("Model saved to %s (%.1f KB)", MODEL_PATH, size_kb)
    except Exception as e:
        logger.error("Failed to save model: %s", e)
        return 1

    logger.info("=" * 50)
    logger.info("Done. Model is ready. Use POST /predictions/events/{id}/compute to cache predictions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())