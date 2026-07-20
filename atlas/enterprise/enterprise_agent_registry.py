from typing import Any, Dict, List, Optional

from atlas.enterprise.agent_profile import (
    AgentProfile,
    AgentStatus,
)


class EnterpriseAgentRegistry:
    """
    Registro empresarial de agentes de Atlas AI OS.

    Mantiene la información organizacional y operativa
    de todos los agentes disponibles en la plataforma.

    Este registro administra perfiles, no ejecuta agentes.
    La ejecución continúa siendo responsabilidad de
    AgentManager.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, AgentProfile] = {}

    def register(
        self,
        profile: AgentProfile,
        replace: bool = False,
    ) -> None:
        """
        Registra un perfil de agente.

        Args:
            profile:
                Perfil empresarial del agente.

            replace:
                Permite reemplazar un perfil existente.
        """
        if not isinstance(profile, AgentProfile):
            raise TypeError(
                "El perfil debe ser una instancia de AgentProfile."
            )

        agent_id = self._normalize_identifier(
            profile.agent_id
        )

        if agent_id in self._profiles and not replace:
            raise ValueError(
                f"El agente '{agent_id}' ya está registrado "
                "en EnterpriseAgentRegistry."
            )

        self._profiles[agent_id] = profile

    def register_many(
        self,
        profiles: List[AgentProfile],
        replace: bool = False,
    ) -> None:
        """
        Registra varios perfiles.
        """
        for profile in profiles:
            self.register(
                profile=profile,
                replace=replace,
            )

    def get(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Obtiene un perfil por identificador.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        if normalized_id not in self._profiles:
            raise KeyError(
                f"El agente '{normalized_id}' no está registrado "
                "en EnterpriseAgentRegistry."
            )

        return self._profiles[normalized_id]

    def find(
        self,
        agent_id: str,
    ) -> Optional[AgentProfile]:
        """
        Busca un perfil sin producir una excepción.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        return self._profiles.get(
            normalized_id
        )

    def remove(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Elimina y devuelve un perfil.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        if normalized_id not in self._profiles:
            raise KeyError(
                f"El agente '{normalized_id}' no está registrado."
            )

        return self._profiles.pop(
            normalized_id
        )

    def contains(
        self,
        agent_id: str,
    ) -> bool:
        """
        Indica si un agente está registrado.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        return normalized_id in self._profiles

    def list_profiles(self) -> List[AgentProfile]:
        """
        Devuelve todos los perfiles registrados.
        """
        return sorted(
            self._profiles.values(),
            key=lambda profile: (
                profile.priority,
                profile.agent_id,
            ),
        )

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Devuelve todos los perfiles serializados.
        """
        return [
            profile.to_dict()
            for profile in self.list_profiles()
        ]

    def list_ids(self) -> List[str]:
        """
        Devuelve los identificadores registrados.
        """
        return sorted(
            self._profiles.keys()
        )

    def count(self) -> int:
        """
        Devuelve la cantidad total de perfiles.
        """
        return len(self._profiles)

    def find_by_capability(
        self,
        capability: str,
        available_only: bool = False,
    ) -> List[AgentProfile]:
        """
        Busca agentes que posean una capacidad.
        """
        normalized_capability = (
            self._normalize_identifier(
                capability
            )
        )

        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.has_capability(
                normalized_capability
            )
        ]

        if available_only:
            profiles = [
                profile
                for profile in profiles
                if profile.is_available
            ]

        return self._sort_profiles(
            profiles
        )

    def find_by_department(
        self,
        department: str,
        available_only: bool = False,
    ) -> List[AgentProfile]:
        """
        Busca agentes de un departamento.
        """
        normalized_department = (
            self._normalize_text(
                department
            ).lower()
        )

        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.department.lower()
            == normalized_department
        ]

        if available_only:
            profiles = [
                profile
                for profile in profiles
                if profile.is_available
            ]

        return self._sort_profiles(
            profiles
        )

    def find_by_role(
        self,
        role: str,
        available_only: bool = False,
    ) -> List[AgentProfile]:
        """
        Busca agentes por rol organizacional.
        """
        normalized_role = (
            self._normalize_text(
                role
            ).lower()
        )

        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.role.lower()
            == normalized_role
        ]

        if available_only:
            profiles = [
                profile
                for profile in profiles
                if profile.is_available
            ]

        return self._sort_profiles(
            profiles
        )

    def find_by_tool(
        self,
        tool_name: str,
        available_only: bool = False,
    ) -> List[AgentProfile]:
        """
        Busca agentes con acceso a una herramienta.
        """
        normalized_tool = self._normalize_identifier(
            tool_name
        )

        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.has_tool(
                normalized_tool
            )
        ]

        if available_only:
            profiles = [
                profile
                for profile in profiles
                if profile.is_available
            ]

        return self._sort_profiles(
            profiles
        )

    def available_agents(self) -> List[AgentProfile]:
        """
        Devuelve agentes disponibles.
        """
        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.is_available
        ]

        return self._sort_profiles(
            profiles
        )

    def busy_agents(self) -> List[AgentProfile]:
        """
        Devuelve agentes ocupados.
        """
        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.status == AgentStatus.BUSY
        ]

        return self._sort_profiles(
            profiles
        )

    def enabled_agents(self) -> List[AgentProfile]:
        """
        Devuelve agentes habilitados.
        """
        profiles = [
            profile
            for profile in self._profiles.values()
            if profile.enabled
        ]

        return self._sort_profiles(
            profiles
        )

    def update_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> AgentProfile:
        """
        Actualiza el estado de un agente.
        """
        profile = self.get(
            agent_id
        )

        profile.set_status(
            status
        )

        return profile

    def enable(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Habilita un agente.
        """
        profile = self.get(
            agent_id
        )

        profile.enable()

        return profile

    def disable(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Deshabilita un agente.
        """
        profile = self.get(
            agent_id
        )

        profile.disable()

        return profile

    def start_task(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Marca el inicio de una tarea.
        """
        profile = self.get(
            agent_id
        )

        profile.start_task()

        return profile

    def finish_task(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Marca la finalización de una tarea.
        """
        profile = self.get(
            agent_id
        )

        profile.finish_task()

        return profile

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen operativo del registro.
        """
        profiles = list(
            self._profiles.values()
        )

        total = len(profiles)

        enabled = sum(
            1
            for profile in profiles
            if profile.enabled
        )

        available = sum(
            1
            for profile in profiles
            if profile.is_available
        )

        busy = sum(
            1
            for profile in profiles
            if profile.status == AgentStatus.BUSY
        )

        offline = sum(
            1
            for profile in profiles
            if profile.status == AgentStatus.OFFLINE
        )

        error = sum(
            1
            for profile in profiles
            if profile.status == AgentStatus.ERROR
        )

        departments = sorted(
            {
                profile.department
                for profile in profiles
            }
        )

        capabilities = sorted(
            {
                capability
                for profile in profiles
                for capability in profile.capabilities
            }
        )

        return {
            "total_agents": total,
            "enabled_agents": enabled,
            "available_agents": available,
            "busy_agents": busy,
            "offline_agents": offline,
            "error_agents": error,
            "departments": departments,
            "department_count": len(departments),
            "capabilities": capabilities,
            "capability_count": len(capabilities),
        }

    def clear(self) -> None:
        """
        Elimina todos los perfiles registrados.
        """
        self._profiles.clear()

    @staticmethod
    def _sort_profiles(
        profiles: List[AgentProfile],
    ) -> List[AgentProfile]:
        """
        Ordena agentes por prioridad, carga y nombre.
        """
        return sorted(
            profiles,
            key=lambda profile: (
                profile.priority,
                profile.load_percentage,
                -profile.metrics.success_rate,
                profile.agent_id,
            ),
        )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace(
            " ",
            "-",
        )
        normalized = normalized.replace(
            "_",
            "-",
        )

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError(
                "El texto no puede estar vacío."
            )

        return normalized