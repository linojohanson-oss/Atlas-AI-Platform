from atlas import AtlasKernel


def print_header() -> None:
    print()
    print("=" * 72)
    print("ATLAS AI PLATFORM")
    print("Enterprise Multi-Agent Artificial Intelligence Framework")
    print("=" * 72)


def on_llm_completed(payload) -> None:
    print()
    print("RESPUESTA LLM GENERADA")
    print("-" * 72)
    print(f"Proveedor               : {payload['provider']}")
    print(f"Modelo                  : {payload['model']}")


def on_agent_completed(payload) -> None:
    print()
    print("TAREA COMPLETADA")
    print("-" * 72)
    print(f"Agente                  : {payload['agent']}")
    print(f"Estado                  : {payload['status']}")
    print(f"Proveedor               : {payload['provider']}")
    print(f"Modelo                  : {payload['model']}")
    print(f"Resultado               : {payload['output']}")


def on_memory_saved(payload) -> None:
    print()
    print("EJECUCIÓN GUARDADA EN MEMORIA")
    print("-" * 72)
    print(f"ID de ejecución         : {payload['execution_id']}")
    print(f"Fecha                   : {payload['created_at']}")
    print(f"Tarea                   : {payload['task']}")


def print_status(kernel: AtlasKernel) -> None:
    status = kernel.status()

    print()
    print("ESTADO DEL SISTEMA")
    print("-" * 72)
    print(f"Aplicación              : {status['application']}")
    print(f"Versión                 : {status['version']}")
    print(f"Entorno                 : {status['environment']}")
    print(f"Kernel iniciado         : {status['started']}")
    print(
        f"Componentes registrados : "
        f"{status['registered_components']}"
    )
    print(
        f"Agentes registrados     : "
        f"{status['registered_agents']}"
    )
    print(
        f"Proveedores LLM         : "
        f"{status['registered_llm_providers']}"
    )
    print(
        f"Proveedor predeterminado: "
        f"{status['default_llm_provider']}"
    )
    print(
        f"Ejecuciones almacenadas : "
        f"{status['stored_executions']}"
    )

    print()
    print("COMPONENTES CENTRALES")
    print("-" * 72)

    for component_name in status["component_names"]:
        print(f"[OK] {component_name}")

    print()
    print("PROVEEDORES LLM")
    print("-" * 72)

    for provider_name in status["llm_provider_names"]:
        print(f"[OK] {provider_name}")

    print()
    print("AGENTES DISPONIBLES")
    print("-" * 72)

    for agent_name in status["agent_names"]:
        print(f"[OK] {agent_name}")


def print_last_execution(kernel: AtlasKernel) -> None:
    last_execution = kernel.execution_memory.get_last()

    print()
    print("ÚLTIMA EJECUCIÓN GUARDADA")
    print("-" * 72)

    if last_execution is None:
        print("No existen ejecuciones guardadas.")
        return

    print(f"ID                      : {last_execution['execution_id']}")
    print(f"Fecha                   : {last_execution['created_at']}")
    print(f"Tarea                   : {last_execution['task']}")
    print(
        f"Estado                  : "
        f"{last_execution['result'].get('status')}"
    )
    print(
        f"Agente                  : "
        f"{last_execution['result'].get('agent')}"
    )


def main() -> None:
    print_header()

    kernel = AtlasKernel()

    kernel.event_bus.subscribe(
        "llm.generation.completed",
        on_llm_completed,
    )

    kernel.event_bus.subscribe(
        "agent.completed",
        on_agent_completed,
    )

    kernel.event_bus.subscribe(
        "memory.execution.saved",
        on_memory_saved,
    )

    try:
        kernel.start()
        print_status(kernel)

        print()
        print("PRUEBA DE ATLAS AI")
        print("-" * 72)

        kernel.execute(
            "Explicar qué es Atlas AI Platform."
        )

        print_last_execution(kernel)

        print()
        print("=" * 72)
        print("ATLAS AI v0.5.0 ESTÁ LISTO")
        print("=" * 72)

    except Exception as exc:
        print()
        print("=" * 72)
        print("ERROR AL INICIAR ATLAS")
        print("=" * 72)
        print(exc)
        raise


if __name__ == "__main__":
    main()