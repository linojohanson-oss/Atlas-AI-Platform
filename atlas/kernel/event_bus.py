from collections import defaultdict
from typing import Any, Callable, Dict, List


EventCallback = Callable[[Any], None]


class EventBus:
    """
    Sistema central de eventos de Atlas AI Platform.

    Permite que los componentes publiquen y reciban eventos
    sin depender directamente unos de otros.
    """

    def __init__(self) -> None:
        self._listeners: Dict[str, List[EventCallback]] = defaultdict(list)

    def subscribe(
        self,
        event_name: str,
        callback: EventCallback,
    ) -> None:
        """Registra una función para escuchar un evento."""
        normalized_name = self._normalize_event_name(event_name)

        if callback not in self._listeners[normalized_name]:
            self._listeners[normalized_name].append(callback)

    def unsubscribe(
        self,
        event_name: str,
        callback: EventCallback,
    ) -> None:
        """Elimina una función suscripta a un evento."""
        normalized_name = self._normalize_event_name(event_name)

        callbacks = self._listeners.get(normalized_name)

        if not callbacks:
            return

        if callback in callbacks:
            callbacks.remove(callback)

        if not callbacks:
            del self._listeners[normalized_name]

    def publish(
        self,
        event_name: str,
        payload: Any = None,
    ) -> int:
        """
        Publica un evento.

        Devuelve la cantidad de listeners ejecutados.
        """
        normalized_name = self._normalize_event_name(event_name)

        callbacks = list(
            self._listeners.get(normalized_name, [])
        )

        for callback in callbacks:
            callback(payload)

        return len(callbacks)

    def clear(self) -> None:
        """Elimina todos los eventos registrados."""
        self._listeners.clear()

    def listeners(self) -> Dict[str, int]:
        """Devuelve la cantidad de listeners por evento."""
        return {
            event_name: len(callbacks)
            for event_name, callbacks in sorted(
                self._listeners.items()
            )
        }

    def count_events(self) -> int:
        """Devuelve la cantidad de eventos con listeners."""
        return len(self._listeners)

    def count_listeners(self) -> int:
        """Devuelve la cantidad total de listeners."""
        return sum(
            len(callbacks)
            for callbacks in self._listeners.values()
        )

    @staticmethod
    def _normalize_event_name(event_name: str) -> str:
        normalized_name = event_name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre del evento no puede estar vacío."
            )

        return normalized_name
