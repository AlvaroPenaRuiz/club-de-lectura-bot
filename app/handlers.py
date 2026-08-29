import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import ChatMemberStatus

logger = logging.getLogger(__name__)


# La ficha mostrada por /info y la que genera /buscardatoslibro comparten
# exactamente los mismos campos y etiquetas.
CAMPOS_INFO_LIBRO = (
    ("📖 Título", "libro"),
    ("✍️ Autor", "autor"),
    ("🎭 Temática", "tematica"),
    ("✨ Características", "caracteristicas"),
    ("📚 Formatos", "formatos"),
    ("📄 Páginas", "paginas"),
    ("📝 Sinopsis", "sinopsis"),
    ("🗂️ Saga", "saga"),
)


def formatear_ficha_libro(datos: dict, incluir_vacios: bool = False) -> str:
    """Devuelve la ficha de libro con el formato común del bot."""
    lineas = []
    for etiqueta, campo in CAMPOS_INFO_LIBRO:
        valor = datos.get(campo)
        if valor or incluir_vacios:
            lineas.append(f"{etiqueta}: {valor or 'No disponible'}")
    return "\n".join(lineas)

from app.db import (
    ver_club,
    cambiar_libro,
    cambiar_capitulos,
    modificar_campo,
    apuntar_lector,
    borrar_lector,
    marcar_leido,
    desmarcar_leido,
    ver_lectores,
    grupo_autorizado,
    autorizar_grupo,
    desautorizar_grupo,
    guardar_capitulos_contenido,
    obtener_capitulo_contenido,
    obtener_capitulos_contenido,
    listar_capitulos_contenido,
    quienes_faltan,
    activar_modo_presion,
    desactivar_modo_presion,
    grupos_con_modo_presion,
    registrar_envio_presion,
    activar_modo_verguenza,
    desactivar_modo_verguenza,
    lector_pendiente_verguenza,
    registrar_envio_verguenza,
    activar_auto_resumen,
    desactivar_auto_resumen,
    auto_resumen_activo,
)
from app.utils import (
    configurar_whitelist,
    es_owner,
    nombre_de_usuario,
    lista_progreso,
    parsear_capitulos,
    formato_capitulos,
)


