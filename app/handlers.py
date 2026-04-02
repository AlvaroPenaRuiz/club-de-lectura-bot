from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from app.db import (
    ver_club,
    cambiar_libro,
    cambiar_bloque,
    apuntar_lector,
    borrar_lector,
    marcar_leido,
    ver_lectores,
    quienes_leyeron,
    quienes_faltan,
)


def nombre_de_usuario(user) -> str:
    nombre = " ".join(p for p in [user.first_name, user.last_name] if p).strip()
    return nombre or user.username or str(user.id)


def _lista_progreso(chat_id: int) -> str:
    leidos = quienes_leyeron(chat_id)
    faltan = quienes_faltan(chat_id)
    ids_leidos = {r['user_id'] for r in leidos}
    lineas = []
    for r in leidos + faltan:
        marca = "✅" if r['user_id'] in ids_leidos else "⬜"
        lineas.append(f"{marca} {r['nombre']}")
    return "\n".join(lineas)


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
        "Comandos disponibles:\n"
        "/start — Mensaje de bienvenida\n"
        "/ayuda — Muestra esta ayuda\n"
        "/estado — Estado actual del club\n"
        "/cambiarlibro <título> — Cambiar el libro (admin)\n"
        "/cambiarbloque <rango> — Cambiar el bloque (admin)\n"
        "/meapunto — Apuntarse a la lectura del libro actual\n"
        "/meborro — Borrarse de la lectura del libro actual\n"
        "/apuntados — Ver quién está apuntado\n"
        "/leido — Marcar el bloque como leído\n"
        "/leidos — Ver quién ha terminado\n"
        "/pendientes — Ver quién falta"
    )
    await update.message.reply_text(texto)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    club = ver_club(update.effective_chat.id)
    if not club:
        await update.message.reply_text("Todavía no hay nada configurado en este grupo.")
        return

    leidos = quienes_leyeron(update.effective_chat.id)
    faltan = quienes_faltan(update.effective_chat.id)
    lista = _lista_progreso(update.effective_chat.id)

    texto = (
        f"📖 Libro: {club['libro'] or 'No definido'}\n"
        f"📑 Bloque: {club['bloque'] or 'No definido'}\n"
        f"✅ Leídos: {len(leidos)} | ⏳ Pendientes: {len(faltan)}"
    )
    if lista:
        texto += f"\n\n{lista}"
    await update.message.reply_text(texto)


async def setlibro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden cambiar el libro.")
        return

    titulo = " ".join(context.args).strip()
    if not titulo:
        await update.message.reply_text("Uso: /setlibro Título del libro")
        return

    cambiar_libro(update.effective_chat.id, update.effective_chat.title, titulo)
    await update.message.reply_text(f"📖 Libro actualizado a: {titulo}")


async def setbloque(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await es_admin(update, context):
        await update.message.reply_text("Solo los admins pueden cambiar el bloque.")
        return

    bloque = " ".join(context.args).strip()
    if not bloque:
        await update.message.reply_text("Uso: /setbloque 5-8  o  /setbloque 5,6,7,8")
        return

    cambiar_bloque(update.effective_chat.id, update.effective_chat.title, bloque)
    await update.message.reply_text(f"📑 Bloque actualizado a: {bloque}")


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
        await update.message.reply_text("✅ Marcado como leído para el bloque actual.")
    except ValueError as e:
        await update.message.reply_text(str(e))


async def leidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leyeron = quienes_leyeron(update.effective_chat.id)
    lista = _lista_progreso(update.effective_chat.id)
    if not lista:
        await update.message.reply_text("No hay nadie apuntado todavía.")
        return

    texto = f"Ya lo han leído {len(leyeron)}:\n\n{lista}"
    await update.message.reply_text(texto)


async def pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    faltan = quienes_faltan(update.effective_chat.id)
    lista = _lista_progreso(update.effective_chat.id)
    if not lista:
        await update.message.reply_text("No hay nadie apuntado todavía.")
        return

    if not faltan:
        texto = f"¡No queda nadie pendiente! 🎉\n\n{lista}"
    else:
        texto = f"Aún quedan {len(faltan)}:\n\n{lista}"
    await update.message.reply_text(texto)
