from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AtlasSettings:
    """Configuración central de Atlas AI Platform."""

    app_name: str = "Atlas AI Platform"
    version: str = "0.5.0"
    environment: str = "development"

    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    memory_dir: Path = BASE_DIR / "data" / "memory"
    uploads_dir: Path = BASE_DIR / "data" / "uploads"
    outputs_dir: Path = BASE_DIR / "data" / "outputs"

    def create_directories(self) -> None:
        """Crea las carpetas necesarias para ejecutar Atlas."""
        directories = [
            self.data_dir,
            self.memory_dir,
            self.uploads_dir,
            self.outputs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


settings = AtlasSettings()
