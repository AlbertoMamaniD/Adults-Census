import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["WebSocket Streaming"])
logger = logging.getLogger("websocket_route")


@router.websocket("/ws/retrain")
async def websocket_retrain_endpoint(websocket: WebSocket):
    """Canal WebSocket bidireccional para monitoreo en vivo del ciclo de reentrenamiento."""
    await ws_manager.connect(websocket)
    try:
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "stage": "connected",
            "progress": 0,
            "message": "Conectado al canal de eventos de reentrenamiento en tiempo real.",
        })
        while True:
            # Mantener conexión abierta y responder a posibles pings del cliente
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Excepción en websocket: {e}")
        ws_manager.disconnect(websocket)
