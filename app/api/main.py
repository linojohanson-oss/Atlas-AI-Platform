from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import asyncio

from app.api.websocket_manager import websocket_manager
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from atlas.kernel.kernel import AtlasKernel


kernel = AtlasKernel()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

UI_DIR = PROJECT_ROOT / "app" / "ui"
DASHBOARD_FILE = UI_DIR / "index.html"
STUDIO_FILE = UI_DIR / "studio.html"

CSS_DIR = UI_DIR / "css"
JS_DIR = UI_DIR / "js"


class ExecuteRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="InstrucciÃ³n que serÃ¡ procesada por Atlas AI.",
        examples=["CalculÃ¡ el 18% de 1250 mÃ¡s 45"],
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
        description="Objetivo que serÃ¡ procesado por el workflow.",
        examples=[
            "DiseÃ±Ã¡ una soluciÃ³n de IA generativa para analizar "
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
    event_loop = asyncio.get_running_loop()

    websocket_manager.start(
        event_bus=kernel.workflow_engine.event_bus,
        event_loop=event_loop,
    )

    print(
        "Atlas Studio WebSocket iniciado: "
        f"{websocket_manager.summary()}"
    )

    yield

    print("\n" + "=" * 80)
    print("DETENIENDO ATLAS AI API")
    print("=" * 80)

    websocket_manager.stop()
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


# =============================================================================
# ARCHIVOS ESTÃTICOS DE ATLAS STUDIO
# =============================================================================

app.mount(
    "/css",
    StaticFiles(directory=str(CSS_DIR)),
    name="atlas-css",
)

app.mount(
    "/js",
    StaticFiles(directory=str(JS_DIR)),
    name="atlas-js",
)


# =============================================================================
# SISTEMA E INTERFACES WEB
# =============================================================================

@app.get("/", tags=["Sistema"], summary="InformaciÃ³n general de Atlas")
def root():
    return {
        "name": "Atlas AI Platform",
        "version": "1.1.0",
        "status": "online",
        "dashboard": "/dashboard",
        "studio": "/studio",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "execute": "/execute",
            "workflow_execute": "/workflows/execute",
            "workflow_history": "/workflows/history",
            "workflow_last": "/workflows/last",
            "studio_status": "/studio/status",
            "workflow_websocket": "/ws/workflows",
        },
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    if not DASHBOARD_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontrÃ³ la interfaz web de Atlas en "
                f"{DASHBOARD_FILE}"
            ),
        )

    return FileResponse(
        path=DASHBOARD_FILE,
        media_type="text/html",
    )


@app.get("/studio", include_in_schema=False)
def studio():
    if not STUDIO_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontrÃ³ Atlas Studio en "
                f"{STUDIO_FILE}"
            ),
        )

    return FileResponse(
        path=STUDIO_FILE,
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


# =============================================================================
# EJECUCIÃ“N GENERAL
# =============================================================================

@app.post(
    "/execute",
    response_model=ExecuteResponse,
    tags=["EjecuciÃ³n"],
    summary="Ejecutar una instrucciÃ³n en Atlas",
)
def execute(request: ExecuteRequest):
    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="La instrucciÃ³n no puede estar vacÃ­a.",
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
                "Atlas no pudo ejecutar la instrucciÃ³n: "
                f"{error}"
            ),
        ) from error


# =============================================================================
# WORKFLOWS
# =============================================================================

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
            detail="El prompt no puede estar vacÃ­o.",
        )

    try:
        resultado = kernel.execute_workflow(
            workflow_id=workflow_name,
            request=prompt,
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

    history = kernel.get_workflow_executions(
        limit=limit
    )

    return {
        "success": True,
        "count": len(history),
        "history": serializar_resultado(
            history
        ),
    }


@app.get(
    "/workflows/last",
    tags=["Workflows"],
    summary="Consultar el último workflow",
)
def last_workflow():
    history = kernel.get_workflow_executions(
        limit=1
    )

    workflow = (
        history[0]
        if history
        else None
    )

    return {
        "success": True,
        "workflow": serializar_resultado(
            workflow
        ),
    }


# =============================================================================
# WEBSOCKET Y ESTADO DE ATLAS STUDIO
# =============================================================================

@app.websocket("/ws/workflows")
async def workflow_events_websocket(
    websocket: WebSocket,
):
    """
    Canal en tiempo real de eventos de workflows
    para Atlas Studio.
    """

    await websocket_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

    except Exception:
        websocket_manager.disconnect(websocket)

        try:
            await websocket.close()
        except Exception:
            pass


@app.get(
    "/studio/status",
    tags=["Atlas Studio"],
    summary="Estado del canal WebSocket",
)
def studio_status():
    return {
        "success": True,
        "websocket": websocket_manager.summary(),
        "event_bus": (
            kernel.workflow_engine
            .event_bus
            .summary()
        ),
    }
@app.get(
    "/studio/data",
    tags=["Atlas Studio"],
    summary="Estado completo del Atlas Studio",
)


def studio_data():
    """
    Devuelve toda la informaciÃ³n necesaria para
    alimentar Atlas Studio.
    """

    try:

        status = kernel.status()

        return {
            "success": True,

            "kernel": {
                "application": status.get("application"),
                "version": status.get("version"),
                "started": status.get("started"),
                "started_at": status.get("started_at"),
            },

            "organization": (
                status.get("organization", {})
            ),

            "department_runtime": (
                status.get(
                    "department_runtime",
                    {},
                )
            ),

            "executive": (
                status.get(
                    "executive_agent",
                    {},
                )
            ),

            "workflow_registry": (
                status.get(
                    "workflow_registry",
                    {},
                )
            ),

            "workflow_engine": (
                status.get(
                    "workflow_engine",
                    {},
                )
            ),

            "agents": {
                "count": (
                    status.get(
                        "registered_agents",
                        0,
                    )
                ),
                "names": (
                    status.get(
                        "agent_names",
                        [],
                    )
                ),
            },

            "tools": {
                "count": (
                    status.get(
                        "registered_tools",
                        0,
                    )
                ),
                "names": (
                    status.get(
                        "tool_names",
                        [],
                    )
                ),
            },

            "llm": {
                "count": (
                    status.get(
                        "registered_llm_providers",
                        0,
                    )
                ),
                "providers": (
                    status.get(
                        "llm_provider_names",
                        [],
                    )
                ),
                "default": (
                    status.get(
                        "default_llm_provider",
                    )
                ),
            },

            "capabilities": {
                "count": (
                    status.get(
                        "registered_capabilities",
                        0,
                    )
                ),
                "names": (
                    status.get(
                        "capability_names",
                        [],
                    )
                ),
                "details": (
                    status.get(
                        "capabilities",
                        [],
                    )
                ),
            },

            "metrics": {

                "components": (
                    status.get(
                        "registered_components",
                        0,
                    )
                ),

                "workflows": (
                    status.get(
                        "registered_workflows",
                        0,
                    )
                ),

                "stored_executions": (
                    status.get(
                        "stored_executions",
                        0,
                    )
                ),

                "event_types": (
                    status.get(
                        "event_types",
                        0,
                    )
                ),

                "event_listeners": (
                    status.get(
                        "event_listeners",
                        0,
                    )
                ),

            },

        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible obtener "
                "el estado del Studio: "
                f"{error}"
            ),
        ) from error