async def check_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtro que se ejecuta antes de cada comando. Lanza ApplicationHandlerStop si no autorizado."""
    from app.utils import WHITELIST_ENABLED
    if not WHITELIST_ENABLED:
        return
    if update.effective_chat and grupo_autorizado(update.effective_chat.id):
        return
    # Permitir siempre /autorizar al owner
    if update.message and update.message.text:
        cmd = update.message.text.split()[0].split("@")[0]
        if cmd == "/autorizar" and es_owner(update.effective_user.id):
            return
    if update.message:
        await update.message.reply_text("⛔ Este grupo no está autorizado. Contacta con el propietario del bot.")
    raise ApplicationHandlerStop()


async def es_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    miembro = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    return miembro.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


# ─── Comandos ────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Este es el Club de Lectura Bot. ¡Bienvenido!")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📌 Básicos:\n"
        "/start — Mensaje de bienvenida\n"
        "/ayuda — Muestra esta ayuda\n"
        "/estado — Estado actual del club\n"
        "\n📖 Libro:\n"
        "/cambiarlibro <título> — Cambiar el libro (admin)\n"
        "/info — Información del libro\n"
        "/buscardatoslibro <título, autor, idioma...> — Buscar ficha de un libro con IA\n"
        "/meapunto — Apuntarse a la lectura\n"
        "/meborro — Borrarse de la lectura\n"
        "/apuntados — Ver quién está apuntado\n"
        "\n📑 Capítulos:\n"
        "/cambiarcapitulos <rango> — Cambiar los capítulos (admin)\n"
        "/leido — Marcar los capítulos como leídos\n"
        "/noleido — Desmarcar si lo marcaste por error\n"
        "/progreso — Ver el progreso de los capítulos\n"
        "/subircapitulos — Subir contenido en ZIP (admin)\n"
        "/listarcapitulos — Ver capítulos subidos\n"
        "/vercapitulo <n> — Previsualizar un capítulo\n"
        "/resumen [rango] — Resumen IA de los capítulos\n"
        "/activarautoresumen — Resumen automático al terminar todos (admin)\n"
        "/desactivarautoresumen — Desactivar resumen automático (admin)\n"
        "/pregunta <texto> — Pregunta a la IA sobre el libro\n"
        "\n🏷️ Metadatos (admin):\n"
        "/modificartitulo <texto>\n"
        "/modificarautor <texto>\n"
        "/modificartematica <texto>\n"
        "/modificarcaracteristicas <texto>\n"
        "/modificarformatos <texto>\n"
        "/modificarpaginas <número>\n"
        "/modificarsinopsis <texto>\n"
        "/modificarsaga <texto>\n"
        "\n🔥 Modo presión (admin):\n"
        "/activarpresion — Activar recordatorios automáticos\n"
        "/desactivarpresion — Desactivar recordatorios\n"
        "  Si quedan lectores pendientes: GIF tras 1 semana,\n"
        "  cada 2 días tras 2 semanas, cada día tras 3 semanas.\n"
        "\n😳 Modo vergüenza (admin):\n"
        "/activarverguenza — Señalar al último lector pendiente\n"
        "/desactivarverguenza — Desactivar el modo vergüenza"
    )
    if es_owner(update.effective_user.id):
        texto += (
            "\n\n🔧 Comandos de propietario:\n"
            "/autorizar — Autorizar este grupo\n"
            "/desautorizar — Desautorizar este grupo"
        )
    await update.message.reply_text(texto)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    club = ver_club(update.effective_chat.id)
    if not club or not club['libro']:
        await update.message.reply_text("No hay ningún libro configurado.")
        return

    await update.message.reply_text(formatear_ficha_libro(club))


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    club = ver_club(update.effective_chat.id)
    if not club:
        await update.message.reply_text("Todavía no hay nada configurado en este grupo.")
        return

    caps = formato_capitulos(club['capitulos']) if club['capitulos'] else 'No definidos'
    texto = (
        f"📖 Libro: {club['libro'] or 'No definido'}\n"
        f"📑 {caps}"
    )
    await update.message.reply_text(texto)


async def setlibro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden cambiar el libro.")
        return

    titulo = " ".join(context.args).strip()
    if not titulo:
        await update.message.reply_text("Uso: /cambiarlibro Título del libro")
        return

    cambiar_libro(update.effective_chat.id, update.effective_chat.title, titulo)
    await update.message.reply_text(f"📖 Libro actualizado a: {titulo}")


async def setcapitulos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden cambiar los capítulos.")
        return

    texto = " ".join(context.args).strip()
    if not texto:
        await update.message.reply_text(
            "Uso:\n"
            "/cambiarcapitulos 5-8\n"
            "/cambiarcapitulos 5,6,7,8\n"
            "/cambiarcapitulos 5, 6, 7, 8"
        )
        return

    caps = parsear_capitulos(texto)
    if caps is None:
        await update.message.reply_text(
            "❌ Formato no válido. Usa uno de estos formatos:\n"
            "• Rango: 5-8\n"
            "• Lista: 5,6,7,8\n"
            "• Lista con espacios: 5, 6, 7, 8"
        )
        return

    caps_str = ",".join(str(c) for c in caps)
    cambiar_capitulos(update.effective_chat.id, update.effective_chat.title, caps_str)
    await update.message.reply_text(f"📑 Toca leer: {formato_capitulos(caps_str)}")


async def meapunto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    apuntar_lector(
        chat_id=update.effective_chat.id,
        nombre_grupo=update.effective_chat.title,
        user_id=user.id,
        nombre=nombre_de_usuario(user),
        username=user.username,
    )
    await update.message.reply_text("✅ Apuntado a la lectura del libro actual.")


async def meborro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    borrar_lector(update.effective_chat.id, update.effective_user.id)
    await update.message.reply_text("👋 Te has borrado de la lectura del libro actual.")


async def apuntados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lista = ver_lectores(update.effective_chat.id)
    if not lista:
        await update.message.reply_text("No hay nadie apuntado a la lectura.")
        return

    texto = "Apuntados a la lectura:\n" + "\n".join(f"• {r['nombre']}" for r in lista)
    await update.message.reply_text(texto)


async def leido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        marcar_leido(chat_id, update.effective_user.id)
        await update.message.reply_text("✅ Marcado como leído para los capítulos actuales.")
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    await _enviar_verguenza_si_corresponde(chat_id, context)

    if auto_resumen_activo(chat_id) and not quienes_faltan(chat_id):
        club = ver_club(chat_id)
        if club and club['capitulos']:
            caps = [int(c) for c in club['capitulos'].split(",")]
            await update.message.reply_text("🎉 ¡Todos han leído los capítulos! Generando resumen automático...")

            async def _send(text, **kwargs):
                return await context.bot.send_message(chat_id, text, **kwargs)

            await _ejecutar_resumen(chat_id, caps, context, _send)


async def noleido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        desmarcar_leido(update.effective_chat.id, update.effective_user.id)
        await update.message.reply_text("↩️ Desmarcado. Ya no figuras como leído en estos capítulos.")
    except ValueError as e:
        await update.message.reply_text(str(e))


async def progreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lista = lista_progreso(update.effective_chat.id)
    if not lista:
        await update.message.reply_text("No hay nadie apuntado todavía.")
        return

    await update.message.reply_text(lista)


# ─── Comandos de modificación de libro (admin) ───────────────


NOMBRES_CAMPO = {
    "titulo": "título",
    "autor": "autor",
    "tematica": "temática",
    "caracteristicas": "características",
    "formatos": "formatos",
    "paginas": "páginas",
    "sinopsis": "sinopsis",
    "saga": "saga",
}


def _handler_modificar(campo: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await es_admin(update, context):
            await update.message.reply_text("Solo los admins pueden modificar el libro.")
            return

        club = ver_club(update.effective_chat.id)
        if not club or not club['libro']:
            await update.message.reply_text("Primero hay que configurar un libro con /cambiarlibro.")
            return

        valor = " ".join(context.args).strip()
        if not valor:
            await update.message.reply_text(f"Uso: /modificar{campo} <valor>")
            return

        try:
            modificar_campo(update.effective_chat.id, campo, valor)
            await update.message.reply_text(f"✅ {NOMBRES_CAMPO[campo].capitalize()} actualizado.")
        except ValueError as e:
            await update.message.reply_text(str(e))

    return handler


modificartitulo = _handler_modificar("titulo")
modificarautor = _handler_modificar("autor")
modificartematica = _handler_modificar("tematica")
modificarcaracteristicas = _handler_modificar("caracteristicas")
modificarformatos = _handler_modificar("formatos")
modificarpaginas = _handler_modificar("paginas")
modificarsinopsis = _handler_modificar("sinopsis")
modificarsaga = _handler_modificar("saga")


# ─── Comandos de contenido de capítulos ──────────────────────


async def _ejecutar_resumen(
    chat_id: int,
    caps: list[int],
    context: ContextTypes.DEFAULT_TYPE,
    send_fn,  # async (text, **kwargs) -> Message
):
    """Núcleo reutilizable: obtén contenido, llama a la IA y envía el resumen."""
    from html import escape
    from app.ai import generar_resumen

    contenidos = obtener_capitulos_contenido(chat_id, caps)
    faltantes = [c for c in caps if c not in contenidos]
    if not contenidos:
        nums = ", ".join(str(c) for c in faltantes)
        await send_fn(
            f"❌ No hay contenido subido para los capítulos: {nums}\n"
            "Súbelos primero con /subircapitulos."
        )
        return

    aviso_faltantes = ""
    if faltantes:
        nums = ", ".join(str(c) for c in faltantes)
        aviso_faltantes = f"\n⚠️ Sin contenido para los capítulos: {nums}"

    caps_con_contenido = [c for c in caps if c in contenidos]
    texto_caps = "\n\n".join(
        f"--- Capítulo {num} ---\n{contenidos[num]}" for num in caps_con_contenido
    )

    aviso = await send_fn("⏳ Generando resumen...")

    try:
        resultado = await generar_resumen(texto_caps)
    except ValueError as e:
        msg = str(e)
        if "content_filter" in msg:
            logger.warning("Resumen bloqueado por filtro de contenido")
            await aviso.edit_text("⚠️ La IA ha bloqueado la respuesta por filtro de contenido. Prueba con menos capítulos o un rango diferente.")
        elif "rate_limit" in msg:
            logger.warning("Resumen bloqueado por rate limit")
            await aviso.edit_text("⚠️ Límite de peticiones alcanzado. Espera un poco y vuelve a intentarlo.")
        else:
            logger.error("Error inesperado en generar_resumen: %s", msg)
            await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return
    except Exception:
        logger.exception("Error al llamar a generar_resumen")
        await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return

    caps_str = formato_capitulos(",".join(str(c) for c in caps_con_contenido))
    header = f"📝 Resumen — {caps_str}{aviso_faltantes}"

    await aviso.delete()
    await send_fn(header)

    bloques = [b.strip() for b in resultado.split("@@@@@@@@") if b.strip()]
    if not bloques:
        bloques = [resultado.strip()]

    for bloque in bloques:
        html = f"<blockquote expandable>{escape(bloque)}</blockquote>"
        await send_fn(html, parse_mode="HTML")


async def subircapitulos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden subir capítulos.")
        return

    doc = update.message.document
    if not doc and update.message.reply_to_message:
        doc = update.message.reply_to_message.document
    if not doc:
        await update.message.reply_text(
            "Envía un archivo ZIP con el comando /subircapitulos como descripción del archivo, "
            "o responde a un ZIP con /subircapitulos.\n"
            "Los archivos dentro deben llamarse con el número del capítulo: "
            "0.txt para el contexto extra previo al libro, seguido de 1.txt, 2.txt, etc."
        )
        return

    if not doc.file_name or not doc.file_name.lower().endswith(".zip"):
        await update.message.reply_text("El archivo debe ser un ZIP.")
        return

    import zipfile
    import io
    import re

    archivo = await doc.get_file()
    buf = io.BytesIO()
    await archivo.download_to_memory(buf)
    buf.seek(0)

    try:
        zf = zipfile.ZipFile(buf)
    except zipfile.BadZipFile:
        await update.message.reply_text("❌ El archivo no es un ZIP válido.")
        return

    capitulos = []
    ignorados = []
    patron = re.compile(r"^(\d+)\.txt$")

    for nombre in zf.namelist():
        # Ignorar directorios
        if nombre.endswith("/"):
            continue
        # Usar solo el nombre del archivo (ignorar carpetas dentro del zip)
        base = nombre.split("/")[-1]
        m = patron.match(base)
        if m:
            numero = int(m.group(1))
            contenido = zf.read(nombre).decode("utf-8", errors="replace")
            capitulos.append((numero, contenido))
        else:
            ignorados.append(nombre)

    zf.close()

    if not capitulos:
        await update.message.reply_text(
            "❌ No se encontró ningún archivo con formato válido "
            "(0.txt para contexto extra previo al libro; 1.txt, 2.txt, ... para capítulos)."
        )
        return

    guardar_capitulos_contenido(update.effective_chat.id, capitulos)
    capitulos.sort(key=lambda x: x[0])
    nums = ", ".join(str(c[0]) for c in capitulos)

    texto = f"✅ Subidos {len(capitulos)} capítulo(s): {nums}"
    if any(numero == 0 for numero, _ in capitulos):
        texto += "\nℹ️ El archivo 0.txt se usará como contexto extra previo al libro."
    if ignorados:
        texto += f"\n\n⚠️ Archivos ignorados ({len(ignorados)}):\n" + "\n".join(f"• {n}" for n in ignorados)

    await update.message.reply_text(texto)


async def vercapitulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /vercapitulo <número>")
        return

    try:
        numero = int(context.args[0])
    except ValueError:
        await update.message.reply_text("El número de capítulo debe ser un número entero.")
        return

    contenido = obtener_capitulo_contenido(update.effective_chat.id, numero)
    if not contenido:
        if numero == 0:
            await update.message.reply_text(
                "No hay contenido extra previo al libro subido como capítulo 0."
            )
        else:
            await update.message.reply_text(f"No hay contenido subido para el capítulo {numero}.")
        return

    lineas = contenido.splitlines()[:10]
    preview = "\n".join(lineas)
    total = len(contenido.splitlines())
    if numero == 0:
        titulo = "📖 Contexto extra previo al libro (capítulo 0)"
    else:
        titulo = f"📖 Capítulo {numero}"
    texto = f"{titulo} (primeras líneas, {total} total):\n\n{preview}"
    if total > 10:
        texto += "\n\n[...]"
    await update.message.reply_text(texto)


async def listarcapitulos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = listar_capitulos_contenido(update.effective_chat.id)
    if not nums:
        await update.message.reply_text("No hay capítulos subidos.")
        return

    texto = f"📄 Capítulos subidos ({len(nums)}):\n" + ", ".join(str(n) for n in nums)
    if 0 in nums:
        texto += "\n\nℹ️ El capítulo 0 contiene contexto extra previo al libro."
    await update.message.reply_text(texto)


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    club = ver_club(chat_id)

    if context.args:
        caps = parsear_capitulos(" ".join(context.args))
        if caps is None:
            await update.message.reply_text(
                "Formato no válido. Usa: /resumen 1-5 o /resumen 1,2,3"
            )
            return
    elif club and club['capitulos']:
        caps = [int(c) for c in club['capitulos'].split(",")]
    else:
        await update.message.reply_text("No hay capítulos activos. Usa /resumen <rango> para indicarlos.")
        return

    async def send_fn(text, **kwargs):
        return await update.message.reply_text(text, **kwargs)

    await _ejecutar_resumen(chat_id, caps, context, send_fn)


async def pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from html import escape
    from app.ai import responder_pregunta

    chat_id = update.effective_chat.id
    texto_pregunta = " ".join(context.args).strip() if context.args else ""
    if not texto_pregunta:
        await update.message.reply_text("Uso: /pregunta ¿Qué pasó con tal personaje?")
        return

    club = ver_club(chat_id)
    if not club or not club['capitulos']:
        await update.message.reply_text("No hay capítulos activos configurados.")
        return

    # Capítulos anteriores y, si todos han terminado, también el bloque activo.
    caps_activos = [int(c) for c in club['capitulos'].split(",")]
    primer_activo = min(caps_activos)
    # El capítulo 0 puede contener contexto previo al comienzo del libro.
    caps_contexto = list(range(0, primer_activo))

    lectores = ver_lectores(chat_id)
    todos_han_leido = bool(lectores) and not quienes_faltan(chat_id)
    if todos_han_leido:
        caps_contexto.extend(caps_activos)

    if not caps_contexto:
        await update.message.reply_text("No hay capítulos anteriores al bloque activo para usar como contexto.")
        return

    caps_contexto = sorted(set(caps_contexto))
    contenidos = obtener_capitulos_contenido(chat_id, caps_contexto)
    if not contenidos:
        await update.message.reply_text(
            "No hay contenido subido para los capítulos disponibles como contexto.\n"
            "Súbelos primero con /subircapitulos."
        )
        return

    caps_disponibles = sorted(contenidos.keys())
    texto_caps = "\n\n".join(
        f"--- Capítulo {num} ---\n{contenidos[num]}" for num in caps_disponibles
    )

    aviso = await update.message.reply_text("⏳ Pensando...")

    try:
        resultado = await responder_pregunta(texto_caps, texto_pregunta)
    except ValueError as e:
        msg = str(e)
        if "content_filter" in msg:
            logger.warning("Pregunta bloqueada por filtro de contenido")
            await aviso.edit_text("⚠️ La IA ha bloqueado la respuesta por filtro de contenido.")
        elif "rate_limit" in msg:
            logger.warning("Pregunta bloqueada por rate limit")
            await aviso.edit_text("⚠️ Límite de peticiones alcanzado. Espera un poco y vuelve a intentarlo.")
        else:
            logger.error("Error inesperado en responder_pregunta: %s", msg)
            await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return
    except Exception:
        logger.exception("Error al llamar a responder_pregunta")
        await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return

    header = f"❓ {texto_pregunta}"
    MAX = 4000
    resultado_escaped = escape(resultado)
    trozos = [resultado_escaped[i:i + MAX] for i in range(0, len(resultado_escaped), MAX)]

    await aviso.delete()
    for i, trozo in enumerate(trozos):
        if i == 0:
            html = f"{escape(header)}\n<blockquote expandable>{trozo}</blockquote>"
        else:
            html = f"<blockquote expandable>{trozo}</blockquote>"
        await update.message.reply_text(html, parse_mode="HTML")


async def buscardatoslibro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca una ficha de libro con la IA sin alterar el libro activo del club."""
    import json

    from app.ai import buscar_datos_libro

    consulta = " ".join(context.args).strip()
    if not consulta:
        await update.message.reply_text(
            "Uso: /buscardatoslibro <título, autor, idioma o editorial>\n"
            "Ejemplo: /buscardatoslibro El camino de los reyes de Brandon Sanderson"
        )
        return

    aviso = await update.message.reply_text("🔎 Buscando datos del libro...")
    try:
        resultado = await buscar_datos_libro(consulta)
    except ValueError as e:
        msg = str(e)
        if "content_filter" in msg:
            logger.warning("Búsqueda de libro bloqueada por filtro de contenido")
            await aviso.edit_text("⚠️ La IA ha bloqueado la respuesta por filtro de contenido.")
        elif "rate_limit" in msg:
            logger.warning("Búsqueda de libro bloqueada por rate limit")
            await aviso.edit_text("⚠️ Límite de peticiones alcanzado. Espera un poco y vuelve a intentarlo.")
        else:
            logger.error("Error inesperado en buscar_datos_libro: %s", msg)
            await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return
    except Exception:
        logger.exception("Error al llamar a buscar_datos_libro")
        await aviso.edit_text("❌ Error al conectar con el servicio de IA.")
        return

    try:
        datos = json.loads(resultado)
    except json.JSONDecodeError:
        logger.warning("La IA devolvió una ficha de libro con JSON no válido: %r", resultado)
        await aviso.edit_text("❌ La IA ha devuelto una ficha con un formato no válido. Vuelve a intentarlo.")
        return

    if not isinstance(datos, dict) or datos.get("identificado") is not True:
        await aviso.edit_text(
            "No he podido identificar el libro con seguridad. "
            "Prueba a incluir el título y el autor."
        )
        return

    ficha = formatear_ficha_libro(datos, incluir_vacios=True)

    # Telegram limita cada mensaje a 4096 caracteres; el prompt solicita 3800,
    # pero esta protección evita fallos si el modelo no sigue el límite.
    max_chars = 4000
    trozos = [ficha[i:i + max_chars] for i in range(0, len(ficha), max_chars)]
    await aviso.delete()
    for trozo in trozos or ["No se han encontrado datos para ese libro."]:
        await update.message.reply_text(trozo)



