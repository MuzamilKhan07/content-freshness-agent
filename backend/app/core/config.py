from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine base paths reliably
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    ENVIRONMENT: str = "development"
    OPENAI_API_KEY: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ADDITIONAL_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    DATASET_PATH: str = "data/ps11_content_inventory.csv"
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def resolve_dataset_path(self) -> Path:
        """Resolve the dataset path reliably regardless of cwd."""
        candidate = Path(self.DATASET_PATH)
        if candidate.is_absolute() and candidate.exists():
            return candidate
            
        # Try relative to project root
        project_relative = (PROJECT_ROOT / self.DATASET_PATH).resolve()
        if project_relative.exists():
            return project_relative
            
        # Try relative to current working directory
        cwd_relative = Path(self.DATASET_PATH).resolve()
        if cwd_relative.exists():
            return cwd_relative
            
        # Try inside backend or data directly
        fallback_data = (PROJECT_ROOT / "data" / "ps11_content_inventory.csv").resolve()
        if fallback_data.exists():
            return fallback_data
            
        # Return candidate relative to project root even if not yet found
        return project_relative

settings = Settings()
