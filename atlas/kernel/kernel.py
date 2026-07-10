from datetime import datetime
from typing import Dict, Optional

from atlas.agents import GeneralAgent
from atlas.config.settings import AtlasSettings, settings
from atlas.kernel.agent_manager import AgentManager
from atlas.kernel.event_bus import EventBus
from atlas.kernel.llm_manager import LLMManager
from atlas.kernel.registry import ComponentRegistry
from atlas.llm import MockLLMProvider
from atlas.memory.execution_memory import ExecutionMemory
from atlas.utils.logger import logger


class AtlasKernel:
    """
    Núcleo principal de Atlas AI Platform.

    Coordina los componentes centrales del sistema:
    registro, eventos, agentes, proveedores LLM y memoria.
    """

    def __init__(
        self,
        configuration: Optional[AtlasSettings] = None,
    ) -> None:
        self.settings = configuration or settings

        self.registry = ComponentRegistry()
        self.event_bus = EventBus()
        self.llm_manager = LLMManager(self.event_bus)
        self.agent_manager = AgentManager(self.event_bus)

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
                "Atlas Kernel ya se encuentra iniciado."
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
        self._register_default_llm_providers()
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
        Registra los componentes internos del Kernel.
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
            "llm_manager",
            self.llm_manager,
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

    def _register_default_llm_providers(self) -> None:
        """
        Registra los proveedores LLM iniciales.
        """
        self.llm_manager.register(
            MockLLMProvider(),
            make_default=True,
        )

        logger.info(
            "Proveedores LLM registrados: %s",
            self.llm_manager.count(),
        )

    def _register_default_agents(self) -> None:
        """
        Registra los agentes iniciales.
        """
        self.agent_manager.register(
            GeneralAgent(self.llm_manager)
        )

        logger.info(
            "Agentes registrados: %s",
            self.agent_manager.count(),
        )

    def execute(
        self,
        task: str,
        agent_name: str = "general-agent",
    ) -> Dict[str, object]:
        """
        Ejecuta una tarea utilizando un agente
        y guarda automáticamente el resultado.
        """
        if not self.started:
            raise RuntimeError(
                "Atlas Kernel debe estar iniciado."
            )

        result = self.agent_manager.execute(
            agent_name=agent_name,
            task=task,
        )

        memory_record = self.execution_memory.save(
            task=task,
            result=result,
            metadata={
                "agent": agent_name,
                "provider": result.get("provider"),
                "model": result.get("model"),
            },
        )

        self.event_bus.publish(
            "memory.execution.saved",
            memory_record,
        )

        return result

    def stop(self) -> None:
        """
        Detiene Atlas AI Platform.
        """
        if not self.started:
            logger.warning(
                "Atlas Kernel no está iniciado."
            )
            return

        self.event_bus.publish(
            "kernel.stopping",
            {
                "application": self.settings.app_name,
                "version": self.settings.version,
            },
        )

        logger.info(
            "Deteniendo Atlas AI Platform..."
        )

        self.started = False

        logger.info(
            "Atlas Kernel detenido correctamente."
        )

    def status(self) -> Dict[str, object]:
        """
        Devuelve el estado actual del Kernel.
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
            "stored_executions": self.execution_memory.count(),
            "event_types": self.event_bus.count_events(),
            "event_listeners": self.event_bus.count_listeners(),
        }