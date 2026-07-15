"""ComfyUI WebSocket proxy."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger("wan_animate.ws")

router = APIRouter()


async def _connect_comfy(target: str, retries: int = 2):
    import websockets

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await websockets.connect(target, open_timeout=10)
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < retries:
                await asyncio.sleep(0.5)
    raise last_exc  # type: ignore[misc]


@router.websocket("/api/comfy/proxy/ws")
async def comfy_ws_proxy(websocket: WebSocket, clientId: str = Query(...)) -> None:
    settings = websocket.app.state.settings
    comfy_url = settings["comfy_url"]
    parsed = urlparse(comfy_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    target = f"{scheme}://{host}:{port}/ws?clientId={clientId}"

    await websocket.accept()
    logger.info("ws proxy accepted clientId=%s target=%s", clientId, target)

    try:
        comfy_ws = await _connect_comfy(target)
    except Exception as exc:
        logger.error("ws proxy failed to connect ComfyUI clientId=%s: %s", clientId, exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        return

    try:
        async with comfy_ws:

            async def client_to_comfy() -> None:
                try:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            break
                        if "text" in message and message["text"] is not None:
                            await comfy_ws.send(message["text"])
                        elif "bytes" in message and message["bytes"] is not None:
                            await comfy_ws.send(message["bytes"])
                except WebSocketDisconnect:
                    logger.info("ws proxy client disconnected clientId=%s", clientId)

            async def comfy_to_client() -> None:
                diag = websocket.app.state.progress_diagnostic
                async for message in comfy_ws:
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
                        diag.log_backend_event(clientId, message)
                        await websocket.send_text(message)

            done, pending = await asyncio.wait(
                [asyncio.create_task(client_to_comfy()), asyncio.create_task(comfy_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                try:
                    task.result()
                except Exception as exc:
                    logger.warning("ws proxy task ended clientId=%s: %s", clientId, exc)
    except WebSocketDisconnect:
        logger.info("ws proxy disconnected during session clientId=%s", clientId)
    except Exception as exc:
        logger.exception("ws proxy error clientId=%s: %s", clientId, exc)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        logger.info("ws proxy closed clientId=%s", clientId)
