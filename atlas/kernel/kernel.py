from datetime import datetime
from typing import Any, Dict, List, Optional

from atlas.agents import GeneralAgent, PlannerAgent
from atlas.config.settings import AtlasSettings, settings
from atlas.kernel.agent_manager import AgentManager
from atlas.kernel.capability_manager import CapabilityManager
from atlas.kernel.event_bus import EventBus
from atlas.kernel.llm_manager import LLMManager
from atlas.kernel.registry import ComponentRegistry
from atlas.kernel.tool_manager import ToolManager
from atlas.llm import MockLLMProvider
from atlas.memory.execution_memory import ExecutionMemory
from atlas.tools import CalculatorTool, ExcelTool, FileInfoTool
from atlas.utils.logger import logger


class AtlasKernel:
    """
    Núcleo principal de Atlas AI Platform.

    Coordina componentes, agentes, proveedores LLM,
    herramientas, capacidades, eventos y memoria.
    """

    def __init__(
        self,
        configuration: Optional[AtlasSettings] = None,
    ) -> None:
        self.settings = configuration or settings

        self.registry = ComponentRegistry()
        self.event_bus = EventBus()

        self.capability_manager = CapabilityManager(
            self.event_bus
        )

        self.llm_manager = LLMManager(
            self.event_bus
        )

        self.tool_manager = ToolManager(
            self.event_bus
        )

        self.agent_manager = AgentManager(
            self.event_bus
        )

        self.execution_memory = ExecutionMemory(
            self.settings.memory_dir
        )

        self.started = False
        self.started_at: Optional[datetime] = None

    def start(self) -> None:
        """
        Inicia Atlas AI Platform.
        """
        if self.started:
            logger.warning(
                "Atlas Kernel ya está iniciado."
            )
            return

        logger.info(
            "Iniciando Atlas AI Platform..."
        )

        self.settings.create_directories()

        logger.info(
            "Directorios del sistema verificados."
        )

        self._register_core_components()
        self._register_default_llm()
        self._register_default_tools()
        self._register_default_capabilities()
        self._register_default_agents()

        self.started = True
        self.started_at = datetime.now()

        self.event_bus.publish(
            "kernel.started",
            {
                "application": self.settings.app_name,
                "version": self.settings.version,
                "started_at": self.started_at.isoformat(),
            },
        )

        logger.info(
            "Atlas Kernel iniciado correctamente. Versión %s",
            self.settings.version,
        )

    def _register_core_components(self) -> None:
        """
        Registra los componentes centrales.
        """
        self.registry.register(
            "configuration",
            self.settings,
        )

        self.registry.register(
            "component_registry",
            self.registry,
        )

        self.registry.register(
            "event_bus",
            self.event_bus,
        )

        self.registry.register(
            "capability_manager",
            self.capability_manager,
        )

        self.registry.register(
            "llm_manager",
            self.llm_manager,
        )

        self.registry.register(
            "tool_manager",
            self.tool_manager,
        )

        self.registry.register(
            "agent_manager",
            self.agent_manager,
        )

        self.registry.register(
            "execution_memory",
            self.execution_memory,
        )

        logger.info(
            "Componentes centrales registrados: %s",
            self.registry.count(),
        )

    def _register_default_llm(self) -> None:
        """
        Registra los proveedores LLM predeterminados.
        """
        self.llm_manager.register(
            MockLLMProvider(),
            make_default=True,
        )

        logger.info(
            "Proveedores LLM registrados: %s",
            self.llm_manager.count(),
        )

    def _register_default_tools(self) -> None:
        """
        Registra las herramientas predeterminadas.
        """
        self.tool_manager.register(
            CalculatorTool()
        )

        self.tool_manager.register(
            FileInfoTool()
        )

        self.tool_manager.register(
            ExcelTool()
        )

        logger.info(
            "Herramientas registradas: %s",
            self.tool_manager.count(),
        )

    def _register_default_capabilities(self) -> None:
        """
        Registra las capacidades predeterminadas.
        """
        self.capability_manager.register(
            "mathematics",
            "calculator",
        )

        self.capability_manager.register(
            "filesystem",
            "file-info",
        )

        self.capability_manager.register(
            "spreadsheet",
            "excel",
        )

        logger.info(
            "Capacidades registradas: %s",
            self.capability_manager.count(),
        )

    def _register_default_agents(self) -> None:
        """
        Registra los agentes predeterminados.
        """
        self.agent_manager.register(
            PlannerAgent(
                llm_manager=self.llm_manager,
                tool_manager=self.tool_manager,
                capability_manager=self.capability_manager,
            )
        )

        self.agent_manager.register(
            GeneralAgent(
                self.llm_manager
            )
        )

        logger.info(
            "Agentes registrados: %s",
            self.agent_manager.count(),
        )

    def execute(
        self,
        task: str,
        agent_name: str = "planner-agent",
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea mediante un agente
        y guarda el resultado en memoria.
        """
        self._ensure_started()

        normalized_task = task.strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        result = self.agent_manager.execute(
            agent_name=agent_name,
            task=normalized_task,
        )

        memory_record = self.execution_memory.save(
            task=normalized_task,
            result=result,
            metadata={
                "execution_type": "agent",
                "agent": agent_name,
                "intent": result.get("intent"),
                "selected_tool": result.get(
                    "selected_tool"
                ),
                "provider": result.get("provider"),
                "model": result.get("model"),
            },
        )

        self.event_bus.publish(
            "memory.execution.saved",
            memory_record,
        )

        return result

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta directamente una herramienta.
        """
        self._ensure_started()

        normalized_tool_name = tool_name.strip().lower()

        if not normalized_tool_name:
            raise ValueError(
                "El nombre de la herramienta no puede estar vacío."
            )

        result = self.tool_manager.execute(
            tool_name=normalized_tool_name,
            **kwargs,
        )

        memory_record = self.execution_memory.save(
            task=(
                f"Ejecutar herramienta '{normalized_tool_name}' "
                f"con argumentos {kwargs}"
            ),
            result=result,
            metadata={
                "execution_type": "tool",
                "tool": normalized_tool_name,
            },
        )

        self.event_bus.publish(
            "memory.execution.saved",
            memory_record,
        )

        return result

    def execute_capability(
        self,
        capability_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Resuelve una capacidad y ejecuta su herramienta.
        """
        self._ensure_started()

        normalized_capability = (
            capability_name.strip().lower()
        )

        if not normalized_capability:
            raise ValueError(
                "El nombre de la capacidad no puede estar vacío."
            )

        tool_name = self.capability_manager.resolve(
            normalized_capability
        )

        result = self.tool_manager.execute(
            tool_name=tool_name,
            **kwargs,
        )

        memory_record = self.execution_memory.save(
            task=(
                f"Ejecutar capacidad '{normalized_capability}' "
                f"mediante '{tool_name}' con argumentos {kwargs}"
            ),
            result=result,
            metadata={
                "execution_type": "capability",
                "capability": normalized_capability,
                "tool": tool_name,
            },
        )

        self.event_bus.publish(
            "memory.execution.saved",
            memory_record,
        )

        return result

    def status(self) -> Dict[str, Any]:
        """
        Devuelve el estado completo del Kernel.
        """
        return {
            "application": self.settings.app_name,
            "version": self.settings.version,
            "environment": self.settings.environment,
            "started": self.started,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "registered_components": self.registry.count(),
            "component_names": self.registry.list_names(),
            "registered_agents": self.agent_manager.count(),
            "agent_names": self.agent_manager.list_names(),
            "registered_llm_providers": self.llm_manager.count(),
            "llm_provider_names": self.llm_manager.list_names(),
            "default_llm_provider": (
                self.llm_manager.default_provider
            ),
            "registered_tools": self.tool_manager.count(),
            "tool_names": self.tool_manager.list_names(),
            "registered_capabilities": (
                self.capability_manager.count()
            ),
            "capability_names": (
                self.capability_manager.list_names()
            ),
            "capabilities": (
                self.capability_manager.list_capabilities()
            ),
            "stored_executions": (
                self.execution_memory.count()
            ),
            "event_types": self.event_bus.count_events(),
            "event_listeners": (
                self.event_bus.count_listeners()
            ),
        }

    def get_execution_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve el historial de ejecuciones.
        """
        return self.execution_memory.get_history(
            limit=limit
        )

    def get_last_execution(
        self,
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve la última ejecución.
        """
        return self.execution_memory.get_last()

    def stop(self) -> None:
        """
        Detiene Atlas AI Platform.
        """
        if not self.started:
            logger.warning(
                "Atlas Kernel no está iniciado."
            )
            return

        stopped_at = datetime.now()

        self.event_bus.publish(
            "kernel.stopping",
            {
                "application": self.settings.app_name,
                "version": self.settings.version,
                "stopped_at": stopped_at.isoformat(),
            },
        )

        logger.info(
            "Deteniendo Atlas AI Platform..."
        )

        self.started = False

        self.event_bus.publish(
            "kernel.stopped",
            {
                "application": self.settings.app_name,
                "version": self.settings.version,
                "stopped_at": stopped_at.isoformat(),
            },
        )

        logger.info(
            "Atlas Kernel detenido correctamente."
        )

    def _ensure_started(self) -> None:
        """
        Verifica que el Kernel esté iniciado.
        """
        if not self.started:
            raise RuntimeError(
                "Atlas Kernel debe estar iniciado "
                "antes de ejecutar tareas."
            )
