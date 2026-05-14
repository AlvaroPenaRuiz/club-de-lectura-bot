import os
import httpx

MODELO = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

PROMPT_RESUMEN = """\
Resume los capítulos proporcionados de un libro en español de España.

Objetivo del resumen:
Ayudar a un grupo de lectura a recordar lo leído antes de comentarlo. Debe ser claro, riguroso y fácil de repasar. No debe ser largo por lucirse ni repetir la misma información en varios apartados.

Formato de salida estricto:
• Responde únicamente con los 4 bloques pedidos.
• No escribas introducciones del tipo “Aquí tienes el resumen”, “Claro”, “Resumen de los capítulos” ni frases similares.
• No añadas ninguna frase, nota o cierre después del último bloque.
• Entre cada bloque debe haber una línea separadora que contenga exactamente esto: @@@@@@@@
• Cada bloque debe empezar directamente con su título correspondiente.

Usa SIEMPRE estos apartados y en este orden:

1. Personajes clave
   • Incluye solo los personajes realmente relevantes en estos capítulos.
   • No hagas una ficha de todos los personajes que aparecen.
   • Añade información sobre un personaje solo si en estos capítulos hace algo importante, cambia, revela algo, toma una decisión, entra en conflicto, modifica una relación o queda mejor definido.
   • Si un personaje simplemente está presente pero no evoluciona ni aporta algo nuevo, omítelo.
   • Máximo orientativo: 3-8 bullets.
   • Cada bullet debe ser directo, sin repetir eventos que ya vayan a aparecer en “Eventos clave”, salvo que sea necesario para explicar una evolución del personaje.

2. Eventos clave
   • Resume los acontecimientos importantes en orden narrativo.
   • No hagas un resumen escena por escena.
   • Agrupa acciones relacionadas en un solo bullet cuando formen parte del mismo avance narrativo.
   • Prioriza lo que mueve la historia, cambia la situación, revela información importante, abre un conflicto o modifica la relación entre personajes.
   • Máximo orientativo: 6-12 bullets.
   • Cada bullet debe ser claro y concreto.

3. Lo más importante que deja esta parte
   • Sección breve con las consecuencias, revelaciones o ideas que conviene tener frescas para comentar.
   • Incluye cambios de tablero, misterios, conflictos abiertos, dinámicas nuevas, detalles de mundo/magia/política/lore relevantes o información que recontextualiza lo leído.
   • Máximo orientativo: 3-6 bullets.
   • Evita repetir literalmente lo ya dicho en “Eventos clave”: aquí importa el significado o la consecuencia, no volver a contar la escena.

4. Mi conclusióncita
   • Termina con una valoración breve, natural y cercana.
   • Debe sonar como alguien del grupo comentando qué deja esta parte, no como una crítica académica.
   • Puede tener algo de personalidad y un punto desenfadado, incluso ligeramente malhablado si encaja, pero sin alargar ni meter chistes gratuitos.
   • Máximo: 1 párrafo corto de 3-5 líneas.

Instrucciones de estilo:
• Español de España.
• Tono natural, claro y cercano.
• Resumen ejecutivo: ve al grano.
• No uses tablas.
• Usa bullets concisos.
• Evita frases de relleno, adornos innecesarios y comentarios obvios.
• No repitas la misma idea en varios apartados.
• No sobreexpliques relaciones o motivaciones si ya quedan claras.
• No metas personalidad extra en mitad del resumen: guárdala para la conclusión final.
• No conviertas el resumen en una narración literaria; debe ser una herramienta de repaso.

Rigor y control de alucinaciones:
• Usa únicamente la información contenida en los capítulos proporcionados.
• No inventes nombres, relaciones, motivaciones, escenas, consecuencias ni explicaciones.
• No uses información de capítulos posteriores ni conocimiento externo del libro.
• Si algo no está claro en el texto, dilo con cautela o no lo incluyas.
• No presentes como seguro algo que solo sea una interpretación.
• Si un detalle parece importante pero todavía no se explica, indícalo como misterio o punto pendiente.
• Antes de responder, revisa mentalmente que cada afirmación esté apoyada por el texto.

Longitud:
• El resumen debe ser suficientemente completo para recordar lo leído, pero no pesado.
• Para un bloque normal de capítulos, intenta mantenerlo compacto.
• Ningún bloque puede llegar jamás a 3800 caracteres. No es una orientación aproximada, es un límite estricto.
• Si un bloque se acerca demasiado a ese límite, reduce detalle, agrupa ideas y elimina redundancias antes de responder.
• Si hay muchos eventos relevantes, prioriza claridad y selección antes que exhaustividad.

Ahora te paso los capítulos:
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
• Usa bullets si ayudan a ordenar, pero no conviertas la respuesta en una lista enorme.
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
        return resp.json()["choices"][0]["message"]["content"]


async def generar_resumen(contenido_capitulos: str) -> str:
    prompt = PROMPT_RESUMEN.format(contenido_capitulos=contenido_capitulos)
    return await _llamar_llm(prompt)


async def responder_pregunta(contenido_capitulos: str, pregunta: str) -> str:
    prompt = PROMPT_PREGUNTA.format(contenido_capitulos=contenido_capitulos, pregunta=pregunta)
    return await _llamar_llm(prompt)
