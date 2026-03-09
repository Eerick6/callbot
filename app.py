import os
import traceback

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response
from loguru import logger

from bot import bot
from pipecat.runner.types import WebSocketRunnerArguments

app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/")
async def twiml(request: Request):
    host = (os.getenv("PROXY_HOST") or "").strip()
    if not host:
        host = request.headers.get("host", "").strip()

    logger.info(f"PROXY_HOST={os.getenv('PROXY_HOST')!r}")
    logger.info(f"request host={request.headers.get('host')!r}")
    logger.info(f"final host={host!r}")

    if not host:
        return Response(
            content="""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>Server configuration error</Say></Response>""",
            media_type="application/xml",
            status_code=500,
        )

    ws_url = f"wss://{host}/ws"
    logger.info(f"Twilio stream url = {ws_url}")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}"></Stream>
    </Connect>
    <Pause length="40"/>
</Response>"""
    return Response(content=xml, media_type="application/xml")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("WS endpoint hit")
    await websocket.accept()
    logger.info("WS accepted")

    try:
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        await bot(runner_args)
    except Exception as e:
        logger.error(f"WS bot error: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        try:
            await websocket.close()
        except Exception:
            pass