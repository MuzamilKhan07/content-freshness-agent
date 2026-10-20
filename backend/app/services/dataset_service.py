import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.models.dataset import (
    DatasetPreviewResponse,
    DatasetStatusResponse,
)

logger = logging.getLogger("freshguard.dataset")


class DatasetService:
    """Service responsible for loading, validating, and previewing the knowledge dataset."""

    def __init__(self, dataset_path: Optional[Path] = None):
        self._custom_path = dataset_path

    @property
    def file_path(self) -> Path:
        """Resolve current dataset file path."""
        if self._custom_path:
            return self._custom_path
        return settings.resolve_dataset_path()

    def get_relative_path(self, target_path: Path) -> str:
        """Sanitize path for public response, returning relative to project root."""
        try:
            return str(target_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return target_path.name

    def load_dataset(self) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Loads the dataset CSV safely into a pandas DataFrame.
        Preserves original column names, source values, and handles missing data.
        Returns (DataFrame, warnings).
        """
        path = self.file_path
        warnings: List[str] = []

        if not path.exists():
            msg = f"Dataset file does not exist at '{self.get_relative_path(path)}'."
            logger.warning(msg)
            warnings.append(msg)
            return None, warnings

        if not path.is_file():
            msg = f"Dataset path '{self.get_relative_path(path)}' is not a file."
            logger.warning(msg)
            warnings.append(msg)
            return None, warnings

        try:
            # Read CSV preserving original headers and content
            # keep_default_na=False keeps empty cells as empty strings or we can replace NaN with None
            df = pd.read_csv(
                path,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
                on_bad_lines="warn",
            )
            
            # Check for empty dataframe
            if df.empty:
                warnings.append("Dataset file is empty (0 records found).")
            
            # Identify columns with missing or empty values
            empty_counts = (df == "").sum()
            partially_empty = empty_counts[empty_counts > 0]
            if not partially_empty.empty:
                cols_with_blanks = list(partially_empty.index)
                if len(cols_with_blanks) > 5:
                    warnings.append(
                        f"Found empty entries in {len(cols_with_blanks)} columns (including {', '.join(cols_with_blanks[:3])})."
                    )
                else:
                    warnings.append(
                        f"Found empty entries in columns: {', '.join(cols_with_blanks)}."
                    )

            return df, warnings

        except pd.errors.EmptyDataError:
            msg = "Dataset file is completely empty or header is missing."
            logger.error(msg)
            warnings.append(msg)
            return None, warnings
        except pd.errors.ParserError as pe:
            msg = f"CSV parsing error encountered: {str(pe).splitlines()[0]}"
            logger.error(msg)
            warnings.append(msg)
            return None, warnings
        except Exception as exc:
            msg = f"Unexpected error reading dataset: {exc.__class__.__name__}"
            logger.error(msg)
            warnings.append(msg)
            return None, warnings

    def get_status(self) -> DatasetStatusResponse:
        """Returns structured status of the dataset."""
        path = self.file_path
        rel_path = self.get_relative_path(path)

        if not path.exists():
            return DatasetStatusResponse(
                available=False,
                record_count=0,
                columns=[],
                warnings=[f"Dataset file '{rel_path}' not found."],
                file_path=rel_path,
            )

        df, warnings = self.load_dataset()
        if df is None:
            return DatasetStatusResponse(
                available=False,
                record_count=0,
                columns=[],
                warnings=warnings,
                file_path=rel_path,
            )

        columns = list(df.columns)
        return DatasetStatusResponse(
            available=True,
            record_count=len(df),
            columns=columns,
            warnings=warnings,
            file_path=rel_path,
        )

    def get_preview(self, limit: int = 10) -> DatasetPreviewResponse:
        """
        Returns a limited preview of records (default max 10).
        Preserves original values while ensuring valid JSON serializability.
        """
        df, warnings = self.load_dataset()
        if df is None:
            return DatasetPreviewResponse(
                available=False,
                total_records=0,
                preview_count=0,
                columns=[],
                preview=[],
                warnings=warnings,
            )

        total_records = len(df)
        columns = list(df.columns)
        clamped_limit = max(0, min(limit, 10))
        subset = df.head(clamped_limit)

        # Convert to records dictionary, safely replacing NaN/empty with None or string
        records: List[Dict[str, Any]] = subset.to_dict(orient="records")

        return DatasetPreviewResponse(
            available=True,
            total_records=total_records,
            preview_count=len(records),
            columns=columns,
            preview=records,
            warnings=warnings,
        )


def get_dataset_service() -> DatasetService:
    """Dependency provider for DatasetService."""
    return DatasetService()
