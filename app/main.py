import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update

from app.db import inicializar
from app.handlers import (
    start,
    ayuda,
    estado,
    setlibro,
    setbloque,
    meapunto,
    meborro,
    apuntados,
    leido,
    leidos,
    pendientes,
)

TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
APP_PORT = int(os.getenv('APP_PORT', '8080'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    inicializar()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("cambiarlibro", setlibro))
    app.add_handler(CommandHandler("cambiarbloque", setbloque))
    app.add_handler(CommandHandler("meapunto", meapunto))
    app.add_handler(CommandHandler("meborro", meborro))
    app.add_handler(CommandHandler("apuntados", apuntados))
    app.add_handler(CommandHandler("leido", leido))
    app.add_handler(CommandHandler("leidos", leidos))
    app.add_handler(CommandHandler("pendientes", pendientes))

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