# ─── Modo presión ─────────────────────────────────────────────

_GIF_PRESION = "https://media.giphy.com/media/JzOyy8vKMCwvK/giphy.gif"


async def activarmodopresion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden activar el modo presión.")
        return

    club = ver_club(update.effective_chat.id)
    if not club or not club['capitulos']:
        await update.message.reply_text("Primero hay que configurar capítulos con /cambiarcapitulos.")
        return

    activar_modo_presion(update.effective_chat.id)
    await update.message.reply_text(
        "🔥 Modo presión activado. Si quedan lectores pendientes:\n"
        "• Tras 1 semana: se enviará un recordatorio\n"
        "• Tras 2 semanas: cada 2 días\n"
        "• Tras 3 semanas: cada día"
    )


async def desactivarmodopresion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden desactivar el modo presión.")
        return

    desactivar_modo_presion(update.effective_chat.id)
    await update.message.reply_text("🙌 Modo presión desactivado.")


# ─── Modo vergüenza ──────────────────────────────────────────

_GIF_VERGUENZA = (
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExaXZxeWdjOGs5dW1jemJzbDMwYndxNWQyMXoyMnk5dXR5am1mcHMyNyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
    "vX9WcCiWwUF7G/giphy.gif"
)


async def activarmodoverguenza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden activar el modo vergüenza.")
        return

    club = ver_club(update.effective_chat.id)
    if not club or not club['capitulos']:
        await update.message.reply_text("Primero hay que configurar capítulos con /cambiarcapitulos.")
        return

    activar_modo_verguenza(update.effective_chat.id)
    await update.message.reply_text(
        "😳 Modo vergüenza activado. Cuando solo quede una persona por leer, "
        "será mencionada públicamente."
    )
    await _enviar_verguenza_si_corresponde(update.effective_chat.id, context)


