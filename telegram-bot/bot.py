#!/usr/bin/env python3
"""
VerifiCuba Telegram Bot
Python + python-telegram-bot + PocketBase REST API
Polls PocketBase every 30s for new pending businesses, sends inline buttons to verify/reject
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# Load env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PB_URL = os.getenv("PB_URL", "http://localhost:8090")
PB_ADMIN_EMAIL = os.getenv("PB_ADMIN_EMAIL", "arangorobe380@gmail.com")
PB_ADMIN_PASS = os.getenv("PB_ADMIN_PASS")

if not BOT_TOKEN or not CHAT_ID or not PB_ADMIN_PASS:
    raise ValueError("Missing required env vars: BOT_TOKEN, CHAT_ID, PB_ADMIN_PASS")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── PocketBase Client ───
class PocketBaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self._admin_token: Optional[str] = None
        self._token_expiry = 0

    async def _get_admin_token(self) -> str:
        import time
        if self._admin_token and time.time() < self._token_expiry:
            return self._admin_token
        
        resp = await self.client.post(
            "/api/admins/auth-with-password",
            json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASS}
        )
        resp.raise_for_status()
        data = resp.json()
        self._admin_token = data["token"]
        self._token_expiry = time.time() + 3600
        return self._admin_token

    async def _auth_headers(self) -> dict:
        token = await self._get_admin_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def get_pending_negocios(self) -> list:
        """Get all negocios with estado='Pendiente'"""
        headers = await self._auth_headers()
        resp = await self.client.get(
            "/api/collections/negocios/records",
            headers=headers,
            params={"filter": "estado='Pendiente'", "sort": "-created", "perPage": 50}
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def get_negocio(self, record_id: str) -> dict:
        headers = await self._auth_headers()
        resp = await self.client.get(
            f"/api/collections/negocios/records/{record_id}",
            headers=headers,
            params={"expand": "categoria"}
        )
        resp.raise_for_status()
        return resp.json()

    async def update_negocio(self, record_id: str, data: dict) -> dict:
        headers = await self._auth_headers()
        resp = await self.client.patch(
            f"/api/collections/negocios/records/{record_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        return resp.json()

    async def verify_negocio(self, record_id: str) -> dict:
        return await self.update_negocio(record_id, {
            "estado": "Verificado",
            "plan": "Destacado",
            "fecha_verificacion": datetime.now().strftime("%Y-%m-%d")
        })

    async def reject_negocio(self, record_id: str) -> dict:
        return await self.update_negocio(record_id, {
            "estado": "Suspendido"
        })

    async def get_stats(self) -> dict:
        headers = await self._auth_headers()
        stats = {}
        for estado in ["Pendiente", "Verificado", "Activo", "Suspendido"]:
            resp = await self.client.get(
                "/api/collections/negocios/records",
                headers=headers,
                params={"filter": f"estado='{estado}'", "perPage": 1}
            )
            stats[estado] = resp.json().get("totalItems", 0)
        return stats

    async def close(self):
        await self.client.aclose()


pb = PocketBaseClient(PB_URL)

# ─── Bot Handlers ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        await update.message.reply_text("No autorizado.")
        return
    
    await update.message.reply_text(
        "🤖 VerifiCuba Bot\n\n"
        "Comandos:\n"
        "/negocios - Últimos 10 negocios\n"
        "/pendientes - Negocios sin verificar\n"
        "/stats - Estadísticas\n"
        "/buscar <texto> - Buscar negocio"
    )

async def cmd_negocios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    headers = await pb._auth_headers()
    resp = await pb.client.get(
        "/api/collections/negocios/records",
        headers=headers,
        params={"sort": "-created", "perPage": 10, "expand": "categoria"}
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    
    if not items:
        await update.message.reply_text("No hay negocios registrados.")
        return
    
    msg = "📋 Últimos 10 negocios:\n\n"
    for i, n in enumerate(items, 1):
        cat = n.get("expand", {}).get("categoria", {}).get("nombre", "Sin categoría")
        msg += (
            f"{i}. 🏢 {n['nombre']}\n"
            f"   📂 {cat} | 📍 {n.get('municipio','')}, {n.get('provincia','')}\n"
            f"   🏷️ {n.get('estado','')} | 📱 {n.get('whatsapp','N/A')}\n\n"
        )
    
    await update.message.reply_text(msg)

async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    items = await pb.get_pending_negocios()
    
    if not items:
        await update.message.reply_text("✅ No hay pendientes. Todo verificado.")
        return
    
    for n in items:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Verificar", callback_data=f"verify_{n['id']}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{n['id']}")
        ]])
        
        msg = (
            f"🆕 Nuevo pre-registro\n\n"
            f"🏢 Negocio: {n['nombre']}\n"
            f"📍 {n.get('municipio','')}, {n.get('provincia','')}\n"
            f"📱 WhatsApp: {n.get('whatsapp','Sin WhatsApp')}\n"
            f"🏷️ Tipo: {n.get('tipo_actor','No especificado')}\n\n"
            f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await update.message.reply_text(msg, reply_markup=keyboard)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    stats = await pb.get_stats()
    total = sum(stats.values())
    verificados = stats.get("Verificado", 0) + stats.get("Activo", 0)
    
    await update.message.reply_text(
        f"📊 VerifiCuba Stats\n\n"
        f"Total: {total}\n"
        f"Verificados: {stats.get('Verificado', 0)}\n"
        f"Activos: {stats.get('Activo', 0)}\n"
        f"Pendientes: {stats.get('Pendiente', 0)}\n"
        f"Suspendidos: {stats.get('Suspendido', 0)}\n\n"
        f"💰 Ingresos est.: {verificados * 500} CUP/mes"
    )

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Uso: /buscar <nombre>")
        return
    
    headers = await pb._auth_headers()
    resp = await pb.client.get(
        "/api/collections/negocios/records",
        headers=headers,
        params={"filter": f"nombre~'{query}'", "perPage": 10, "expand": "categoria"}
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    
    if not items:
        await update.message.reply_text(f'Sin resultados para "{query}"')
        return
    
    msg = "🔍 Resultados:\n\n"
    for n in items:
        cat = n.get("expand", {}).get("categoria", {}).get("nombre", "Sin categoría")
        msg += f"🏢 {n['nombre']} - {cat} - {n.get('municipio','')}, {n.get('provincia','')} - {n.get('estado','')}\n"
    
    await update.message.reply_text(msg)

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    query = update.callback_query
    await query.answer()
    
    action, record_id = query.data.split("_", 1)
    
    if action == "verify":
        await pb.verify_negocio(record_id)
        await query.edit_message_text(query.message.text + "\n\n✅ VERIFICADO")
    elif action == "reject":
        await pb.reject_negocio(record_id)
        await query.edit_message_text(query.message.text + "\n\n❌ RECHAZADO")

# ─── Background Poller ───
async def poll_pending(application: Application):
    """Poll PocketBase every 30s for new Pendiente negocios"""
    seen_ids = set()
    
    while True:
        try:
            items = await pb.get_pending_negocios()
            for n in items:
                if n["id"] not in seen_ids:
                    seen_ids.add(n["id"])
                    
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Verificar", callback_data=f"verify_{n['id']}"),
                        InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{n['id']}")
                    ]])
                    
                    msg = (
                        f"🆕 Nuevo pre-registro\n\n"
                        f"🏢 Negocio: {n['nombre']}\n"
                        f"📍 {n.get('municipio','')}, {n.get('provincia','')}\n"
                        f"📱 WhatsApp: {n.get('whatsapp','Sin WhatsApp')}\n"
                        f"🏷️ Tipo: {n.get('tipo_actor','No especificado')}\n\n"
                        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    )
                    
                    await application.bot.send_message(
                        chat_id=CHAT_ID, text=msg, reply_markup=keyboard
                    )
        except Exception as e:
            logger.error(f"Poll error: {e}")
        
        await asyncio.sleep(30)


# ─── Main ───
async def main():
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("negocios", cmd_negocios))
    application.add_handler(CommandHandler("pendientes", cmd_pendientes))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("buscar", cmd_buscar))
    application.add_handler(CallbackQueryHandler(callback_query))
    
    # Start poller
    poller_task = asyncio.create_task(poll_pending(application))
    
    # Run bot
    logger.info("Bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        poller_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await pb.close()

if __name__ == "__main__":
    asyncio.run(main())