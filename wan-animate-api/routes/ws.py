"""ComfyUI WebSocket proxy."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()


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

    try:
        import websockets

        async with websockets.connect(target) as comfy_ws:

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
                    pass

            async def comfy_to_client() -> None:
                async for message in comfy_ws:
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
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
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
