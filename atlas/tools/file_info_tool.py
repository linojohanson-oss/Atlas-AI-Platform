from pathlib import Path
from typing import Any, Dict

from atlas.tools.base_tool import BaseTool


class FileInfoTool(BaseTool):
    """
    Obtiene información básica y una vista previa
    de un archivo de texto.
    """

    name = "file-info"
    description = (
        "Inspecciona archivos y devuelve tamaño, extensión, "
        "cantidad de líneas y vista previa."
    )
    version = "1.0.0"

    TEXT_EXTENSIONS = {
        ".txt",
        ".md",
        ".py",
        ".json",
        ".csv",
        ".yaml",
        ".yml",
        ".html",
        ".css",
        ".js",
    }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        file_path_value = str(
            kwargs.get("file_path", "")
        ).strip()

        if not file_path_value:
            raise ValueError(
                "Debe indicar la ruta del archivo."
            )

        file_path = Path(file_path_value).expanduser()

        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        file_path = file_path.resolve()

        if not file_path.exists():
            raise FileNotFoundError(
                f"El archivo no existe: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"La ruta no corresponde a un archivo: {file_path}"
            )

        extension = file_path.suffix.lower()
        size_bytes = file_path.stat().st_size

        result: Dict[str, Any] = {
            "tool": self.name,
            "status": "completed",
            "input": {
                "file_path": str(file_path),
            },
            "result": {
                "name": file_path.name,
                "path": str(file_path),
                "extension": extension,
                "size_bytes": size_bytes,
                "is_text": extension in self.TEXT_EXTENSIONS,
            },
        }

        if extension in self.TEXT_EXTENSIONS:
            content = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            lines = content.splitlines()

            result["result"]["line_count"] = len(lines)
            result["result"]["character_count"] = len(content)
            result["result"]["preview"] = "\n".join(
                lines[:10]
            )

        return result