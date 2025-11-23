from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class MenuFactory:
    """
    Factory para crear menús consistentes con navegación lineal.
    Todos los menús se muestran editando el mismo mensaje para mantener
    una pantalla de chat limpia.
    """
    
    @staticmethod
    def create_menu(title, options, back_callback=None):
        """
        Crea un menú con título y opciones.
        
        Args:
            title (str): Título del menú
            options (list): Lista de opciones [(texto, callback_data), ...]
            back_callback (str): Callback para botón de volver
        
        Returns:
            tuple: (texto, reply_markup)
        """
        keyboard = []
        
        # Agregar opciones principales
        for option_text, callback_data in options:
            keyboard.append([InlineKeyboardButton(option_text, callback_data=callback_data)])
        
        # Agregar botón de volver si se especifica
        if back_callback:
            keyboard.append([InlineKeyboardButton("← Volver", callback_data=back_callback)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return title, reply_markup
    
    @staticmethod
    def admin_panel():
        """Menú principal del administrador"""
        title = "<b>Panel de Administración</b>\n\nSelecciona una opción:"
        
        options = [
            ("⚙️ Configurar Sistema", "system_config"),
            ("📊 Gestionar Canales", "manage_channels"),
            ("👑 Gestión VIP", "vip_management"),
            ("📈 Estadísticas", "statistics")
        ]
        
        return MenuFactory.create_menu(title, options)
    
    @staticmethod
    def system_config():
        """Menú de configuración del sistema"""
        title = "<b>Configuración del Sistema</b>\n\nSelecciona una opción:"
        
        options = [
            ("⏱️ Configurar Delay Canal Gratuito", "config_delay"),
            ("🔧 Configuración Avanzada", "advanced_config")
        ]
        
        return MenuFactory.create_menu(title, options, "admin_panel")
    
    @staticmethod
    def config_delay():
        """Menú para configurar delay del canal gratuito"""
        title = "<b>Configurar Delay del Canal Gratuito</b>\n\nSelecciona el tiempo de espera:"
        
        options = [
            ("30 segundos", "set_delay_30"),
            ("1 minuto", "set_delay_60"),
            ("5 minutos", "set_delay_300"),
            ("10 minutos", "set_delay_600")
        ]
        
        return MenuFactory.create_menu(title, options, "system_config")
    
    @staticmethod
    def manage_channels():
        """Menú de gestión de canales"""
        title = "<b>Gestión de Canales</b>\n\nSelecciona una opción:"
        
        options = [
            ("➕ Agregar Canal Gratuito", "add_free_channel"),
            ("➕ Agregar Canal VIP", "add_vip_channel"),
            ("📋 Ver Canales Configurados", "view_channels"),
            ("🔄 Gestionar Estado Canales", "toggle_channels")
        ]
        
        return MenuFactory.create_menu(title, options, "admin_panel")
    
    @staticmethod
    def vip_management():
        """Menú de gestión VIP"""
        title = "<b>Gestión VIP</b>\n\nSelecciona una opción:"
        
        options = [
            ("💰 Gestionar Tarifas", "manage_rates"),
            ("🎫 Generar Token VIP", "generate_vip_token"),
            ("👥 Ver Usuarios VIP", "view_vip_users"),
            ("📊 Estadísticas VIP", "vip_statistics")
        ]
        
        return MenuFactory.create_menu(title, options, "admin_panel")
    
    @staticmethod
    def manage_rates():
        """Menú de gestión de tarifas VIP"""
        title = "<b>Gestión de Tarifas VIP</b>\n\nSelecciona una opción:"
        
        options = [
            ("➕ Crear Nueva Tarifa", "select_rate_duration"),
            ("📋 Ver Tarifas Configuradas", "view_rates")
        ]
        
        return MenuFactory.create_menu(title, options, "vip_management")
    
    @staticmethod
    def select_rate_duration():
        """Menú para seleccionar duración de tarifa"""
        title = "<b>Crear Tarifa - Paso 1</b>\n\nSelecciona la duración de la suscripción:"
        
        options = [
            ("1 día", "rate_duration_1"),
            ("1 semana (7 días)", "rate_duration_7"),
            ("2 semanas (14 días)", "rate_duration_14"),
            ("1 mes (30 días)", "rate_duration_30")
        ]
        
        return MenuFactory.create_menu(title, options, "manage_rates")
    
    @staticmethod
    def view_rates_list(rates=None):
        """Menú para listar tarifas con botones inline"""
        if not rates:
            title = "<b>Tarifas VIP Configuradas</b>\n\nNo hay tarifas configuradas.\n\nSelecciona una opción:"
            options = [
                ("➕ Crear Nueva Tarifa", "select_rate_duration")
            ]
        else:
            title = "<b>Tarifas VIP Configuradas</b>\n\nSelecciona una tarifa para gestionarla:"
            options = []
            
            # Agregar botones para cada tarifa
            for rate_id, name, days, cost, is_active in rates:
                status = "🟢" if is_active else "🔴"
                button_text = f"{status} {name} - {days}d - ${cost:.2f}"
                options.append((button_text, f"edit_rate_{rate_id}"))
            
            # Agregar botón para crear nueva tarifa
            options.append(("➕ Crear Nueva Tarifa", "select_rate_duration"))
        
        return MenuFactory.create_menu(title, options, "manage_rates")
    
    @staticmethod
    def statistics():
        """Menú de estadísticas"""
        title = "<b>Estadísticas del Sistema</b>\n\nSelecciona una opción:"
        
        options = [
            ("📊 Estadísticas Generales", "general_stats"),
            ("📈 Reportes de Actividad", "activity_reports")
        ]
        
        return MenuFactory.create_menu(title, options, "admin_panel")
    
    @staticmethod
    def create_simple_message(title, message, back_callback=None):
        """
        Crea un mensaje simple con botón de volver.
        
        Args:
            title (str): Título del mensaje
            message (str): Contenido del mensaje
            back_callback (str): Callback para botón de volver
        
        Returns:
            tuple: (texto, reply_markup)
        """
        full_text = f"<b>{title}</b>\n\n{message}"
        
        if back_callback:
            keyboard = [[InlineKeyboardButton("← Volver", callback_data=back_callback)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None
        
        return full_text, reply_markup
    
    @staticmethod
    def create_confirmation(title, message, confirm_callback, cancel_callback):
        """
        Crea un menú de confirmación.
        
        Args:
            title (str): Título del mensaje
            message (str): Contenido del mensaje
            confirm_callback (str): Callback para confirmar
            cancel_callback (str): Callback para cancelar
        
        Returns:
            tuple: (texto, reply_markup)
        """
        full_text = f"<b>{title}</b>\n\n{message}"
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data=confirm_callback)],
            [InlineKeyboardButton("❌ Cancelar", callback_data=cancel_callback)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return full_text, reply_markup