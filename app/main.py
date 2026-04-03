import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, Defaults, filters
from telegram import Update

from app.db import inicializar
from app.handlers import (
    configurar_whitelist,
    check_whitelist,
    start,
    ayuda,
    estado,
    setlibro,
    setbloque,
    meapunto,
    meborro,
    apuntados,
    leido,
    noleido,
    leidos,
    pendientes,
    autorizar,
    desautorizar,
)

TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
APP_PORT = int(os.getenv('APP_PORT', '8080'))
OWNER_ID = int(os.getenv('OWNER_ID', '0')) or None
WHITELIST_ENABLED = os.getenv('WHITELIST_ENABLED', 'true').lower() != 'false'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    inicializar()
    configurar_whitelist(WHITELIST_ENABLED, OWNER_ID)

    defaults = Defaults(do_quote=False)
    app = ApplicationBuilder().token(TOKEN).defaults(defaults).build()

    # Middleware de whitelist (grupo 0 = antes que los comandos de grupo 1)
    from telegram.ext import TypeHandler
    app.add_handler(TypeHandler(Update, check_whitelist), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("cambiarlibro", setlibro))
    app.add_handler(CommandHandler("cambiarbloque", setbloque))
    app.add_handler(CommandHandler("meapunto", meapunto))
    app.add_handler(CommandHandler("meborro", meborro))
    app.add_handler(CommandHandler("apuntados", apuntados))
    app.add_handler(CommandHandler("leido", leido))
    app.add_handler(CommandHandler("noleido", noleido))
    app.add_handler(CommandHandler("leidos", leidos))
    app.add_handler(CommandHandler("pendientes", pendientes))
    app.add_handler(CommandHandler("autorizar", autorizar))
    app.add_handler(CommandHandler("desautorizar", desautorizar))

    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=APP_PORT,
            url_path="/telegram/webhook",
            webhook_url=f"{WEBHOOK_URL}",
            secret_token=WEBHOOK_SECRET,
        )
    else:
        app.run_polling()