import asyncio
import json
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket, status

logger = logging.getLogger("websocket_manager")


class WebSocketManager:
    """Gestiona conexiones activas WebSocket para retransmisión en tiempo real con límites de concurrencia."""

    MAX_CONNECTIONS: int = 20  # Límite global para prevenir agotamiento de sockets (Finding 1)

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> bool:
        """Acepta la conexión si no se supera el límite global."""
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            logger.warning(f"Límite de conexiones WebSocket alcanzado ({self.MAX_CONNECTIONS}). Rechazando conexión.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Límite máximo de conexiones simultáneas alcanzado.")
            return False

        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente WebSocket conectado. Conexiones activas: {len(self.active_connections)}")
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"Cliente WebSocket desconectado. Conexiones activas: {len(self.active_connections)}")

    async def broadcast(self, data: Dict[str, Any]) -> None:
        """
        Emite un mensaje concurrentemente a una instantánea (snapshot) de clientes conectados
        con timeout por socket para evitar bloqueos por clientes lentos (Findings 8 y 12).
        """
        connections_snapshot: List[WebSocket] = list(self.active_connections)
        if not connections_snapshot:
            return

        message_str = json.dumps(data)
        dead_connections: List[WebSocket] = []

        async def _safe_send(ws: WebSocket):
            try:
                # Timeout de 2 segundos por socket para no demorar al resto (Finding 12)
                await asyncio.wait_for(ws.send_text(message_str), timeout=2.0)
            except Exception as e:
                logger.warning(f"Fallo o timeout al enviar mensaje por WebSocket: {e}")
                dead_connections.append(ws)

        await asyncio.gather(*[_safe_send(ws) for ws in connections_snapshot], return_exceptions=True)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = WebSocketManager()
