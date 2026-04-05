import os
import httpx

MODELO = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

PROMPT_RESUMEN = """\
Quiero que me resumas unos capítulos de un libro en español de España, con un formato estructurado y muy útil para recordar lo leído y comentarlo en mi grupo de lectura.

Hazlo SIEMPRE con estos apartados y en este orden:

1. Personajes
   • Resume solo los personajes relevantes en estos capítulos.
   • Para cada personaje, explica qué hace, qué cambia, qué descubre o qué papel juega.
   • Prioriza evolución, relaciones, conflictos, motivaciones y revelaciones importantes.
   • Escríbelo en bullet points.

2. Eventos clave
   • Resume los acontecimientos importantes de forma clara y ordenada.
   • No quiero un resumen escena por escena sin filtro, sino los eventos que de verdad mueven la historia, revelan algo importante o cambian la situación.
   • Escríbelo también en bullet points.

3. Lo más importante que deja esta parte
   • Haz una sección breve en bullet points con las ideas más importantes que dejan estos capítulos.
   • Por ejemplo: cambios en el tablero, revelaciones, nuevas dinámicas, conflictos que se abren, misterios que se aclaran o se complican.

4. Mi conclusióncita
   • Termina con una pequeña conclusión/opinión final en tono natural, cercana y algo desenfadada.
   • Quiero que parezca una valoración útil para comentar con otra gente, no una crítica académica.
   • Puede incluir impresiones del tipo: “aquí el libro pega un salto”, “este personaje queda retratado del todo”, “aquí cambia de nivel”, etc.
   • Que tenga personalidad, pero sin pasarse de chiste, puede ser malhablado.

Instrucciones de estilo:
• Escribe en español de España.
• Tono claro, natural y cercano.
• Nada de tono robótico ni excesivamente formal.
• No uses tablas.
• Mejor bullet points que párrafos larguísimos, salvo en la conclusión final.
• No inventes nada ni metas información de capítulos posteriores.
• Si un personaje parece importante pero en estos capítulos aún no se revela del todo, dilo claramente sin forzarlo.
• Si hay un giro importante, destácalo bien.
• Si hay relaciones entre personajes que cambian, subráyalo.
• Si hay detalles de mundo, magia, política o lore que aquí pasan a ser importantes, inclúyelos.

Importante:
No me hagas un resumen genérico. Quiero uno con buena lectura narrativa, centrado en:
• personajes,
• eventos que importan de verdad,
• qué cambia en la historia,
• y una conclusión final con criterio.

Ahora te paso los capítulos:
{contenido_capitulos}

Genera el resumen:"""

PROMPT_PREGUNTA = """\
Eres un asistente de un club de lectura. A continuación se te proporcionan los textos de varios capítulos de un libro como contexto.

IMPORTANTE: Responde SOLO con información que aparezca en los capítulos proporcionados. No inventes ni añadas nada que no esté en el texto. Si la respuesta no se puede encontrar en los capítulos, dilo claramente.

Capítulos disponibles:
{contenido_capitulos}

Pregunta del lector:
{pregunta}

Responde en español de España, con tono cercano y claro:"""


async def _llamar_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODELO,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def generar_resumen(contenido_capitulos: str) -> str:
    prompt = PROMPT_RESUMEN.format(contenido_capitulos=contenido_capitulos)
    return await _llamar_llm(prompt)


async def responder_pregunta(contenido_capitulos: str, pregunta: str) -> str:
    prompt = PROMPT_PREGUNTA.format(contenido_capitulos=contenido_capitulos, pregunta=pregunta)
    return await _llamar_llm(prompt)
