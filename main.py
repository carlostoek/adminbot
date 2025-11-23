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
        if not self.token:
            raise ValueError("BOT_TOKEN environment variable is required")
        self.app = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        
        if context.args and len(context.args) > 0:
            token = context.args[0]
            await self.handle_vip_token(user_id, update.effective_user.username, token, update, context)
        else:
            if user_id == self.admin_bot.admin_id:
                title, reply_markup = MenuFactory.admin_panel()
                if update.message:
                    await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja todas las entradas de texto basadas en el estado actual"""
        if context.user_data is None:
            return
        
        if not update.message or not update.message.text:
            return
        
        user_input = update.message.text.strip()
        
        # Verificar estado de creación de tarifa
        if context.user_data.get('awaiting_rate_cost'):
            await self.handle_rate_cost(update, context)
        elif context.user_data.get('awaiting_rate_name'):
            await self.handle_rate_name(update, context)
        elif context.user_data.get('awaiting_rate_name_edit'):
            await self.handle_rate_name_edit(update, context)
        elif context.user_data.get('awaiting_rate_cost_edit'):
            await self.handle_rate_cost_edit(update, context)

    async def handle_vip_token(self, user_id: int, username: str | None, token: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.admin_bot.validate_vip_token(token):
            self.admin_bot.register_vip_user(user_id, username or f"ID: {user_id}", token)
            
            if update.message:
                await update.message.reply_text(
                    "¡Felicidades! Has sido registrado como usuario VIP.\n"
                    "Tu suscripción es válida por 30 días.\n\n"
                    "Recibirás un recordatorio un día antes de que expire tu suscripción."
                )
        else:
            if update.message:
                await update.message.reply_text("Token inválido o ya utilizado.")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not update.effective_user or update.effective_user.id != self.admin_bot.admin_id:
            await query.edit_message_text("No tienes permisos de administrador.")
            return
        
        title, reply_markup = MenuFactory.admin_panel()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def config_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        current_delay = self.admin_bot.get_free_channel_delay()
        title, reply_markup = MenuFactory.config_delay()
        
        # Personalizar el título con el delay actual
        title = title.replace("Selecciona el tiempo de espera:", f"Delay actual: {current_delay} segundos\n\nSelecciona el tiempo de espera:")
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def set_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return
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
        if not query:
            return
        await query.answer()
        
        # Obtener tarifas disponibles
        rates = self.admin_bot.get_vip_rates()
        
        if not rates:
            title, reply_markup = MenuFactory.create_simple_message(
                "🎫 Generar Token VIP",
                "❌ No hay tarifas configuradas.\n\n"
                "Para generar tokens VIP, primero debes crear tarifas en el menú de gestión de tarifas.",
                "vip_management"
            )
        else:
            title = "<b>🎫 Generar Token VIP</b>\n\n"
            title += "Selecciona la tarifa para el token:\n\n"
            
            # Mostrar información de tarifas disponibles
            for rate_id, name, days, cost, is_active in rates:
                if is_active:
                    title += f"• <b>{name}</b> - {days} días - ${cost:.2f}\n"
            
            title += "\nSelecciona una tarifa:"
            
            # Crear botones para cada tarifa activa
            keyboard = []
            for rate_id, name, days, cost, is_active in rates:
                if is_active:
                    button_text = f"🎫 {name} - {days}d - ${cost:.2f}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"generate_token_rate_{rate_id}")])
            
            keyboard.append([InlineKeyboardButton("← Volver", callback_data="vip_management")])
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def generate_token_for_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Genera un token VIP para una tarifa específica"""
        query = update.callback_query
        if not query or not query.data:
            return
        await query.answer()
        
        # Extraer el ID de la tarifa
        rate_id = int(query.data.replace('generate_token_rate_', ''))
        
        # Obtener información de la tarifa
        rate = self.admin_bot.get_vip_rate(rate_id)
        if not rate:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa seleccionada no existe.",
                "generate_vip_token"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        rate_id, name, days, cost, is_active = rate
        
        if not is_active:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa seleccionada no está activa.",
                "generate_vip_token"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # Generar token con la duración de la tarifa
        token = self.admin_bot.generate_vip_token(duration_days=days)
        
        # Crear enlace de invitación
        if self.app and self.app.bot:
            bot_username = (await self.app.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start={token}"
        else:
            invite_link = f"Token: {token}"
        
        # Formato mejorado para el token
        title = "🎫 <b>Token VIP Generado</b>\n\n"
        title += f"📋 <b>Tarifa:</b> {name}\n"
        title += f"⏱️ <b>Duración:</b> {days} días\n"
        title += f"💰 <b>Costo:</b> ${cost:.2f}\n\n"
        title += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        title += f"🔑 <b>Token:</b>\n<code>{token}</code>\n\n"
        title += f"🔗 <b>Enlace de invitación:</b>\n<code>{invite_link}</code>\n\n"
        title += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        title += "📝 <b>Instrucciones:</b>\n"
        title += "• Comparte el enlace con el usuario VIP\n"
        title += f"• El token es válido por {days} días\n"
        title += "• Se activa al primer uso\n\n"
        title += "⚠️ <i>Guarda este token en un lugar seguro</i>"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Generar Otro Token", callback_data="generate_vip_token")],
            [InlineKeyboardButton("← Volver al Menú VIP", callback_data="vip_management")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def view_vip_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
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
        if not query:
            return
        await query.answer()
        
        if not update.effective_user or update.effective_user.id != self.admin_bot.admin_id:
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
        if not query:
            return
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
        if context.user_data is not None:
            context.user_data['awaiting_channel'] = 'free'

    async def add_vip_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
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
        if context.user_data is not None:
            context.user_data['awaiting_channel'] = 'vip'

    async def view_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
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
        if not update.effective_user or update.effective_user.id != self.admin_bot.admin_id:
            return
        
        if context.user_data is None or 'awaiting_channel' not in context.user_data:
            return
        
        channel_type = context.user_data['awaiting_channel']
        
        if update.message and update.message.forward_from_chat:
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
            
            if update.message:
                await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')
            if context.user_data is not None:
                del context.user_data['awaiting_channel']
        else:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "No se pudo detectar el canal. Asegúrate de reenviar un mensaje del canal, no de un usuario.",
                "manage_channels"
            )
            if update.message:
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
        if not query:
            return
        await query.answer()
        
        title, reply_markup = MenuFactory.system_config()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def vip_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        title, reply_markup = MenuFactory.vip_management()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        title, reply_markup = MenuFactory.statistics()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    # Funciones para gestión de tarifas VIP
    async def manage_rates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        title, reply_markup = MenuFactory.manage_rates()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def select_rate_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        title, reply_markup = MenuFactory.select_rate_duration()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_rate_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return
        await query.answer()
        
        duration_days = int(query.data.replace('rate_duration_', ''))
        if context.user_data is not None:
            context.user_data['rate_duration'] = duration_days
        
        title, reply_markup = MenuFactory.create_simple_message(
            "💰 Crear Tarifa - Paso 2",
            f"Duración seleccionada: {duration_days} días\n\n"
            "Ahora ingresa el costo de la tarifa:\n"
            "<i>Envía un mensaje con el precio (ejemplo: 10.50)</i>",
            "select_rate_duration"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
        if context.user_data is not None:
            context.user_data['awaiting_rate_cost'] = True

    async def handle_rate_cost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data is None or not context.user_data.get('awaiting_rate_cost'):
            return
        
        if not update.message or not update.message.text:
            return
        
        try:
            cost = float(update.message.text)
            if cost <= 0:
                raise ValueError("El costo debe ser mayor a 0")
            
            context.user_data['rate_cost'] = cost
            
            # Generar nombre automático basado en duración
            duration = context.user_data['rate_duration']
            if duration == 1:
                name = "1 Día"
            elif duration == 7:
                name = "1 Semana"
            elif duration == 14:
                name = "2 Semanas"
            elif duration == 30:
                name = "1 Mes"
            else:
                name = f"{duration} Días"
            
            context.user_data['rate_name'] = name
            
            title, reply_markup = MenuFactory.create_simple_message(
                "💰 Crear Tarifa - Paso 3",
                f"<b>Resumen de la tarifa:</b>\n"
                f"• Nombre: {name}\n"
                f"• Duración: {duration} días\n"
                f"• Costo: ${cost:.2f}\n\n"
                "¿Deseas cambiar el nombre de la tarifa?\n"
                "<i>Envía un mensaje con el nuevo nombre o escribe 'no' para usar el nombre automático</i>",
                "select_rate_duration"
            )
            
            await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')
            
            # Limpiar estado anterior y activar nuevo estado
            context.user_data['awaiting_rate_name'] = True
            context.user_data['awaiting_rate_cost'] = False
            
        except ValueError:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "Por favor ingresa un precio válido (ejemplo: 10.50)",
                "select_rate_duration"
            )
            await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_rate_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data is None or not context.user_data.get('awaiting_rate_name'):
            return
        
        if not update.message or not update.message.text:
            return
        
        user_input = update.message.text.strip()
        
        if user_input.lower() != 'no':
            context.user_data['rate_name'] = user_input
        
        # Crear la tarifa
        name = context.user_data['rate_name']
        duration = context.user_data['rate_duration']
        cost = context.user_data['rate_cost']
        
        self.admin_bot.add_vip_rate(name, duration, cost)
        
        # Limpiar datos temporales
        for key in ['rate_duration', 'rate_cost', 'rate_name', 'awaiting_rate_cost', 'awaiting_rate_name']:
            context.user_data.pop(key, None)
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✅ Tarifa Creada",
            f"<b>Tarifa VIP creada exitosamente:</b>\n"
            f"• Nombre: {name}\n"
            f"• Duración: {duration} días\n"
            f"• Costo: ${cost:.2f}\n\n"
            "La tarifa está ahora disponible en el sistema.",
            "manage_rates"
        )
        
        await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def view_rates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        rates = self.admin_bot.get_vip_rates()
        
        # Pasar la lista de tarifas directamente para que se muestren como botones inline
        title, reply_markup = MenuFactory.view_rates_list(rates)
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('edit_rate_', ''))
        rate = self.admin_bot.get_vip_rate(rate_id)
        
        if not rate:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa no existe.",
                "view_rates"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        rate_id, name, days, cost, is_active = rate
        status = "Activa" if is_active else "Inactiva"
        
        title = f"<b>Editar Tarifa: {name}</b>\n\n"
        title += f"• Duración: {days} días\n"
        title += f"• Costo: ${cost:.2f}\n"
        title += f"• Estado: {status}\n\n"
        title += "Selecciona una acción:"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Cambiar Nombre", callback_data=f"change_rate_name_{rate_id}")],
            [InlineKeyboardButton("⏱️ Cambiar Duración", callback_data=f"change_rate_duration_{rate_id}")],
            [InlineKeyboardButton("💰 Cambiar Costo", callback_data=f"change_rate_cost_{rate_id}")],
            [InlineKeyboardButton("🔄 Cambiar Estado", callback_data=f"toggle_rate_status_{rate_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Tarifa", callback_data=f"delete_rate_{rate_id}")],
            [InlineKeyboardButton("← Volver", callback_data="view_rates")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def toggle_rate_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('toggle_rate_status_', ''))
        rate = self.admin_bot.get_vip_rate(rate_id)
        
        if not rate:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa no existe.",
                "view_rates"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        rate_id, name, days, cost, is_active = rate
        new_status = not is_active
        
        self.admin_bot.toggle_vip_rate_status(rate_id, new_status)
        
        status_text = "activada" if new_status else "desactivada"
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✅ Estado Actualizado",
            f"La tarifa <b>{name}</b> ha sido {status_text}.",
            "view_rates"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('delete_rate_', ''))
        rate = self.admin_bot.get_vip_rate(rate_id)
        
        if not rate:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa no existe.",
                "view_rates"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        rate_id, name, days, cost, is_active = rate
        
        title, reply_markup = MenuFactory.create_confirmation(
            "🗑️ Eliminar Tarifa",
            f"¿Estás seguro de que deseas eliminar la tarifa <b>{name}</b>?\n"
            f"• Duración: {days} días\n"
            f"• Costo: ${cost:.2f}\n\n"
            "<b>Esta acción no se puede deshacer.</b>",
            f"confirm_delete_rate_{rate_id}",
            f"edit_rate_{rate_id}"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def confirm_delete_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('confirm_delete_rate_', ''))
        rate = self.admin_bot.get_vip_rate(rate_id)
        
        if not rate:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "La tarifa no existe.",
                "view_rates"
            )
            await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        rate_id, name, days, cost, is_active = rate
        
        self.admin_bot.delete_vip_rate(rate_id)
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✅ Tarifa Eliminada",
            f"La tarifa <b>{name}</b> ha sido eliminada del sistema.",
            "view_rates"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def change_rate_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('change_rate_name_', ''))
        
        if context.user_data is not None:
            context.user_data['editing_rate_id'] = rate_id
            context.user_data['awaiting_rate_name_edit'] = True
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✏️ Cambiar Nombre",
            "Envía el nuevo nombre para la tarifa:",
            f"edit_rate_{rate_id}"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def change_rate_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('change_rate_duration_', ''))
        
        if context.user_data is not None:
            context.user_data['editing_rate_id'] = rate_id
        
        title, reply_markup = MenuFactory.select_rate_duration()
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def change_rate_cost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        
        if not query.data:
            return
        rate_id = int(query.data.replace('change_rate_cost_', ''))
        
        if context.user_data is not None:
            context.user_data['editing_rate_id'] = rate_id
            context.user_data['awaiting_rate_cost_edit'] = True
        
        title, reply_markup = MenuFactory.create_simple_message(
            "💰 Cambiar Costo",
            "Envía el nuevo costo para la tarifa (ejemplo: 10.50):",
            f"edit_rate_{rate_id}"
        )
        
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_rate_name_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data is None or not context.user_data.get('awaiting_rate_name_edit'):
            return
        
        if not update.message or not update.message.text:
            return
        
        rate_id = context.user_data['editing_rate_id']
        new_name = update.message.text.strip()
        
        self.admin_bot.update_vip_rate(rate_id, name=new_name)
        
        # Limpiar datos temporales
        for key in ['editing_rate_id', 'awaiting_rate_name_edit']:
            context.user_data.pop(key, None)
        
        title, reply_markup = MenuFactory.create_simple_message(
            "✅ Nombre Actualizado",
            f"El nombre de la tarifa ha sido cambiado a: <b>{new_name}</b>",
            f"edit_rate_{rate_id}"
        )
        
        await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_rate_cost_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data is None or not context.user_data.get('awaiting_rate_cost_edit'):
            return
        
        if not update.message or not update.message.text:
            return
        
        try:
            new_cost = float(update.message.text)
            if new_cost <= 0:
                raise ValueError("El costo debe ser mayor a 0")
            
            rate_id = context.user_data['editing_rate_id']
            self.admin_bot.update_vip_rate(rate_id, cost=new_cost)
            
            # Limpiar datos temporales
            for key in ['editing_rate_id', 'awaiting_rate_cost_edit']:
                context.user_data.pop(key, None)
            
            title, reply_markup = MenuFactory.create_simple_message(
                "✅ Costo Actualizado",
                f"El costo de la tarifa ha sido cambiado a: <b>${new_cost:.2f}</b>",
                f"edit_rate_{rate_id}"
            )
            
            await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')
            
        except ValueError:
            title, reply_markup = MenuFactory.create_simple_message(
                "❌ Error",
                "Por favor ingresa un precio válido (ejemplo: 10.50)",
                f"edit_rate_{context.user_data.get('editing_rate_id', 0)}" if context.user_data and 'editing_rate_id' in context.user_data else "view_rates"
            )
            if update.message:
                await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')

    def run(self):
        if not self.token:
            raise ValueError("Bot token is not available")
        self.app = Application.builder().token(self.token).build()
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.admin_panel, pattern="^admin_panel$"))
        self.app.add_handler(CallbackQueryHandler(self.config_delay, pattern="^config_delay$"))
        self.app.add_handler(CallbackQueryHandler(self.set_delay, pattern="^set_delay_"))
        self.app.add_handler(CallbackQueryHandler(self.generate_vip_token, pattern="^generate_vip_token$"))
        self.app.add_handler(CallbackQueryHandler(self.generate_token_for_rate, pattern="^generate_token_rate_"))
        self.app.add_handler(CallbackQueryHandler(self.view_vip_users, pattern="^view_vip_users$"))
        self.app.add_handler(CallbackQueryHandler(self.manage_channels, pattern="^manage_channels$"))
        self.app.add_handler(CallbackQueryHandler(self.add_free_channel, pattern="^add_free_channel$"))
        self.app.add_handler(CallbackQueryHandler(self.add_vip_channel, pattern="^add_vip_channel$"))
        self.app.add_handler(CallbackQueryHandler(self.view_channels, pattern="^view_channels$"))
        
        # Nuevos handlers para menús factory
        self.app.add_handler(CallbackQueryHandler(self.system_config, pattern="^system_config$"))
        self.app.add_handler(CallbackQueryHandler(self.vip_management, pattern="^vip_management$"))
        self.app.add_handler(CallbackQueryHandler(self.statistics, pattern="^statistics$"))
        
        # Handlers para gestión de tarifas VIP
        self.app.add_handler(CallbackQueryHandler(self.manage_rates, pattern="^manage_rates$"))
        self.app.add_handler(CallbackQueryHandler(self.select_rate_duration, pattern="^select_rate_duration$"))
        self.app.add_handler(CallbackQueryHandler(self.handle_rate_duration, pattern="^rate_duration_"))
        self.app.add_handler(CallbackQueryHandler(self.view_rates, pattern="^view_rates$"))
        self.app.add_handler(CallbackQueryHandler(self.edit_rate, pattern="^edit_rate_"))
        self.app.add_handler(CallbackQueryHandler(self.toggle_rate_status, pattern="^toggle_rate_status_"))
        self.app.add_handler(CallbackQueryHandler(self.delete_rate, pattern="^delete_rate_"))
        self.app.add_handler(CallbackQueryHandler(self.confirm_delete_rate, pattern="^confirm_delete_rate_"))
        self.app.add_handler(CallbackQueryHandler(self.change_rate_name, pattern="^change_rate_name_"))
        self.app.add_handler(CallbackQueryHandler(self.change_rate_duration, pattern="^change_rate_duration_"))
        self.app.add_handler(CallbackQueryHandler(self.change_rate_cost, pattern="^change_rate_cost_"))
        
        self.app.add_handler(MessageHandler(filters.FORWARDED, self.handle_forwarded_message))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input))
        
        job_queue = self.app.job_queue
        if job_queue:
            job_queue.run_repeating(self.check_subscriptions, interval=3600, first=10)
        
        print("Bot iniciado...")
        self.app.run_polling()

if __name__ == "__main__":
    telegram_bot = TelegramBot()
    telegram_bot.run()