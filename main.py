import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bot import AdminBot
from menu_factory import MenuFactory

class TelegramBot:
    def __init__(self):
        self.admin_bot = AdminBot()
        self.token = self.admin_bot.token
        self.app = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if context.args and len(context.args) > 0:
            token = context.args[0]
            await self.handle_vip_token(user_id, update.effective_user.username, token, update, context)
        else:
            if user_id == self.admin_bot.admin_id:
                title, reply_markup = MenuFactory.admin_panel()
                await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "¡Bienvenido!\n\n"
                    "Este bot gestiona el acceso a los canales.\n\n"
                    "Si tienes un token VIP, úsalo con /start <token>",
                )

    async def handle_vip_token(self, user_id: int, username: str, token: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.admin_bot.validate_vip_token(token):
            self.admin_bot.register_vip_user(user_id, username, token)
            
            await update.message.reply_text(
                "¡Felicidades! Has sido registrado como usuario VIP.\n"
                "Tu suscripción es válida por 30 días.\n\n"
                "Recibirás un recordatorio un día antes de que expire tu suscripción."
            )
        else:
            await update.message.reply_text("Token inválido o ya utilizado.")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if update.effective_user.id != self.admin_bot.admin_id:
            await query.edit_message_text("No tienes permisos de administrador.")
            return
        
        title, reply_markup = MenuFactory.admin_panel()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def config_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        current_delay = self.admin_bot.get_free_channel_delay()
        title, reply_markup = MenuFactory.config_delay()
        
        # Personalizar el título con el delay actual
        title = title.replace("Selecciona el tiempo de espera:", f"Delay actual: {current_delay} segundos\n\nSelecciona el tiempo de espera:")
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def set_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        delay_seconds = query.data.replace('set_delay_', '')
        self.admin_bot.set_free_channel_delay(delay_seconds)
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✅ Configuración Actualizada",
            f"El delay del canal gratuito ha sido configurado a {delay_seconds} segundos.",
            "system_config"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def generate_vip_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        token = self.admin_bot.generate_vip_token()
        
        bot_username = (await self.app.bot.get_me()).username
        invite_link = f"https://t.me/{bot_username}?start={token}"
        
        title, reply_markup = MenuFactory.create_simple_message(
            "🎫 Token VIP Generado",
            f"<b>Token:</b> <code>{token}</code>\n"
            f"<b>Enlace de invitación:</b> <code>{invite_link}</code>\n\n"
            f"Comparte este enlace con el usuario VIP.",
            "vip_management"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def view_vip_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        users = self.admin_bot.get_vip_users()
        
        if not users:
            title, reply_markup = MenuFactory.create_simple_message(
                "👥 Usuarios VIP",
                "No hay usuarios VIP registrados.",
                "vip_management"
            )
        else:
            message = ""
            for user in users:
                user_id, username, sub_end, status = user
                message += f"👤 {username or f'ID: {user_id}'}\n"
                message += f"   Estado: {status}\n"
                message += f"   Vence: {sub_end}\n\n"
            
            title, reply_markup = MenuFactory.create_simple_message(
                "👥 Usuarios VIP",
                message,
                "vip_management"
            )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def manage_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if update.effective_user.id != self.admin_bot.admin_id:
            await query.edit_message_text("No tienes permisos de administrador.")
            return
        
        channels = self.admin_bot.get_all_channels()
        title, reply_markup = MenuFactory.manage_channels()
        
        # Personalizar el título con información de canales
        if channels:
            channels_info = "\n<b>Canales Configurados:</b>\n"
            for channel_id, channel_name, channel_type, is_active in channels:
                status = "🟢 Activo" if is_active else "🔴 Inactivo"
                channels_info += f"• {channel_name} ({channel_type.upper()}) - {status}\n"
            title = title.replace("Selecciona una opción:", channels_info + "\nSelecciona una opción:")
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def add_free_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        title, reply_markup = MenuFactory.create_simple_message(
            "➕ Agregar Canal Gratuito",
            "Para configurar el canal gratuito:\n"
            "1. Agrega el bot como administrador al canal\n"
            "2. Reenvía un mensaje del canal al bot\n"
            "3. El bot detectará automáticamente el ID del canal\n\n"
            "<i>Reenvía ahora un mensaje del canal gratuito...</i>",
            "manage_channels"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
        context.user_data['awaiting_channel'] = 'free'

    async def add_vip_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        title, reply_markup = MenuFactory.create_simple_message(
            "➕ Agregar Canal VIP",
            "Para configurar el canal VIP:\n"
            "1. Agrega el bot como administrador al canal\n"
            "2. Reenvía un mensaje del canal al bot\n"
            "3. El bot detectará automáticamente el ID del canal\n\n"
            "<i>Reenvía ahora un mensaje del canal VIP...</i>",
            "manage_channels"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
        context.user_data['awaiting_channel'] = 'vip'

    async def view_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        channels = self.admin_bot.get_all_channels()
        
        if not channels:
            title, reply_markup = MenuFactory.create_simple_message(
                "📋 Canales Configurados",
                "No hay canales configurados.",
                "manage_channels"
            )
        else:
            message = ""
            for channel_id, channel_name, channel_type, is_active in channels:
                status = "🟢 Activo" if is_active else "🔴 Inactivo"
                message += f"<b>{channel_name}</b>\n"
                message += f"ID: <code>{channel_id}</code>\n"
                message += f"Tipo: {channel_type.upper()}\n"
                message += f"Estado: {status}\n\n"
            
            title, reply_markup = MenuFactory.create_simple_message(
                "📋 Canales Configurados",
                message,
                "manage_channels"
            )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_forwarded_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_bot.admin_id:
            return
        
        if 'awaiting_channel' not in context.user_data:
            return
        
        channel_type = context.user_data['awaiting_channel']
        
        if update.message.forward_from_chat:
            channel = update.message.forward_from_chat
            channel_id = channel.id
            channel_name = channel.title
            
            self.admin_bot.add_channel(channel_id, channel_name, channel_type)
            
            title, reply_markup = MenuFactory.create_simple_message(
                f"✅ Canal {channel_type.upper()} Configurado",
                f"<b>Nombre:</b> {channel_name}\n"
                f"<b>ID:</b> <code>{channel_id}</code>\n"
                f"<b>Tipo:</b> {channel_type}\n\n"
                f"El canal ha sido registrado en el sistema.",
                "manage_channels"
            )
            
            await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')
            del context.user_data['awaiting_channel']
        else:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "No se pudo detectar el canal. Asegúrate de reenviar un mensaje del canal, no de un usuario.",
                "manage_channels"
            )
            await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def check_subscriptions(self, context: ContextTypes.DEFAULT_TYPE):
        expiring_users = self.admin_bot.get_expiring_vip_users()
        
        for user_id, username, sub_end in expiring_users:
            try:
                await context.bot.send_message(
                    user_id,
                    f"¡Recordatorio! Tu suscripción VIP expira en menos de 24 horas.\n"
                    f"Fecha de expiración: {sub_end}\n\n"
                    f"Renueva tu suscripción para mantener el acceso al canal VIP."
                )
            except Exception as e:
                print(f"Error enviando recordatorio a {user_id}: {e}")
        
        self.admin_bot.expire_old_subscriptions()

    # Nuevas funciones para menús factory
    async def system_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        title, reply_markup = MenuFactory.system_config()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def vip_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        title, reply_markup = MenuFactory.vip_management()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        title, reply_markup = MenuFactory.statistics()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    def run(self):
        self.app = Application.builder().token(self.token).build()
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.admin_panel, pattern="^admin_panel$"))
        self.app.add_handler(CallbackQueryHandler(self.config_delay, pattern="^config_delay$"))
        self.app.add_handler(CallbackQueryHandler(self.set_delay, pattern="^set_delay_"))
        self.app.add_handler(CallbackQueryHandler(self.generate_vip_token, pattern="^generate_vip_token$"))
        self.app.add_handler(CallbackQueryHandler(self.view_vip_users, pattern="^view_vip_users$"))
        self.app.add_handler(CallbackQueryHandler(self.manage_channels, pattern="^manage_channels$"))
        self.app.add_handler(CallbackQueryHandler(self.add_free_channel, pattern="^add_free_channel$"))
        self.app.add_handler(CallbackQueryHandler(self.add_vip_channel, pattern="^add_vip_channel$"))
        self.app.add_handler(CallbackQueryHandler(self.view_channels, pattern="^view_channels$"))
        
        # Nuevos handlers para menús factory
        self.app.add_handler(CallbackQueryHandler(self.system_config, pattern="^system_config$"))
        self.app.add_handler(CallbackQueryHandler(self.vip_management, pattern="^vip_management$"))
        self.app.add_handler(CallbackQueryHandler(self.statistics, pattern="^statistics$"))
        
        self.app.add_handler(MessageHandler(filters.FORWARDED, self.handle_forwarded_message))
        
        job_queue = self.app.job_queue
        if job_queue:
            job_queue.run_repeating(self.check_subscriptions, interval=3600, first=10)
        
        print("Bot iniciado...")
        self.app.run_polling()

if __name__ == "__main__":
    telegram_bot = TelegramBot()
    telegram_bot.run()