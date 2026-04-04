import os
import httpx

MODELO = "gemma3:4b"
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")

PROMPT_RESUMEN = """\
Eres un asistente de un club de lectura. A continuación se te proporcionan los textos de varios capítulos de un libro.

Tu tarea es generar un resumen claro y conciso de lo que ocurre en estos capítulos. \
El resumen debe ayudar a los lectores a recordar los puntos clave sin revelar spoilers innecesarios de capítulos posteriores.

Capítulos:
{contenido_capitulos}

Genera el resumen:"""


async def generar_resumen(contenido_capitulos: str) -> str:
    prompt = PROMPT_RESUMEN.format(contenido_capitulos=contenido_capitulos)

    async with httpx.AsyncClient(timeout=900.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": MODELO,
                "prompt": prompt,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]
