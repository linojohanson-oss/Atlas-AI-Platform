"""
Atlas AI Platform - Kernel

Núcleo principal de la plataforma Atlas AI.

El Kernel coordina:

- Configuración.
- Registro de componentes.
- Event Bus.
- Proveedores LLM.
- Herramientas.
- Capacidades.
- Agentes.
- Organización empresarial.
- Departamentos.
- Executive Agent.
- Workflows.
- Memoria de ejecuciones.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from atlas.agents import (
    EngineeringAgent,
    GeneralAgent,
    PlannerAgent,
    ResearchAgent,
    SecurityAgent,
)
from atlas.config.settings import (
    AtlasSettings,
    settings,
)
from atlas.enterprise.department_runtime import (
    DepartmentRuntime,
)
from atlas.enterprise.executive_agent import (
    ExecutiveAgent,
)
from atlas.kernel.agent_manager import AgentManager
from atlas.kernel.capability_manager import (
    CapabilityManager,
)
from atlas.kernel.event_bus import EventBus
from atlas.kernel.llm_manager import LLMManager
from atlas.kernel.organization_manager import (
    OrganizationManager,
)
from atlas.kernel.registry import ComponentRegistry
from atlas.kernel.tool_manager import ToolManager
from atlas.llm import MockLLMProvider
from atlas.memory.execution_memory import (
    ExecutionMemory,
)
from atlas.tools import (
    CalculatorTool,
    ExcelTool,
    FileInfoTool,
)
from atlas.utils.logger import logger
from atlas.workflows import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowRegistry,
    WorkflowStep,
)


class AtlasKernel:
    """
    Núcleo principal de Atlas AI Platform.

    AtlasKernel inicializa y coordina todos los componentes
    centrales de la plataforma.
    """

    def __init__(
        self,
        configuration: Optional[
            AtlasSettings
        ] = None,
    ) -> None:
        self.settings = configuration or settings

        # ========================================================
        # Infraestructura central
        # ========================================================

        self.registry = ComponentRegistry()
        self.event_bus = EventBus()

        # ========================================================
        # Managers
        # ========================================================

        self.capability_manager = (
            CapabilityManager(
                self.event_bus
            )
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

        # ========================================================
        # Enterprise Layer
        # ========================================================

        self.organization_manager = (
            OrganizationManager()
        )

        self.department_runtime = (
            DepartmentRuntime(
                organization_manager=(
                    self.organization_manager
                ),
                agent_manager=(
                    self.agent_manager
                ),
                event_bus=self.event_bus,
            )
        )

        self.executive_agent = ExecutiveAgent(
            department_runtime=(
                self.department_runtime
            ),
        )

        # ========================================================
        # Workflow Layer
        # ========================================================

        self.workflow_registry = (
            WorkflowRegistry()
        )

        self.workflow_engine = WorkflowEngine(
            department_runtime=(
                self.department_runtime
            ),
            workflow_registry=(
                self.workflow_registry
            ),
        )

        # ========================================================
        # Memory Layer
        # ========================================================

        self.execution_memory = (
            ExecutionMemory(
                self.settings.memory_dir
            )
        )

        # ========================================================
        # Estado del Kernel
        # ========================================================

        self.started = False

        self.started_at: Optional[
            datetime
        ] = None

        self.stopped_at: Optional[
            datetime
        ] = None

    # ============================================================
    # Ciclo de vida
    # ============================================================

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

        try:
            self._register_core_components()
            self._register_default_llm()
            self._register_default_tools()
            self._register_default_capabilities()
            self._register_default_agents()

            self._initialize_organization()
            self._register_default_workflows()
            self._initialize_workflow_engine()

            self.started = True
            self.started_at = datetime.now()
            self.stopped_at = None

            self.event_bus.publish(
                "kernel.started",
                {
                    "application": (
                        self.settings.app_name
                    ),
                    "version": (
                        self.settings.version
                    ),
                    "started_at": (
                        self.started_at
                        .isoformat()
                    ),
                },
            )

            logger.info(
                "Atlas Kernel iniciado "
                "correctamente. Versión %s",
                self.settings.version,
            )

        except Exception as error:
            logger.exception(
                "No fue posible iniciar "
                "Atlas Kernel: %s",
                error,
            )

            self._stop_started_components()
            raise

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
                "application": (
                    self.settings.app_name
                ),
                "version": (
                    self.settings.version
                ),
                "stopped_at": (
                    stopped_at.isoformat()
                ),
            },
        )

        logger.info(
            "Deteniendo Atlas AI Platform..."
        )

        # El WorkflowEngine debe detenerse antes
        # que DepartmentRuntime.
        self.workflow_engine.stop()

        logger.info(
            "Workflow Engine detenido: %s",
            self.workflow_engine.status.value,
        )

        self.executive_agent.stop()

        logger.info(
            "Executive Agent detenido: %s",
            self.executive_agent.status.value,
        )

        self.department_runtime.stop()

        logger.info(
            "Department Runtime detenido: %s",
            self.department_runtime.status.value,
        )

        self.started = False
        self.stopped_at = stopped_at

        self.event_bus.publish(
            "kernel.stopped",
            {
                "application": (
                    self.settings.app_name
                ),
                "version": (
                    self.settings.version
                ),
                "stopped_at": (
                    stopped_at.isoformat()
                ),
            },
        )

        logger.info(
            "Atlas Kernel detenido correctamente."
        )

    def _stop_started_components(
        self,
    ) -> None:
        """
        Detiene componentes parcialmente iniciados.

        Se utiliza cuando ocurre un error durante start().
        """

        try:
            if self.workflow_engine.is_ready:
                self.workflow_engine.stop()
        except Exception:
            logger.exception(
                "Error deteniendo WorkflowEngine."
            )

        try:
            if self.executive_agent.is_ready:
                self.executive_agent.stop()
        except Exception:
            logger.exception(
                "Error deteniendo ExecutiveAgent."
            )

        try:
            if self.department_runtime.is_ready:
                self.department_runtime.stop()
        except Exception:
            logger.exception(
                "Error deteniendo DepartmentRuntime."
            )

        self.started = False

    # ============================================================
    # Registro de componentes
    # ============================================================

    def _register_core_components(
        self,
    ) -> None:
        """
        Registra los componentes centrales.
        """

        components = {
            "configuration": self.settings,
            "component_registry": (
                self.registry
            ),
            "event_bus": self.event_bus,
            "capability_manager": (
                self.capability_manager
            ),
            "llm_manager": (
                self.llm_manager
            ),
            "tool_manager": (
                self.tool_manager
            ),
            "agent_manager": (
                self.agent_manager
            ),
            "organization_manager": (
                self.organization_manager
            ),
            "department_runtime": (
                self.department_runtime
            ),
            "executive_agent": (
                self.executive_agent
            ),
            "workflow_registry": (
                self.workflow_registry
            ),
            "workflow_engine": (
                self.workflow_engine
            ),
            "execution_memory": (
                self.execution_memory
            ),
        }

        for name, component in components.items():
            self.registry.register(
                name,
                component,
            )

        logger.info(
            "Componentes centrales registrados: %s",
            self.registry.count(),
        )

    def _register_default_llm(
        self,
    ) -> None:
        """
        Registra el proveedor LLM predeterminado.
        """

        self.llm_manager.register(
            MockLLMProvider(),
            make_default=True,
        )

        logger.info(
            "Proveedores LLM registrados: %s",
            self.llm_manager.count(),
        )

    def _register_default_tools(
        self,
    ) -> None:
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

    def _register_default_capabilities(
        self,
    ) -> None:
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

    def _register_default_agents(
        self,
    ) -> None:
        """
        Registra los agentes base de Atlas.
        """

        self.agent_manager.register(
            PlannerAgent(
                llm_manager=self.llm_manager,
                tool_manager=self.tool_manager,
                capability_manager=(
                    self.capability_manager
                ),
            )
        )

        self.agent_manager.register(
            GeneralAgent(
                self.llm_manager
            )
        )

        self.agent_manager.register(
            EngineeringAgent(
                self.llm_manager
            )
        )

        self.agent_manager.register(
            ResearchAgent(
                self.llm_manager
            )
        )

        self.agent_manager.register(
            SecurityAgent(
                self.llm_manager
            )
        )

        logger.info(
            "Agentes registrados: %s",
            self.agent_manager.count(),
        )

    # ============================================================
    # Enterprise Layer
    # ============================================================

    def _initialize_organization(
        self,
    ) -> None:
        """
        Inicializa la organización empresarial.
        """

        self.organization_manager.initialize()
        self.department_runtime.start()
        self.executive_agent.start()

        organization_summary = (
            self.organization_manager.summary()
        )

        department_count = (
            organization_summary
            .get("organization", {})
            .get("departments", {})
            .get("total_departments", 0)
        )

        logger.info(
            "Organización inicializada: "
            "%s departamentos",
            department_count,
        )

        logger.info(
            "Department Runtime iniciado: %s",
            self.department_runtime.status.value,
        )

        logger.info(
            "Executive Agent iniciado: %s",
            self.executive_agent.status.value,
        )

    # ============================================================
    # Workflow Layer
    # ============================================================

    def _register_default_workflows(
        self,
    ) -> None:
        """
        Registra los workflows base de Atlas AI.
        """

        enterprise_workflow = (
            WorkflowDefinition(
                workflow_id=(
                    "enterprise-ai-solution"
                ),
                name=(
                    "Enterprise AI Solution"
                ),
                description=(
                    "Analiza, investiga, diseña, "
                    "implementa conceptualmente y "
                    "revisa una solución empresarial "
                    "de inteligencia artificial."
                ),
                tags=[
                    "enterprise",
                    "artificial-intelligence",
                    "architecture",
                    "security",
                ],
                steps=[
                    WorkflowStep(
                        step_id="planning",
                        name="Strategic Planning",
                        department_id="planning",
                    ),
                    WorkflowStep(
                        step_id="research",
                        name="Research",
                        department_id="research",
                        depends_on=[
                            "planning",
                        ],
                    ),
                    WorkflowStep(
                        step_id="engineering",
                        name="Solution Engineering",
                        department_id=(
                            "engineering"
                        ),
                        depends_on=[
                            "planning",
                            "research",
                        ],
                    ),
                    WorkflowStep(
                        step_id="security-review",
                        name="Security Review",
                        department_id="security",
                        depends_on=[
                            "engineering",
                        ],
                    ),
                    WorkflowStep(
                        step_id="final-review",
                        name="Final Review",
                        department_id="operations",
                        depends_on=[
                            "engineering",
                            "security-review",
                        ],
                    ),
                ],
            )
        )

        security_api_workflow = (
            WorkflowDefinition(
                workflow_id=(
                    "security-api-review"
                ),
                name="Security API Review",
                description=(
                    "Analiza la seguridad de una API, "
                    "propone correcciones técnicas y "
                    "consolida una revisión final."
                ),
                tags=[
                    "security",
                    "api",
                    "engineering",
                ],
                steps=[
                    WorkflowStep(
                        step_id=(
                            "security-analysis"
                        ),
                        name=(
                            "Security Analysis"
                        ),
                        department_id="security",
                    ),
                    WorkflowStep(
                        step_id=(
                            "engineering-fix"
                        ),
                        name=(
                            "Engineering Fix"
                        ),
                        department_id=(
                            "engineering"
                        ),
                        depends_on=[
                            "security-analysis",
                        ],
                    ),
                    WorkflowStep(
                        step_id="final-review",
                        name="Final Review",
                        department_id="operations",
                        depends_on=[
                            "security-analysis",
                            "engineering-fix",
                        ],
                    ),
                ],
            )
        )

        self.workflow_registry.register_many(
            [
                enterprise_workflow,
                security_api_workflow,
            ]
        )

        logger.info(
            "Workflows registrados: %s",
            self.workflow_registry.count,
        )

    def _initialize_workflow_engine(
        self,
    ) -> None:
        """
        Inicia el motor de workflows.
        """

        self.workflow_engine.start()

        logger.info(
            "Workflow Engine iniciado: %s",
            self.workflow_engine.status.value,
        )

    # ============================================================
    # Ejecución de agentes
    # ============================================================

    def execute(
        self,
        task: str,
        agent_name: str = "planner-agent",
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea directamente mediante un agente.
        """

        self._ensure_started()

        normalized_task = str(
            task
        ).strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        result = self.agent_manager.execute(
            agent_name=agent_name,
            task=normalized_task,
        )

        self._save_execution(
            task=normalized_task,
            result=result,
            metadata={
                "execution_type": "agent",
                "agent": agent_name,
                "intent": result.get(
                    "intent"
                ),
                "selected_tool": result.get(
                    "selected_tool"
                ),
                "provider": result.get(
                    "provider"
                ),
                "model": result.get(
                    "model"
                ),
            },
            event_type=(
                "memory.execution.saved"
            ),
        )

        return result

    # ============================================================
    # Ejecución ejecutiva
    # ============================================================

    def execute_executive(
        self,
        task: str,
        department_id: Optional[
            str
        ] = None,
        required_capabilities: Optional[
            List[str]
        ] = None,
        required_tools: Optional[
            List[str]
        ] = None,
        required_permissions: Optional[
            List[str]
        ] = None,
        preferred_agent_ids: Optional[
            List[str]
        ] = None,
        excluded_agent_ids: Optional[
            List[str]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una solicitud mediante ExecutiveAgent.
        """

        self._ensure_started()

        normalized_task = str(
            task
        ).strip()

        if not normalized_task:
            raise ValueError(
                "La tarea ejecutiva "
                "no puede estar vacía."
            )

        result = self.executive_agent.execute(
            request=normalized_task,
            department_id=department_id,
            required_capabilities=(
                required_capabilities
            ),
            required_tools=required_tools,
            required_permissions=(
                required_permissions
            ),
            preferred_agent_ids=(
                preferred_agent_ids
            ),
            excluded_agent_ids=(
                excluded_agent_ids
            ),
            metadata=metadata,
        )

        decision = result.get(
            "decision",
            {},
        )

        self._save_execution(
            task=normalized_task,
            result=result,
            metadata={
                "execution_type": "executive",
                "department_id": (
                    decision.get(
                        "department_id"
                    )
                ),
                "confidence": (
                    decision.get(
                        "confidence"
                    )
                ),
                "matched_keywords": (
                    decision.get(
                        "matched_keywords",
                        [],
                    )
                ),
            },
            event_type=(
                "memory.executive_execution.saved"
            ),
        )

        return result

    # ============================================================
    # Ejecución departamental
    # ============================================================

    def execute_department(
        self,
        department_id: str,
        task: str,
        required_capabilities: Optional[
            List[str]
        ] = None,
        required_tools: Optional[
            List[str]
        ] = None,
        required_permissions: Optional[
            List[str]
        ] = None,
        preferred_agent_ids: Optional[
            List[str]
        ] = None,
        excluded_agent_ids: Optional[
            List[str]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea mediante un departamento.
        """

        self._ensure_started()

        normalized_department_id = str(
            department_id
        ).strip()

        normalized_task = str(
            task
        ).strip()

        if not normalized_department_id:
            raise ValueError(
                "department_id no puede estar vacío."
            )

        if not normalized_task:
            raise ValueError(
                "La tarea departamental "
                "no puede estar vacía."
            )

        result = self.department_runtime.execute(
            department_id=(
                normalized_department_id
            ),
            task=normalized_task,
            required_capabilities=(
                required_capabilities
            ),
            required_tools=required_tools,
            required_permissions=(
                required_permissions
            ),
            preferred_agent_ids=(
                preferred_agent_ids
            ),
            excluded_agent_ids=(
                excluded_agent_ids
            ),
            metadata=metadata,
        )

        selected_agent_id = (
            result
            .get("selected_agent", {})
            .get("agent", {})
            .get("agent_id")
        )

        self._save_execution(
            task=normalized_task,
            result=result,
            metadata={
                "execution_type": "department",
                "department_id": (
                    normalized_department_id
                ),
                "task_id": result.get(
                    "task_id"
                ),
                "status": result.get(
                    "status"
                ),
                "selected_agent": (
                    selected_agent_id
                ),
            },
            event_type=(
                "memory.execution.saved"
            ),
        )

        return result

    # ============================================================
    # Ejecución de workflows
    # ============================================================

    def execute_workflow(
        self,
        workflow_id: str,
        request: str,
        variables: Optional[
            Dict[str, Any]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow registrado.

        Ejemplo:

        kernel.execute_workflow(
            workflow_id="security-api-review",
            request="Revisar la seguridad de la API.",
        )
        """

        self._ensure_started()

        normalized_workflow_id = str(
            workflow_id
        ).strip()

        normalized_request = str(
            request
        ).strip()

        if not normalized_workflow_id:
            raise ValueError(
                "workflow_id no puede estar vacío."
            )

        if not normalized_request:
            raise ValueError(
                "La solicitud del workflow "
                "no puede estar vacía."
            )

        workflow_result = (
            self.workflow_engine.execute(
                workflow_id=(
                    normalized_workflow_id
                ),
                request=normalized_request,
                variables=variables,
                metadata=metadata,
            )
        )

        result_data = (
            workflow_result.to_dict()
        )

        self._save_execution(
            task=normalized_request,
            result=result_data,
            metadata={
                "execution_type": "workflow",
                "workflow_id": (
                    normalized_workflow_id
                ),
                "execution_id": (
                    workflow_result.execution_id
                ),
                "status": (
                    workflow_result.status.value
                ),
                "completed_steps": (
                    workflow_result
                    .completed_count
                ),
                "failed_steps": (
                    workflow_result
                    .failed_count
                ),
                "skipped_steps": (
                    workflow_result
                    .skipped_count
                ),
                "blocked_steps": (
                    workflow_result
                    .blocked_count
                ),
            },
            event_type=(
                "memory.workflow_execution.saved"
            ),
        )

        return result_data

    # ============================================================
    # Herramientas y capacidades
    # ============================================================

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta una herramienta registrada.
        """

        self._ensure_started()

        normalized_tool_name = str(
            tool_name
        ).strip().lower()

        if not normalized_tool_name:
            raise ValueError(
                "El nombre de la herramienta "
                "no puede estar vacío."
            )

        result = self.tool_manager.execute(
            tool_name=normalized_tool_name,
            **kwargs,
        )

        self._save_execution(
            task=(
                f"Ejecutar herramienta "
                f"'{normalized_tool_name}' "
                f"con argumentos {kwargs}"
            ),
            result=result,
            metadata={
                "execution_type": "tool",
                "tool": normalized_tool_name,
            },
            event_type=(
                "memory.execution.saved"
            ),
        )

        return result

    def execute_capability(
        self,
        capability_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta una capacidad mediante su herramienta.
        """

        self._ensure_started()

        normalized_capability = str(
            capability_name
        ).strip().lower()

        if not normalized_capability:
            raise ValueError(
                "El nombre de la capacidad "
                "no puede estar vacío."
            )

        tool_name = (
            self.capability_manager.resolve(
                normalized_capability
            )
        )

        result = self.tool_manager.execute(
            tool_name=tool_name,
            **kwargs,
        )

        self._save_execution(
            task=(
                f"Ejecutar capacidad "
                f"'{normalized_capability}' "
                f"mediante '{tool_name}' "
                f"con argumentos {kwargs}"
            ),
            result=result,
            metadata={
                "execution_type": "capability",
                "capability": (
                    normalized_capability
                ),
                "tool": tool_name,
            },
            event_type=(
                "memory.execution.saved"
            ),
        )

        return result

    # ============================================================
    # Memoria
    # ============================================================

    def _save_execution(
        self,
        task: str,
        result: Dict[str, Any],
        metadata: Dict[str, Any],
        event_type: str,
    ) -> Dict[str, Any]:
        """
        Guarda una ejecución y publica el evento.
        """

        memory_record = (
            self.execution_memory.save(
                task=task,
                result=result,
                metadata=metadata,
            )
        )

        self.event_bus.publish(
            event_type,
            memory_record,
        )

        return memory_record

    def get_execution_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial general.
        """

        return (
            self.execution_memory.get_history(
                limit=limit
            )
        )

    def get_last_execution(
        self,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene la última ejecución.
        """

        return self.execution_memory.get_last()

    def get_workflow_execution(
        self,
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Obtiene una ejecución del WorkflowEngine.
        """

        self._ensure_started()

        return (
            self.workflow_engine
            .get_execution_data(
                execution_id
            )
        )

    def get_workflow_executions(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lista ejecuciones mantenidas por WorkflowEngine.
        """

        self._ensure_started()

        return (
            self.workflow_engine
            .list_executions(
                limit=limit
            )
        )

    # ============================================================
    # Estado
    # ============================================================

    def status(self) -> Dict[str, Any]:
        """
        Devuelve el estado general de Atlas AI.
        """

        organization_status: Dict[
            str,
            Any,
        ]

        if self.organization_manager.is_ready:
            organization_status = (
                self.organization_manager.summary()
            )
        else:
            organization_status = {
                "status": (
                    self.organization_manager
                    .status.value
                ),
                "is_ready": False,
            }

        return {
            "application": (
                self.settings.app_name
            ),
            "version": (
                self.settings.version
            ),
            "environment": (
                self.settings.environment
            ),
            "started": self.started,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "stopped_at": (
                self.stopped_at.isoformat()
                if self.stopped_at
                else None
            ),
            "registered_components": (
                self.registry.count()
            ),
            "component_names": (
                self.registry.list_names()
            ),
            "registered_agents": (
                self.agent_manager.count()
            ),
            "agent_names": (
                self.agent_manager.list_names()
            ),
            "registered_llm_providers": (
                self.llm_manager.count()
            ),
            "llm_provider_names": (
                self.llm_manager.list_names()
            ),
            "default_llm_provider": (
                self.llm_manager
                .default_provider
            ),
            "registered_tools": (
                self.tool_manager.count()
            ),
            "tool_names": (
                self.tool_manager.list_names()
            ),
            "registered_capabilities": (
                self.capability_manager.count()
            ),
            "capability_names": (
                self.capability_manager
                .list_names()
            ),
            "capabilities": (
                self.capability_manager
                .list_capabilities()
            ),
            "organization": (
                organization_status
            ),
            "department_runtime": (
                self.department_runtime.summary()
            ),
            "executive_agent": (
                self.executive_agent.summary()
            ),
            "workflow_registry": (
                self.workflow_registry.stats()
            ),
            "registered_workflows": (
                self.workflow_registry.count
            ),
            "workflow_ids": (
                self.workflow_registry
                .workflow_ids
            ),
            "workflow_engine": (
                self.workflow_engine.summary()
            ),
            "stored_executions": (
                self.execution_memory.count()
            ),
            "event_types": (
                self.event_bus.count_events()
            ),
            "event_listeners": (
                self.event_bus.count_listeners()
            ),
        }

    # ============================================================
    # Validaciones
    # ============================================================

    def _ensure_started(self) -> None:
        """
        Verifica que Atlas Kernel esté iniciado.
        """

        if not self.started:
            raise RuntimeError(
                "Atlas Kernel debe estar iniciado "
                "antes de ejecutar tareas."
            )

    def __repr__(self) -> str:
        return (
            "AtlasKernel("
            f"started={self.started}, "
            f"agents={self.agent_manager.count()}, "
            f"workflows={self.workflow_registry.count}"
            ")"
        )