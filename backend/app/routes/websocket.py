import json
import logging
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from app.services.auth_service import verify_token
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["WebSocket Streaming"])
logger = logging.getLogger("websocket_route")


@router.websocket("/ws/retrain")
async def websocket_retrain_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Token JWT Bearer opcional (preferir autenticación en banda)"),
):
    """Canal WebSocket bidireccional para monitoreo en vivo del ciclo de reentrenamiento con límite de concurrencia y soporte de autenticación en banda."""
    if token:
        try:
            verify_token(token)
        except Exception:
            logger.warning("Rechazando conexión WebSocket: token de autenticación inválido o expirado.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación inválido.")
            return

    connected = await ws_manager.connect(websocket)
    if not connected:
        return

    try:
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "stage": "connected",
            "progress": 0,
            "message": "Conectado al canal de eventos de reentrenamiento en tiempo real.",
        })
        while True:
            # Mantener conexión abierta, responder a pings y procesar autenticación en banda
            raw_data = await websocket.receive_text()
            if raw_data == "ping":
                await websocket.send_text("pong")
                continue

            try:
                msg = json.loads(raw_data)
                if isinstance(msg, dict) and msg.get("type") == "auth":
                    auth_token = msg.get("token")
                    if auth_token:
                        try:
                            verify_token(auth_token)
                            await websocket.send_json({"stage": "auth", "status": "authenticated"})
                        except Exception:
                            logger.warning("Rechazando WebSocket: token en banda inválido.")
                            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación en banda inválido.")
                            ws_manager.disconnect(websocket)
                            return
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Excepción en websocket: {e}")
        ws_manager.disconnect(websocket)
