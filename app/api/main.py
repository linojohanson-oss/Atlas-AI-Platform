from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from atlas.kernel.kernel import AtlasKernel


kernel = AtlasKernel()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_FILE = PROJECT_ROOT / "app" / "ui" / "index.html"


class ExecuteRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Instrucción que será procesada por Atlas AI.",
        examples=["Calculá el 18% de 1250 más 45"],
    )


class ExecuteResponse(BaseModel):
    success: bool
    prompt: str
    result: Any


class WorkflowExecuteRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="Objetivo que será procesado por el workflow.",
        examples=[
            "Diseñá una solución de IA generativa para analizar "
            "reclamos de clientes de un banco."
        ],
    )
    workflow: str = Field(
        default="enterprise_ai_solution",
        min_length=1,
        max_length=100,
        description="Nombre del workflow registrado.",
    )


class WorkflowExecuteResponse(BaseModel):
    success: bool
    prompt: str
    workflow: str
    result: Any


def serializar_resultado(valor: Any) -> Any:
    if valor is None:
        return None

    if isinstance(valor, (str, int, float, bool)):
        return valor

    if isinstance(valor, list):
        return [
            serializar_resultado(elemento)
            for elemento in valor
        ]

    if isinstance(valor, dict):
        return {
            clave: serializar_resultado(contenido)
            for clave, contenido in valor.items()
        }

    if hasattr(valor, "model_dump"):
        return serializar_resultado(valor.model_dump())

    if hasattr(valor, "to_dict"):
        return serializar_resultado(valor.to_dict())

    if hasattr(valor, "__dict__"):
        return {
            clave: serializar_resultado(contenido)
            for clave, contenido in vars(valor).items()
            if not clave.startswith("_")
        }

    return str(valor)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 80)
    print("INICIANDO ATLAS AI API")
    print("=" * 80)

    kernel.start()

    yield

    print("\n" + "=" * 80)
    print("DETENIENDO ATLAS AI API")
    print("=" * 80)

    kernel.stop()


app = FastAPI(
    title="Atlas AI Platform API",
    description=(
        "API REST de Atlas AI Platform para ejecutar agentes, "
        "herramientas y workflows multiagente."
    ),
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Sistema"], summary="Información general de Atlas")
def root():
    return {
        "name": "Atlas AI Platform",
        "version": "1.1.0",
        "status": "online",
        "dashboard": "/dashboard",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "execute": "/execute",
            "workflow_execute": "/workflows/execute",
            "workflow_history": "/workflows/history",
        },
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    if not DASHBOARD_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontró la interfaz web de Atlas en "
                f"{DASHBOARD_FILE}"
            ),
        )

    return FileResponse(
        path=DASHBOARD_FILE,
        media_type="text/html",
    )


@app.get("/health", tags=["Sistema"], summary="Comprobar el estado")
def health():
    return {
        "success": True,
        "service": "Atlas AI API",
        "kernel_started": bool(
            getattr(kernel, "started", False)
        ),
    }


@app.get("/status", tags=["Sistema"], summary="Estado del kernel")
def status():
    try:
        return {
            "success": True,
            "status": serializar_resultado(kernel.status()),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo consultar el estado del kernel: "
                f"{error}"
            ),
        ) from error


@app.post(
    "/execute",
    response_model=ExecuteResponse,
    tags=["Ejecución"],
    summary="Ejecutar una instrucción en Atlas",
)
def execute(request: ExecuteRequest):
    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="La instrucción no puede estar vacía.",
        )

    try:
        resultado = kernel.execute(prompt)

        return ExecuteResponse(
            success=True,
            prompt=prompt,
            result=serializar_resultado(resultado),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Atlas no pudo ejecutar la instrucción: "
                f"{error}"
            ),
        ) from error


@app.post(
    "/workflows/execute",
    response_model=WorkflowExecuteResponse,
    tags=["Workflows"],
    summary="Ejecutar un workflow multiagente",
)
def execute_workflow(request: WorkflowExecuteRequest):
    prompt = request.prompt.strip()
    workflow_name = request.workflow.strip().lower()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="El prompt no puede estar vacío.",
        )

    try:
        resultado = kernel.execute_workflow(
            prompt=prompt,
            workflow_name=workflow_name,
        )

        if resultado.get("status") == "FAILED":
            raise HTTPException(
                status_code=500,
                detail=resultado,
            )

        return WorkflowExecuteResponse(
            success=True,
            prompt=prompt,
            workflow=workflow_name,
            result=serializar_resultado(resultado),
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Atlas no pudo ejecutar el workflow: "
                f"{error}"
            ),
        ) from error


@app.get(
    "/workflows/history",
    tags=["Workflows"],
    summary="Consultar historial de workflows",
)
def workflow_history(limit: int = 20):
    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="El límite debe estar entre 1 y 500.",
        )

    return {
        "success": True,
        "count": min(
            kernel.workflow_trace.count(),
            limit,
        ),
        "history": serializar_resultado(
            kernel.get_workflow_history(limit=limit)
        ),
    }


@app.get(
    "/workflows/last",
    tags=["Workflows"],
    summary="Consultar el último workflow",
)
def last_workflow():
    return {
        "success": True,
        "workflow": serializar_resultado(
            kernel.get_last_workflow()
        ),
    }
