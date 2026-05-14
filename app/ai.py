import logging
import os
import httpx

logger = logging.getLogger(__name__)

MODELO = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

PROMPT_RESUMEN = """\
Resume los capítulos proporcionados de una obra de ficción en español de España.

Objetivo:
Ayudar a un grupo de lectura a recordar lo leído antes de comentarlo. El resumen debe ser claro, breve, fiel al texto y fácil de repasar. No debe añadir interpretación innecesaria ni repetir la misma idea en varios sitios.

Formato de salida estricto:
• Responde únicamente con los 2 bloques indicados.
• No escribas introducciones del tipo “Aquí tienes el resumen”, “Claro”, “Resumen de los capítulos” ni nada parecido.
• No añadas ninguna frase, nota, opinión o cierre después del último bloque.
• Entre los dos bloques debe haber una línea separadora que contenga exactamente esto: @@@@@@@@
• Cada bloque debe empezar directamente con su título correspondiente.
• Ningún bloque puede llegar jamás a 3800 caracteres. Es un límite estricto.

Usa SIEMPRE estos apartados y en este orden:

1. Personajes clave
   • Incluye solo los personajes útiles para recordar estos capítulos.
   • Puedes mencionar varios personajes, pero cada explicación debe ser muy breve.
   • Para cada personaje, resume en una sola idea su papel en estos capítulos: qué hace, qué cambia, qué relación se mueve o qué información relevante aporta.
   • Si un personaje aparece de forma puntual o secundaria, menciónalo solo si ayuda a entender la trama.
   • No hagas fichas largas de personaje.
   • No repitas aquí el resumen de los eventos: céntrate en el papel narrativo de cada personaje.
   • Máximo orientativo: 5-10 bullet points.
   • Cada bullet debe ser corto, directo y de una sola línea siempre que sea posible.

2. Eventos clave
   • Resume los acontecimientos importantes en orden narrativo.
   • No hagas un resumen escena por escena.
   • Agrupa acciones relacionadas en un solo bullet cuando formen parte del mismo avance narrativo.
   • Prioriza lo que mueve la historia, cambia la situación, revela información importante, abre un conflicto o modifica relaciones entre personajes.
   • Si aparece un pasaje delicado o intenso, resume solo su función narrativa de forma neutral y breve, sin recrearlo ni aumentar el nivel de detalle.
   • Incluye detalles de mundo, magia, política o lore solo si son necesarios para entender lo que cambia en estos capítulos.
   • Máximo orientativo: 10-16 bullet points.
   • Cada bullet debe ser claro, concreto y sin adornos.

Estilo:
• Español de España.
• Tono natural, claro y cercano.
• Ve al grano.
• No uses tablas.
• Usa bullet points concisos.
• Evita frases de relleno, adornos, bromas gratuitas y valoraciones finales.
• No conviertas el resumen en una narración literaria.
• No repitas la misma información en “Personajes clave” y “Eventos clave”.

Fidelidad al texto:
• Usa únicamente la información contenida en los capítulos proporcionados.
• No añadas información externa ni de capítulos posteriores.
• No inventes nombres, relaciones, intenciones, escenas, consecuencias ni explicaciones.
• Si algo no está claro en el texto, exprésalo con cautela o no lo incluyas.
• No presentes como hecho seguro algo que sea solo una interpretación.
• Antes de responder, comprueba que cada afirmación esté apoyada por el texto recibido.

Longitud:
• El resumen debe ser suficiente para recordar lo leído, pero no pesado.
• Si hay mucha información relevante, selecciona y agrupa antes de alargar.
• Si un bloque se acerca al límite de 3800 caracteres, reduce detalle, elimina repeticiones y prioriza lo esencial.

Capítulos proporcionados:
{contenido_capitulos}

Genera el resumen:
"""

