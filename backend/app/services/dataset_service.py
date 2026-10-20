import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.models.dataset import (
    DashboardDistributionsResponse,
    DashboardSummaryResponse,
    DatasetPreviewResponse,
    DatasetStatusResponse,
    DistributionItem,
    DocumentListResponse,
    DocumentRecord,
)

logger = logging.getLogger("freshguard.dataset")

ALLOWED_SORT_FIELDS = {
    "content_id",
    "title",
    "content_type",
    "platform",
    "author",
    "created_date",
    "last_updated",
    "last_reviewed",
    "page_views_90d",
    "linked_from_count",
    "mentions_deprecated_tool",
    "has_broken_links",
    "subject_area",
    "staleness_score",
    "recommended_action",
}


class DatasetService:
    _extra_records: List[Dict[str, Any]] = []

    def __init__(self, dataset_path: Optional[Path] = None):
        self._custom_path = dataset_path

    @classmethod
    def add_document_record(cls, record: Dict[str, Any]) -> None:
        """Add an in-memory document record (e.g. from live URL imports)."""
        cls._extra_records.append(record)



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
            df = pd.read_csv(
                path,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
                on_bad_lines="warn",
            )

            if self._extra_records:
                extra_df = pd.DataFrame(self._extra_records)
                df = pd.concat([df, extra_df], ignore_index=True) if not df.empty else extra_df

            if df.empty:
                warnings.append("Dataset file is empty (0 records found).")

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

    def _row_to_document_record(self, row: Dict[str, Any]) -> DocumentRecord:
        """Convert a raw CSV dictionary row into a strongly typed DocumentRecord."""
        # Parse boolean flags safely
        dep_val = str(row.get("mentions_deprecated_tool", "")).strip().lower()
        mentions_deprecated = dep_val in ("true", "1", "yes")

        broken_val = str(row.get("has_broken_links", "")).strip().lower()
        has_broken = broken_val in ("true", "1", "yes")

        # Parse numeric fields safely
        def parse_int(val: Any) -> Optional[int]:
            if val is None or val == "":
                return None
            try:
                return int(float(str(val).strip()))
            except (ValueError, TypeError):
                return None

        def parse_float(val: Any) -> Optional[float]:
            if val is None or val == "":
                return None
            try:
                return round(float(str(val).strip()), 4)
            except (ValueError, TypeError):
                return None

        def clean_str(val: Any) -> Optional[str]:
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        return DocumentRecord(
            content_id=str(row.get("content_id", "UNKNOWN")).strip(),
            title=str(row.get("title", "Untitled Document")).strip(),
            content_type=str(row.get("content_type", "Unspecified")).strip(),
            platform=str(row.get("platform", "Unknown")).strip(),
            author=clean_str(row.get("author")),
            created_date=clean_str(row.get("created_date")),
            last_updated=clean_str(row.get("last_updated")),
            last_reviewed=clean_str(row.get("last_reviewed")),
            page_views_90d=parse_int(row.get("page_views_90d")),
            linked_from_count=parse_int(row.get("linked_from_count")),
            mentions_deprecated_tool=mentions_deprecated,
            has_broken_links=has_broken,
            subject_area=clean_str(row.get("subject_area")),
            staleness_score=parse_float(row.get("staleness_score")),
            recommended_action=clean_str(row.get("recommended_action")),
            raw_data=row,
        )

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

        return DatasetStatusResponse(
            available=True,
            record_count=len(df),
            columns=list(df.columns),
            warnings=warnings,
            file_path=rel_path,
        )

    def get_preview(self, limit: int = 10) -> DatasetPreviewResponse:
        """Returns a preview of the initial dataset records (capped at 10)."""
        df, warnings = self.load_dataset()
        if df is None or df.empty:
            return DatasetPreviewResponse(
                available=False,
                total_records=0,
                preview_count=0,
                columns=[],
                preview=[],
                warnings=warnings,
            )

        total_records = len(df)
        clamped_limit = max(0, min(limit, 10))
        subset = df.head(clamped_limit)
        records = subset.to_dict(orient="records")

        return DatasetPreviewResponse(
            available=True,
            total_records=total_records,
            preview_count=len(records),
            columns=list(df.columns),
            preview=records,
            warnings=warnings,
        )

    def get_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> DocumentListResponse:
        """
        Query paginated document inventory with search, filtering, and sorting.
        """
        df, _ = self.load_dataset()
        if df is None or df.empty:
            return DocumentListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                available_platforms=[],
                available_content_types=[],
            )

        # Extract unique platforms and content types for filter controls
        unique_platforms = sorted([p for p in df["platform"].unique() if p])
        unique_content_types = sorted([c for c in df["content_type"].unique() if c])

        working_df = df.copy()

        # 1. Global Search across multiple text fields
        if search and search.strip():
            term = search.strip().lower()
            mask = pd.Series(False, index=working_df.index)
            searchable_cols = [
                "content_id",
                "title",
                "platform",
                "content_type",
                "subject_area",
                "author",
                "recommended_action",
            ]
            for col in searchable_cols:
                if col in working_df.columns:
                    mask |= working_df[col].astype(str).str.lower().str.contains(term, regex=False)
            working_df = working_df[mask]

        # 2. Filter by Platform
        if platform and platform.strip() and platform.strip().lower() != "all":
            plat_target = platform.strip().lower()
            working_df = working_df[working_df["platform"].str.strip().str.lower() == plat_target]

        # 3. Filter by Content Type
        if content_type and content_type.strip() and content_type.strip().lower() != "all":
            ct_target = content_type.strip().lower()
            working_df = working_df[working_df["content_type"].str.strip().str.lower() == ct_target]

        # 4. Filter by Status / Action (e.g., recommended_action)
        if status and status.strip() and status.strip().lower() != "all":
            st_target = status.strip().lower()
            working_df = working_df[working_df["recommended_action"].str.strip().str.lower() == st_target]

        # 5. Sorting
        if sort_by and sort_by.strip():
            sort_field = sort_by.strip().lower()
            if sort_field not in ALLOWED_SORT_FIELDS:
                raise ValueError(
                    f"Unsupported sort field '{sort_field}'. Supported fields: {sorted(ALLOWED_SORT_FIELDS)}"
                )

            ascending = sort_order.strip().lower() != "desc"

            # Parse sorting values correctly for numbers and booleans
            if sort_field in ("page_views_90d", "linked_from_count", "staleness_score"):
                numeric_series = pd.to_numeric(working_df[sort_field], errors="coerce").fillna(0)
                working_df = working_df.iloc[numeric_series.argsort(kind="stable").values]
                if not ascending:
                    working_df = working_df.iloc[::-1]
            elif sort_field in ("mentions_deprecated_tool", "has_broken_links"):
                bool_series = working_df[sort_field].astype(str).str.lower().isin(["true", "1", "yes"])
                working_df = working_df.iloc[bool_series.argsort(kind="stable").values]
                if not ascending:
                    working_df = working_df.iloc[::-1]
            else:
                # String sort (case-insensitive)
                working_df = working_df.sort_values(
                    by=sort_field,
                    ascending=ascending,
                    key=lambda s: s.str.lower(),
                    kind="stable",
                )

        total_matching = len(working_df)
        total_pages = max(1, math.ceil(total_matching / page_size)) if total_matching > 0 else 0
        current_page = max(1, page)

        # Slice pagination
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        paged_df = working_df.iloc[start_idx:end_idx]

        # Convert to records
        items = [self._row_to_document_record(r) for r in paged_df.to_dict(orient="records")]

        return DocumentListResponse(
            items=items,
            total=total_matching,
            page=current_page,
            page_size=page_size,
            total_pages=total_pages,
            available_platforms=unique_platforms,
            available_content_types=unique_content_types,
        )

    def get_document_by_id(self, document_id: str) -> Optional[DocumentRecord]:
        """Fetch complete document metadata by its identifier."""
        df, _ = self.load_dataset()
        if df is None or df.empty:
            return None

        target = document_id.strip().lower()
        match = df[df["content_id"].astype(str).str.strip().str.lower() == target]
        if match.empty:
            return None

        row = match.iloc[0].to_dict()
        return self._row_to_document_record(row)

    def get_dashboard_summary(self) -> DashboardSummaryResponse:
        """Calculate high-level KPI metrics from dataset records."""
        df, _ = self.load_dataset()
        if df is None or df.empty:
            return DashboardSummaryResponse(
                total_documents=0,
                distinct_platforms=0,
                distinct_content_types=0,
                missing_update_dates=0,
                deprecated_references=0,
                broken_links=0,
                missing_metadata_count=0,
                platforms_list=[],
                content_types_list=[],
            )

        total = len(df)
        platforms = sorted([p for p in df["platform"].unique() if p])
        content_types = sorted([c for c in df["content_type"].unique() if c])

        # Missing update dates
        missing_updates = int(
            (df["last_updated"].isna() | (df["last_updated"].str.strip() == "")).sum()
        )

        # Deprecated tool flags
        deprecated_count = int(
            df["mentions_deprecated_tool"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()
        )

        # Broken link flags
        broken_count = int(
            df["has_broken_links"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()
        )

        # Missing or incomplete metadata check (empty author, empty dates, or empty subject)
        metadata_incomplete_mask = (
            df["author"].isna()
            | (df["author"].str.strip() == "")
            | df["subject_area"].isna()
            | (df["subject_area"].str.strip() == "")
            | df["last_reviewed"].isna()
            | (df["last_reviewed"].str.strip() == "")
            | df["last_updated"].isna()
            | (df["last_updated"].str.strip() == "")
        )
        missing_metadata_count = int(metadata_incomplete_mask.sum())

        return DashboardSummaryResponse(
            total_documents=total,
            distinct_platforms=len(platforms),
            distinct_content_types=len(content_types),
            missing_update_dates=missing_updates,
            deprecated_references=deprecated_count,
            broken_links=broken_count,
            missing_metadata_count=missing_metadata_count,
            platforms_list=platforms,
            content_types_list=content_types,
        )

    def get_dashboard_distributions(self) -> DashboardDistributionsResponse:
        """Calculate aggregate distributions for frontend charts."""
        df, _ = self.load_dataset()
        if df is None or df.empty:
            return DashboardDistributionsResponse()

        total = len(df)

        # 1. By Platform
        platform_counts = df["platform"].value_counts().to_dict()
        by_platform = [
            DistributionItem(
                label=k,
                count=int(v),
                percentage=round((int(v) / total) * 100, 1) if total > 0 else 0.0,
            )
            for k, v in platform_counts.items()
        ]

        # 2. By Content Type
        ct_counts = df["content_type"].value_counts().to_dict()
        by_content_type = [
            DistributionItem(
                label=k,
                count=int(v),
                percentage=round((int(v) / total) * 100, 1) if total > 0 else 0.0,
            )
            for k, v in ct_counts.items()
        ]

        # 3. By Recommended Action
        action_counts = df["recommended_action"].value_counts().to_dict()
        by_recommended_action = [
            DistributionItem(
                label=k,
                count=int(v),
                percentage=round((int(v) / total) * 100, 1) if total > 0 else 0.0,
            )
            for k, v in action_counts.items()
        ]

        # 4. By Reference Score Ranges (0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
        scores = pd.to_numeric(df["staleness_score"], errors="coerce").dropna()
        score_bins = [
            ("0.00 - 0.20 (Low)", (scores >= 0.0) & (scores <= 0.20)),
            ("0.21 - 0.40 (Mild)", (scores > 0.20) & (scores <= 0.40)),
            ("0.41 - 0.60 (Moderate)", (scores > 0.40) & (scores <= 0.60)),
            ("0.61 - 0.80 (High)", (scores > 0.60) & (scores <= 0.80)),
            ("0.81 - 1.00 (Critical)", (scores > 0.80) & (scores <= 1.00)),
        ]
        by_reference_score = [
            DistributionItem(
                label=label,
                count=int(mask.sum()),
                percentage=round((int(mask.sum()) / total) * 100, 1) if total > 0 else 0.0,
            )
            for label, mask in score_bins
        ]

        # 5. Signals
        dep_count = int(
            df["mentions_deprecated_tool"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()
        )
        broken_count = int(
            df["has_broken_links"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()
        )
        by_signals = {
            "deprecated_tool_references": dep_count,
            "clean_tool_references": total - dep_count,
            "broken_links_detected": broken_count,
            "intact_links": total - broken_count,
        }

        return DashboardDistributionsResponse(
            by_platform=by_platform,
            by_content_type=by_content_type,
            by_reference_score=by_reference_score,
            by_recommended_action=by_recommended_action,
            by_signals=by_signals,
        )


_dataset_service_instance: Optional[DatasetService] = None


def get_dataset_service() -> DatasetService:
    """Dependency provider for DatasetService singleton."""
    global _dataset_service_instance
    if _dataset_service_instance is None:
        _dataset_service_instance = DatasetService()
    return _dataset_service_instance

