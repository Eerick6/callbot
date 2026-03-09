#!/usr/bin/env python3
"""
Cliente de prueba para TaxiBlau - FLUJO COMPLETO
Simula una llamada real con el bot
"""

import asyncio
import aiohttp
import json
import sys
import random
from loguru import logger

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

class TaxiBlauTester:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.phone = f"+346{random.randint(10000000, 99999999)}"
        self.stream_sid = "test-stream-123"
        self.call_sid = "test-call-456"
        
    async def run(self):
        logger.info("=" * 60)
        logger.info("🚕 TEST CLIENT - FLUJO COMPLETO TAXIBLAU")
        logger.info(f"📞 Teléfono: {self.phone}")
        logger.info("=" * 60)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url) as ws:
                    logger.info("✅ Conectado al bot")
                    
                    # PASO 1: Handshake inicial
                    await self._send_handshake(ws)
                    
                    # PASO 2: Escuchar el saludo del bot
                    await self._listen_for_saludo(ws)
                    
                    # PASO 3: Bot debería llamar a tool sin nombre y preguntar nombre
                    await self._listen_for_pregunta_nombre(ws)
                    
                    # PASO 4: Responder con nombre (simulado como audio)
                    await self._respond_with_name(ws, "Juan Pérez")
                    
                    # PASO 5: Escuchar confirmación de registro
                    await self._listen_for_confirmacion(ws)
                    
                    # PASO 6: Escuchar resto de conversación
                    await self._listen_rest(ws)
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}")
    
    async def _send_handshake(self, ws):
        """Envía el handshake inicial"""
        logger.info("📤 Paso 1: Enviando handshake...")
        await ws.send_json({
            "event": "connected",
            "protocol": "Call",
            "version": "1.0.0"
        })
        await ws.send_json({
            "event": "start",
            "streamSid": self.stream_sid,
            "callSid": self.call_sid,
            "start": {"streamSid": self.stream_sid, "callSid": self.call_sid}
        })
        logger.info("✅ Handshake enviado")
    
    async def _listen_for_saludo(self, ws):
        """Espera el saludo inicial del bot"""
        logger.info("👂 Paso 2: Esperando saludo del bot...")
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                logger.info(f"📨 Bot dice: {data}")
                break  # Salimos después del primer mensaje
        logger.info("✅ Saludo recibido")
    
    async def _listen_for_pregunta_nombre(self, ws):
        """Espera que el bot pregunte el nombre"""
        logger.info("👂 Paso 3: Esperando que el bot pregunte el nombre...")
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                logger.info(f"📨 Bot dice: {data}")
                if "nombre" in data.get("text", "").lower() or "llamas" in data.get("text", "").lower():
                    logger.info("✅ Bot preguntó por el nombre")
                    break
        logger.info("✅ Pregunta de nombre recibida")
    
    async def _respond_with_name(self, ws, name: str):
        """Simula que el usuario dice su nombre (en un cliente real sería audio)"""
        logger.info(f"🗣️ Paso 4: Usuario dice: 'Me llamo {name}'")
        # NOTA: En un cliente real, aquí enviarías AUDIO con la frase
        # Por ahora solo simulamos con texto para ver el flujo
        await ws.send_str(f"Me llamo {name}")
        logger.info("✅ Nombre enviado")
    
    async def _listen_for_confirmacion(self, ws):
        """Espera confirmación de registro"""
        logger.info("👂 Paso 5: Esperando confirmación de registro...")
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                logger.info(f"📨 Bot dice: {data}")
                if "registrado" in data.get("text", "").lower() or "gracias" in data.get("text", "").lower():
                    logger.info("✅ Bot confirmó el registro")
                    break
        logger.info("✅ Confirmación recibida")
    
    async def _listen_rest(self, ws):
        """Escucha el resto de la conversación por 30 segundos"""
        logger.info("👂 Paso 6: Escuchando resto de conversación (30s)...")
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.info(f"📨 Bot dice: {data}")
        except asyncio.TimeoutError:
            pass

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", default="wss://marcie-expandable-jackeline.ngrok-free.dev/ws")
    args = parser.parse_args()
    
    tester = TaxiBlauTester(args.url)
    await tester.run()
    
    logger.info("=" * 60)
    logger.info("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(main())