async def desactivarmodoverguenza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden desactivar el modo vergüenza.")
        return

    desactivar_modo_verguenza(update.effective_chat.id)
    await update.message.reply_text("😌 Modo vergüenza desactivado.")


async def _enviar_verguenza_si_corresponde(
    chat_id: int, context: ContextTypes.DEFAULT_TYPE
):
    pendiente = lector_pendiente_verguenza(chat_id)
    if not pendiente:
        return

    if pendiente['username']:
        mencion = f"@{pendiente['username']}"
    else:
        nombre = html.escape(pendiente['nombre'])
        mencion = f'<a href="tg://user?id={pendiente["user_id"]}">{nombre}</a>'

    texto = (
        f"{mencion} es el último miembro por leer los capítulos. "
        "Que el peso de la vergüenza caiga sobre ti."
    )
    try:
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=_GIF_VERGUENZA,
            caption=texto,
            parse_mode="HTML",
        )
        registrar_envio_verguenza(chat_id)
    except Exception:
        logger.exception("Error enviando el aviso de vergüenza al chat %s", chat_id)


async def activarautoresumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden activar el auto-resumen.")
        return

    activar_auto_resumen(update.effective_chat.id)
    await update.message.reply_text(
        "🤖 Auto-resumen activado. Cuando el último lector marque /leido "
        "se generará automáticamente el resumen de los capítulos."
    )


