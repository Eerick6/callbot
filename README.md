# Taxiblau - Bot de Atención Telefónica con IA

Bot de atención al cliente para Taxiblau que utiliza inteligencia artificial para responder llamadas telefónicas en tiempo real.

## Caracteristicas

- Atencion telefonica automatica 24/7
- Respuestas en español con voz natural
- Transcripcion en tiempo real
- Integracion con Twilio Media Streams
- Grabacion dual de llamadas (opcional)
- Baja latencia en respuestas

## Tecnologias

- Pipecat - Framework de orquestacion de voz/IA
- Twilio - Telefonia y Media Streams
- Deepgram - Speech-to-Text
- OpenAI (GPT-4) - Procesamiento de lenguaje natural
- Cartesia - Text-to-Speech
- FastAPI - Servidor web
- Docker - Contenerizacion
- Render - Hosting y despliegue

## Requisitos Previos

- Docker y Docker Compose
- Cuenta en Twilio con numero telefonico
- API Key de Deepgram
- API Key de OpenAI
- API Key de Cartesia
- Cuenta en Render

## Estructura del Proyecto

server.py              # Servidor FastAPI y endpoints
bot.py                 # Logica principal del bot
requirements.txt       # Dependencias del proyecto
Dockerfile             # Configuracion Docker
.env                   # Variables de entorno (local)
.dockerignore          # Archivos ignorados por Docker
README.md              # Documentacion

## Variables de Entorno

Crear archivo `.env` con las siguientes variables:

OPENAI_API_KEY=tu_api_key_de_openai
DEEPGRAM_API_KEY=tu_api_key_de_deepgram
CARTESIA_API_KEY=tu_api_key_de_cartesia
TWILIO_ACCOUNT_SID=tu_sid_de_twilio
TWILIO_AUTH_TOKEN=tu_token_de_twilio

## Instalacion y Ejecucion Local con Docker

git clone https://github.com/tu-usuario/taxiblau-bot.git
cd taxiblau-bot
docker build -t taxiblau-bot .
docker run -p 7860:7860 --env-file .env taxiblau-bot

## Dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["python", "server.py"]

## .dockerignore

__pycache__
*.pyc
.env
.git
README.md

## Despliegue en Render

1. Crear nuevo Web Service en Render
2. Conectar repositorio de GitHub
3. Seleccionar "Docker" como entorno
4. Configurar variables de entorno
5. Desplegar

## Configuracion en Twilio

1. En consola de Twilio, ir a Phone Numbers
2. Seleccionar numero a configurar
3. En "A call comes in", seleccionar Webhook
4. URL: https://tu-dominio-en-render.com/
5. Metodo: HTTP POST
6. Guardar cambios

## Comportamiento del Bot

El bot esta configurado como operadora de Taxiblau:
- Responde amable y profesionalmente en español
- Utiliza voz femenina friendly
- Velocidad de habla: 1.2x
- Procesa interrupciones naturalmente
- Espera a que el usuario termine de hablar antes de responder

## Monitoreo

Los logs estan habilitados en nivel DEBUG para seguimiento de:
- Conexiones de clientes
- Transcripciones de Deepgram
- Tokens utilizados en OpenAI
- Generacion de audio en Cartesia
- Desconexiones

## Notas Importantes

- El bot funciona con una llamada a la vez con la configuracion actual
- Para multiples llamadas concurrentes se requiere ajustar la arquitectura
- Los costos de API se calculan por minuto de uso
- Las grabaciones de llamadas son opcionales via API de Twilio

## Licencia

Copyright (c) 2025 - Taxiblau - Todos los derechos reservados