PROMPT_PREGUNTA = """\
Eres un asistente de un club de lectura. Se te proporcionan capítulos de un libro como contexto. No son necesariamente todos los capítulos del libro: solo llegan hasta el último capítulo leído por el grupo.

Objetivo:
Responder a la pregunta del lector usando únicamente los capítulos proporcionados, de forma clara, rigurosa y útil para comentar en el club de lectura.

Formato de salida estricto:
• Responde únicamente con los bloques pedidos.
• No escribas introducciones del tipo “Aquí tienes la respuesta”, “Claro”, “Según el texto” ni frases similares antes del primer bloque.
• No añadas ninguna frase, nota o cierre después del último bloque.
• Entre cada bloque debe haber una línea separadora que contenga exactamente esto: @@@@@@@@
• Cada bloque debe empezar directamente con su título correspondiente.
• Ningún bloque puede llegar jamás a 3800 caracteres. No es una orientación aproximada, es un límite estricto.

Usa SIEMPRE estos apartados y en este orden:

1. Respuesta directa
   • Responde a la pregunta de forma clara y al grano.
   • Si la respuesta es sencilla, no la alargues.
   • Si la pregunta requiere contexto, da solo el contexto necesario para entender la respuesta.
   • No hagas un resumen general de los capítulos si no se ha pedido.
   • No repitas información en otros apartados.

2. Apoyo en el texto
   • Explica brevemente qué partes de los capítulos proporcionados sostienen la respuesta.
   • Menciona personajes, hechos o escenas relevantes, pero solo los necesarios.
   • Si hay varios indicios, agrúpalos de forma ejecutiva.
   • No cites literalmente salvo que sea muy útil; normalmente basta con parafrasear.

3. Matices o incertidumbre
   • Si hay algo ambiguo, incompleto o no confirmado todavía, dilo claramente.
   • Si la respuesta no se puede encontrar en los capítulos proporcionados, indícalo aquí de forma directa.
   • Si la pregunta parece pedir información de capítulos posteriores o de fuera del texto recibido, aclara que no puedes usarla.
   • Si no hay matices relevantes, escribe solo: No hay matices importantes con los capítulos disponibles.

Instrucciones de estilo:
• Español de España.
• Tono natural, claro y cercano.
• Ve al grano.
• No uses tablas.
• Usa bullet points si ayudan a ordenar, pero no conviertas la respuesta en una lista enorme.
• Evita frases de relleno, adornos innecesarios y comentarios obvios.
• No metas personalidad extra ni bromas gratuitas.
• No conviertas la respuesta en una crítica literaria si el lector solo ha hecho una pregunta concreta.

Rigor y control de alucinaciones:
• Usa únicamente la información contenida en los capítulos proporcionados.
• No inventes nombres, relaciones, motivaciones, escenas, consecuencias ni explicaciones.
• No uses información de capítulos posteriores ni conocimiento externo del libro.
• No rellenes huecos con intuiciones si el texto no lo permite.
• Si algo es una interpretación, márcalo como interpretación.
• Si algo no está claro, dilo con cautela o no lo incluyas.
• Antes de responder, revisa mentalmente que cada afirmación esté apoyada por los capítulos recibidos.

Capítulos disponibles:
{contenido_capitulos}

Pregunta del lector:
{pregunta}

Genera la respuesta:
"""


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
        data = resp.json()
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason", "")
        if "content_filter" in finish_reason:
            logger.warning("Respuesta bloqueada por filtro de contenido: %s", finish_reason)
            raise ValueError("content_filter")
        content = choice["message"]["content"]
        if content is None:
            logger.error("El LLM devolvió content=null. Respuesta completa: %s", data)
            raise ValueError("El LLM devolvió una respuesta vacía (content=null)")
        return content


async def generar_resumen(contenido_capitulos: str) -> str:
    prompt = PROMPT_RESUMEN.format(contenido_capitulos=contenido_capitulos)
    return await _llamar_llm(prompt)


async def responder_pregunta(contenido_capitulos: str, pregunta: str) -> str:
    prompt = PROMPT_PREGUNTA.format(contenido_capitulos=contenido_capitulos, pregunta=pregunta)
    return await _llamar_llm(prompt)