async def desactivarautoresumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden desactivar el auto-resumen.")
        return

    desactivar_auto_resumen(update.effective_chat.id)
    await update.message.reply_text("🔕 Auto-resumen desactivado.")


async def check_modo_presion(context: ContextTypes.DEFAULT_TYPE):
    """Job diario que envía el GIF de presión a los grupos que lo tienen activo."""
    from datetime import datetime, timezone

    grupos = grupos_con_modo_presion()
    for grupo in grupos:
        chat_id = grupo['chat_id']
        caps_cambiados_en = grupo['capitulos_cambiados_en']
        if not caps_cambiados_en:
            continue

        faltan = quienes_faltan(chat_id)
        if not faltan:
            continue

        cambiado = datetime.fromisoformat(caps_cambiados_en).replace(tzinfo=timezone.utc)
        ahora = datetime.now(timezone.utc)
        dias = (ahora - cambiado).days

        if dias < 7:
            continue

        ultimo_str = grupo.get('presion_enviado_en')
        if ultimo_str:
            ultimo = datetime.fromisoformat(ultimo_str).replace(tzinfo=timezone.utc)
            dias_desde_envio = (ahora - ultimo).days
        else:
            dias_desde_envio = None

        if dias >= 21:
            debe_enviar = dias_desde_envio is None or dias_desde_envio >= 1
        elif dias >= 14:
            debe_enviar = dias_desde_envio is None or dias_desde_envio >= 2
        else:  # 7 <= dias < 14
            debe_enviar = dias_desde_envio is None

        if debe_enviar:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=_GIF_PRESION)
                registrar_envio_presion(chat_id)
            except Exception:
                logger.exception("Error enviando GIF de presión al chat %s", chat_id)


# ─── Comandos de propietario ───────────────────────────────────────


async def autorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_owner(update.effective_user.id):
        await update.message.reply_text("Solo el propietario del bot puede usar este comando.")
        return

    chat_id = update.effective_chat.id
    autorizar_grupo(chat_id)
    await update.message.reply_text(f"✅ Grupo autorizado (ID: {chat_id}).")


async def desautorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_owner(update.effective_user.id):
        await update.message.reply_text("Solo el propietario del bot puede usar este comando.")
        return

    chat_id = update.effective_chat.id
    desautorizar_grupo(chat_id)
    await update.message.reply_text(f"⛔ Grupo desautorizado (ID: {chat_id}).")
