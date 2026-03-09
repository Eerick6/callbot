"""Function calling tools for Taxiblau voice bot.

Tools for taxi service:
  1. check_user_status — checks if caller already exists
  2. register_user — registers a new caller with provided name
"""

import os
import aiohttp
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams


def register_tools(
    llm,
    caller_number: str,
    backend_url: str = None,
):
    """Register taxi service tools on the LLM.

    Args:
        llm: LLM service instance
        caller_number: Customer's phone number from call info
        backend_url: URL of your NestJS backend
    """

    if not backend_url:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:3000")

    async def check_user_status(params: FunctionCallParams):
        """Check if user exists using caller phone number only."""
        logger.info(f"📞 Tool called: check_user_status(phone={caller_number!r})")

        if not caller_number:
            logger.warning("No caller number available")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": "No phone number available",
            })
            return

        try:
            url = f"{backend_url}/bot-clients/check"
            payload = {"phone": caller_number}

            logger.debug(f"Calling backend: {url}")
            logger.debug(f"Payload: {payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✅ Backend response: {data}")

                        client = data.get("client")

                        await params.result_callback({
                            "success": data.get("success", True),
                            "user_exists": data.get("user_exists", False),
                            "client_id": client.get("id") if client else None,
                            "client_name": client.get("name") if client else None,
                            "client_email": (
                                client.get("user", {}).get("email")
                                if client and isinstance(client.get("user"), dict)
                                else client.get("email") if client else None
                            ),
                            "client": client,
                            "source": "check",
                        })
                        return

                    error_text = await resp.text()
                    logger.error(f"❌ Backend error ({resp.status}): {error_text}")

                    await params.result_callback({
                        "success": False,
                        "user_exists": False,
                        "client": None,
                        "error": f"HTTP {resp.status}",
                    })

        except aiohttp.ClientError as e:
            logger.error(f"❌ Connection error calling backend: {e}")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": f"Connection error: {str(e)}",
            })
        except Exception as e:
            logger.error(f"❌ Unexpected error in check_user_status: {e}")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": str(e),
            })

    async def register_user(params: FunctionCallParams, name: str):
        """Register a new user with caller phone number and provided name."""
        logger.info(f"📞 Tool called: register_user(phone={caller_number!r}, name={name!r})")

        if not caller_number:
            logger.warning("No caller number available")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": "No phone number available",
            })
            return

        trimmed_name = (name or "").strip()
        if not trimmed_name:
            logger.warning("No valid name provided for registration")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": "Name is required",
            })
            return

        try:
            url = f"{backend_url}/bot-clients/register"
            payload = {
                "phone": caller_number,
                "name": trimmed_name,
            }

            logger.debug(f"Calling backend: {url}")
            logger.debug(f"Payload: {payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✅ Backend response: {data}")

                        client = data.get("client")

                        await params.result_callback({
                            "success": data.get("success", True),
                            "user_exists": data.get("user_exists", True),
                            "client_id": client.get("id") if client else None,
                            "client_name": client.get("name") if client else trimmed_name,
                            "client_email": (
                                client.get("user", {}).get("email")
                                if client and isinstance(client.get("user"), dict)
                                else client.get("email") if client else None
                            ),
                            "client": client,
                            "source": "register",
                        })
                        return

                    error_text = await resp.text()
                    logger.error(f"❌ Backend error ({resp.status}): {error_text}")

                    await params.result_callback({
                        "success": False,
                        "user_exists": False,
                        "client": None,
                        "error": f"HTTP {resp.status}",
                    })

        except aiohttp.ClientError as e:
            logger.error(f"❌ Connection error calling backend: {e}")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": f"Connection error: {str(e)}",
            })
        except Exception as e:
            logger.error(f"❌ Unexpected error in register_user: {e}")
            await params.result_callback({
                "success": False,
                "user_exists": False,
                "client": None,
                "error": str(e),
            })

    llm.register_function("check_user_status", check_user_status)
    llm.register_function("register_user", register_user)

    logger.info(f"✅ Registered tools for caller: {caller_number or 'unknown'}")

    check_user_schema = FunctionSchema(
        name="check_user_status",
        description=(
            "Verifica si el cliente que llama ya existe usando su número de teléfono. "
            "Debes llamarla al inicio de la llamada para saber si el cliente ya existe o es nuevo."
        ),
        properties={},
        required=[],
    )

    register_user_schema = FunctionSchema(
        name="register_user",
        description=(
            "Registra un cliente nuevo usando el número de teléfono de la llamada y su nombre completo. "
            "Solo debes llamarla después de que el cliente haya dicho su nombre."
        ),
        properties={
            "name": {
                "type": "string",
                "description": "Nombre completo del cliente para registrarlo.",
            }
        },
        required=["name"],
    )

    return ToolsSchema(standard_tools=[check_user_schema, register_user_schema])