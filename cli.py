from atlas import AtlasKernel


def print_header() -> None:
    print()
    print("=" * 76)
    print("ATLAS AI PLATFORM")
    print("Enterprise Multi-Agent Artificial Intelligence Framework")
    print("=" * 76)


def on_llm_completed(payload) -> None:
    print()
    print("RESPUESTA LLM GENERADA")
    print("-" * 76)
    print(f"Proveedor               : {payload['provider']}")
    print(f"Modelo                  : {payload['model']}")


def on_agent_completed(payload) -> None:
    print()
    print("TAREA COMPLETADA POR AGENTE")
    print("-" * 76)
    print(f"Agente                  : {payload.get('agent')}")
    print(f"Estado                  : {payload.get('status')}")
    print(f"Proveedor               : {payload.get('provider')}")
    print(f"Modelo                  : {payload.get('model')}")

    output = (
        payload.get("output")
        or payload.get("result")
        or payload.get("response")
        or payload
    )

    print(f"Resultado               : {output}")


def on_tool_completed(payload) -> None:
    print()
    print("HERRAMIENTA EJECUTADA")
    print("-" * 76)
    print(f"Herramienta             : {payload['tool']}")
    print(f"Estado                  : {payload['status']}")
    print(f"Entrada                 : {payload['input']}")
    print(f"Resultado               : {payload['result']}")


def on_memory_saved(payload) -> None:
    print()
    print("EJECUCIÓN GUARDADA EN MEMORIA")
    print("-" * 76)
    print(f"ID                      : {payload['execution_id']}")
    print(f"Fecha                   : {payload['created_at']}")
    print(f"Tarea                   : {payload['task']}")


def print_status(kernel: AtlasKernel) -> None:
    status = kernel.status()

    print()
    print("ESTADO DEL SISTEMA")
    print("-" * 76)
    print(f"Aplicación              : {status['application']}")
    print(f"Versión                 : {status['version']}")
    print(f"Entorno                 : {status['environment']}")
    print(f"Kernel iniciado         : {status['started']}")
    print(f"Componentes registrados : {status['registered_components']}")
    print(f"Agentes registrados     : {status['registered_agents']}")
    print(f"Proveedores LLM         : {status['registered_llm_providers']}")
    print(f"Proveedor predeterminado: {status['default_llm_provider']}")
    print(f"Herramientas registradas: {status['registered_tools']}")
    print(f"Ejecuciones almacenadas : {status['stored_executions']}")

    print()
    print("COMPONENTES CENTRALES")
    print("-" * 76)

    for component_name in status["component_names"]:
        print(f"[OK] {component_name}")

    print()
    print("AGENTES DISPONIBLES")
    print("-" * 76)

    for agent_name in status["agent_names"]:
        print(f"[OK] {agent_name}")

    print()
    print("PROVEEDORES LLM")
    print("-" * 76)

    for provider_name in status["llm_provider_names"]:
        print(f"[OK] {provider_name}")

    print()
    print("HERRAMIENTAS DISPONIBLES")
    print("-" * 76)

    for tool_name in status["tool_names"]:
        print(f"[OK] {tool_name}")


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
        "tool.execution.completed",
        on_tool_completed,
    )

    kernel.event_bus.subscribe(
        "memory.execution.saved",
        on_memory_saved,
    )

    try:
        kernel.start()

        print_status(kernel)

        print()
        print("DEMOSTRACIÓN 1 — AGENTE GENERAL")
        print("-" * 76)

        kernel.execute(
            "Explicar qué es Atlas AI Platform."
        )

        print()
        print("DEMOSTRACIÓN 2 — CALCULATOR TOOL")
        print("-" * 76)

        expression = "(1250 * 18) / 100 + 45"

        print(f"Expresión solicitada    : {expression}")

        result = kernel.execute_tool(
            "calculator",
            expression=expression,
        )

        print()
        print("RESULTADO FINAL")
        print("-" * 76)
        print(f"Herramienta seleccionada: {result['tool']}")
        print(f"Resultado calculado     : {result['result']}")

        print()
        print("=" * 76)
        print("ATLAS AI v0.6.0 ESTÁ LISTO")
        print("=" * 76)

    except Exception as exc:
        print()
        print("=" * 76)
        print("ERROR AL INICIAR ATLAS")
        print("=" * 76)
        print(exc)
        raise


if __name__ == "__main__":
    main()
