import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")


class WebSocketManager:
    """Gestiona conexiones activas WebSocket para retransmisión en tiempo real."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente WebSocket conectado. Conexiones activas: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"Cliente WebSocket desconectado. Conexiones activas: {len(self.active_connections)}")

    async def broadcast(self, data: Dict[str, Any]) -> None:
        """Emite un mensaje a todos los clientes conectados de manera segura."""
        if not self.active_connections:
            return

        dead_connections = set()
        message_str = json.dumps(data)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Error al enviar por WebSocket a cliente: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)


ws_manager = WebSocketManager()
