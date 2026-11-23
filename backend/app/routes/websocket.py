import asyncio
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
    """Canal WebSocket bidireccional para monitoreo en vivo del ciclo de reentrenamiento.
    Requiere autenticación válida antes de registrar el socket para recibir broadcasts (Qodo Finding 11).
    """
    # 1. Autenticación en query o en banda
    if token:
        try:
            verify_token(token)
        except Exception:
            logger.warning("Rechazando conexión WebSocket: token de autenticación inválido o expirado.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación inválido.")
            return
        await websocket.accept()
    else:
        await websocket.accept()
        # Pre-autenticación acotada: esperar hasta 5 segundos por el mensaje {type: 'auth', token: ...}
        try:
            raw_auth = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg = json.loads(raw_auth)
            if isinstance(msg, dict) and msg.get("type") == "auth":
                auth_token = msg.get("token")
                if not auth_token:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación ausente.")
                    return
                verify_token(auth_token)
                await websocket.send_json({"stage": "auth", "status": "authenticated"})
            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Mensaje de autenticación requerido.")
                return
        except Exception as e:
            logger.warning(f"Rechazando WebSocket por fallo o timeout de autenticación en banda: {e}")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Autenticación requerida no suministrada a tiempo.")
            except Exception:
                pass
            return

    # 2. Registrar conexión autenticada en el gestor de broadcasts
    registered = await ws_manager.register_authenticated(websocket)
    if not registered:
        return

    try:
        # Enviar mensaje de bienvenida únicamente a clientes autenticados
        await websocket.send_json({
            "stage": "connected",
            "progress": 0,
            "message": "Conectado al canal de eventos de reentrenamiento en tiempo real.",
        })
        while True:
            raw_data = await websocket.receive_text()
            if raw_data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Excepción en websocket autenticado: {e}")
    finally:
        ws_manager.disconnect(websocket)
