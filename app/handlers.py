from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import ChatMemberStatus

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
        "/meapunto — Apuntarse a la lectura\n"
        "/meborro — Borrarse de la lectura\n"
        "/apuntados — Ver quién está apuntado\n"
        "\n📑 Capítulos:\n"
        "/cambiarcapitulos <rango> — Cambiar los capítulos (admin)\n"
        "/leido — Marcar los capítulos como leídos\n"
        "/noleido — Desmarcar si lo marcaste por error\n"
        "/progreso — Ver el progreso de los capítulos\n"
        "\n🏷️ Metadatos (admin):\n"
        "/modificartitulo <texto>\n"
        "/modificarautor <texto>\n"
        "/modificartematica <texto>\n"
        "/modificarcaracteristicas <texto>\n"
        "/modificarformatos <texto>\n"
        "/modificarpaginas <número>\n"
        "/modificarsinopsis <texto>\n"
        "/modificarsaga <texto>"
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

    campos = [
        ("📖 Título", club['libro']),
        ("✍️ Autor", club.get('autor')),
        ("🎭 Temática", club.get('tematica')),
        ("✨ Características", club.get('caracteristicas')),
        ("📚 Formatos", club.get('formatos')),
        ("📄 Páginas", club.get('paginas')),
        ("📝 Sinopsis", club.get('sinopsis')),
        ("🗂️ Saga", club.get('saga')),
    ]

    lineas = [f"{etiqueta}: {valor}" for etiqueta, valor in campos if valor]
    await update.message.reply_text("\n".join(lineas))


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
    try:
        marcar_leido(update.effective_chat.id, update.effective_user.id)
        await update.message.reply_text("✅ Marcado como leído para los capítulos actuales.")
    except ValueError as e:
        await update.message.reply_text(str(e))


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


# ─── Comandos de propietario ─────────────────────────────────


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
