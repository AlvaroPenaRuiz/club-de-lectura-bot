import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, Defaults, filters
from telegram import Update

from app.db import inicializar
from app.utils import configurar_whitelist
from app.handlers import (
    check_whitelist,
    start,
    ayuda,
    info,
    estado,
    setlibro,
    setcapitulos,
    meapunto,
    meborro,
    apuntados,
    leido,
    noleido,
    progreso,
    subircapitulos,
    listarcapitulos,
    modificartitulo,
    modificarautor,
    modificartematica,
    modificarcaracteristicas,
    modificarformatos,
    modificarpaginas,
    modificarsinopsis,
    modificarsaga,
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
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("cambiarlibro", setlibro))
    app.add_handler(CommandHandler("cambiarcapitulos", setcapitulos))
    app.add_handler(CommandHandler("modificartitulo", modificartitulo))
    app.add_handler(CommandHandler("modificarautor", modificarautor))
    app.add_handler(CommandHandler("modificartematica", modificartematica))
    app.add_handler(CommandHandler("modificarcaracteristicas", modificarcaracteristicas))
    app.add_handler(CommandHandler("modificarformatos", modificarformatos))
    app.add_handler(CommandHandler("modificarpaginas", modificarpaginas))
    app.add_handler(CommandHandler("modificarsinopsis", modificarsinopsis))
    app.add_handler(CommandHandler("modificarsaga", modificarsaga))
    app.add_handler(CommandHandler("meapunto", meapunto))
    app.add_handler(CommandHandler("meborro", meborro))
    app.add_handler(CommandHandler("apuntados", apuntados))
    app.add_handler(CommandHandler("leido", leido))
    app.add_handler(CommandHandler("noleido", noleido))
    app.add_handler(CommandHandler("progreso", progreso))
    app.add_handler(CommandHandler("subircapitulos", subircapitulos))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.CaptionRegex(r"^/subircapitulos"), subircapitulos))
    app.add_handler(CommandHandler("listarcapitulos", listarcapitulos))
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