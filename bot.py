import os
import asyncio  # 👈 IMPORTANTE: AÑADE ESTO
from typing import Optional

import aiohttp
from deepgram import LiveOptions
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService, GenerationConfig
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Importar nuestras tools
from tools import register_tools

load_dotenv(override=True)

# 🔥 HABILITAR TODOS LOS LOGS PARA DEBUG 🔥
logger.remove(0)
logger.add(lambda msg: print(msg, flush=True), level="DEBUG")
logger.enable("pipecat.services.stt_service")
logger.enable("pipecat.services.deepgram")
logger.enable("pipecat.audio.vad")
logger.enable("pipecat.transports")
logger.enable("pipecat.processors")


async def get_call_info(call_sid: str) -> dict:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials, cannot fetch call info")
        return {}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"

    try:
        auth = aiohttp.BasicAuth(account_sid, auth_token)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Twilio API error ({response.status}): {error_text}")
                    return {}

                data = await response.json()
                return {
                    "from_number": data.get("from"),
                    "to_number": data.get("to"),
                }
    except Exception as e:
        logger.error(f"Error fetching call info from Twilio: {e}")
        return {}


async def start_twilio_recording(call_sid: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials, cannot start recording")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}/Recordings.json"

    try:
        auth = aiohttp.BasicAuth(account_sid, auth_token)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                auth=auth,
                data={"RecordingChannels": "dual"},
            ) as response:
                if response.status not in (200, 201):
                    error_text = await response.text()
                    logger.error(f"Twilio recording API error ({response.status}): {error_text}")
                    return

                data = await response.json()
                logger.info(f"Twilio recording started: SID={data.get('sid')}")
    except Exception as e:
        logger.error(f"Error starting Twilio recording: {e}")


async def run_bot(
    transport: BaseTransport,
    handle_sigint: bool,
    testing: bool,
    call_sid: str = "",
    caller_number: str = "",
):
    logger.info("🚀 Starting TaxiBlau bot")

    # 🔧 CONFIGURACIÓN DE SERVICIOS 🔧
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=LiveOptions(
            model="nova-2-general", 
            language="es",
            encoding="linear16",
            sample_rate=8000,
            channels=1,
            smart_format=True, 
            interim_results=False,  
        ),
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="d4db5fb9-f44b-4bd1-85fa-192e0f0d75f9",
        params=CartesiaTTSService.InputParams(
            language="es",
            generation_config=GenerationConfig(
                emotion="friendly",
                speed=1.1,
            ),
        ),
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # 📞 REGISTRAR TOOLS
    tools_schema = register_tools(
        llm,
        caller_number=caller_number,
        backend_url=os.getenv("BACKEND_URL", "http://localhost:3000"),
    )

    # 💬 PROMPT DEL SISTEMA
    messages = [
        {
            "role": "system",
            "content": (
                "Eres una operadora telefónica de TaxiBlau para gestionar servicios de taxi en España. "
                "Responde siempre en español, con frases cortas, naturales y profesionales. "
                "Tu único objetivo es ayudar con servicios de taxi y no debes desviarte del tema. "

                "El saludo inicial 'Bienvenido a TaxiBlau.' ya se reproduce automáticamente al conectar la llamada, "
                "así que no debes repetirlo salvo que sea necesario. "

                "La referencia de fecha y hora es siempre Madrid, España (zona horaria Europe/Madrid). "
                "Cuando el cliente diga 'ahora', 'hoy', 'esta tarde', 'mañana' o expresiones similares, "
                "interprétalas siempre según la hora local de Madrid. "
                "Si el cliente no indica fecha ni hora, asume que el servicio es para ahora. "

                "Flujo obligatorio: "
                "1) Al iniciar cada llamada, usa inmediatamente la herramienta 'check_user_status' para verificar si el cliente ya existe. "
                "2) Si el cliente existe, pregúntale de forma natural en qué puedes ayudarle hoy. "
                "3) Si el cliente no existe, pide su nombre completo para registrarlo. "
                "4) Cuando el cliente diga su nombre, usa inmediatamente la herramienta 'register_user' con ese nombre. "
                "5) Después de registrarlo, pregunta qué servicio necesita hoy. "

                "Si el cliente quiere reservar un taxi: "
                "1) Debes pedir siempre la dirección exacta de recogida. "
                "2) Debes pedir siempre la dirección exacta de destino. "
                "3) Ambas direcciones deben ser reales, válidas y estar en España. "
                "4) No aceptes direcciones ambiguas, ficticias, imposibles o fuera de España. "
                "5) No aceptes viajes entre países. "
                "6) Si una dirección no está clara o parece inválida, pide que la repitan o completen. "
                "7) No confirmes ninguna reserva hasta tener los datos necesarios. "

                "Nunca menciones herramientas, verificaciones internas, backend ni procesos del sistema. "
                "Haz una sola pregunta a la vez."
            ),
        },
    ]

    context = LLMContext(messages)

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("✅ Client connected")

        if call_sid:
            await start_twilio_recording(call_sid)

        # 🚀 SALUDO INMEDIATO - SIN ESPERAR AL LLM
        saludo_inicial = "Bienvenido a TaxiBlau."
        logger.info(f"📢 Reproduciendo saludo inmediato: '{saludo_inicial}'")

        # Enviar el saludo directamente al TTS (NO espera al LLM)
        await tts.say(saludo_inicial)

        # Disparar el primer paso obligatorio del flujo
        context.add_message(
            {
                "role": "system",
                "content": (
                    "Cliente conectado. Usa ahora mismo 'check_user_status'. "
                    "Si el cliente existe, pregúntale en qué puedes ayudar hoy. "
                    "Si no existe, pide su nombre completo para registrarlo. "
                    "Cuando te diga su nombre, usa 'register_user' y luego continúa con el flujo."
                ),
            }
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("❌ Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments, testing: Optional[bool] = False):
    logger.info("📞 Executing bot()")

    _, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"📋 call_data: {call_data}")

    call_info = await get_call_info(call_data["call_id"])
    caller_number = ""

    if call_info:
        caller_number = call_info.get("from_number", "")
        logger.info(f"📞 Call from: {caller_number}")

    serializer = TwilioFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_data["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    await run_bot(
        transport,
        runner_args.handle_sigint,
        testing,
        call_sid=call_data["call_id"],
        caller_number=caller_number,
    )