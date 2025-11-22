# Telegram Admin Bot

Un bot administrador para gestionar canales VIP y gratuitos en Telegram.

## Características

### Gestión de Canales
- Registro de canales gratuito y VIP
- Detección automática de ID de canal al reenviar mensajes
- Panel de administración para gestionar canales
- Estado activo/inactivo para cada canal

### Canal Gratuito
- Acepta solicitudes de ingreso automáticamente
- Tiempo de delay configurable desde el panel de administración
- Registro de todas las solicitudes en base de datos

### Canal VIP
- Generación de tokens únicos para acceso VIP
- Validación automática de tokens
- Suscripciones de 30 días
- Recordatorios automáticos 24 horas antes de la expiración
- Expulsión automática de usuarios con suscripción vencida

## Configuración

1. Instalar dependencias:
```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

2. Configurar variables de entorno en `.env`:
```
BOT_TOKEN=tu_token_de_bot
ADMIN_ID=tu_id_de_telegram
DATABASE_PATH=./database.sqlite
```

3. Ejecutar el bot:
```bash
. venv/bin/activate
python main.py
```

## Uso

### Para Administradores
1. Inicia el bot con `/start`
2. Usa el panel de administración con navegación lineal:
   - **Configurar Sistema** - Delay del canal gratuito, configuración avanzada
   - **Gestionar Canales** - Agregar, ver, activar/desactivar canales
   - **Gestión VIP** - Generar tokens, ver usuarios VIP, estadísticas
   - **Estadísticas** - Reportes y métricas del sistema

**Navegación:** Todos los menús se muestran editando el mismo mensaje para mantener una pantalla de chat limpia.

### Para Configurar Canales
1. Ve a "Gestionar Canales" en el panel de administración
2. Selecciona "Agregar Canal Gratuito" o "Agregar Canal VIP"
3. Agrega el bot como administrador al canal
4. Reenvía un mensaje del canal al bot
5. El bot detectará automáticamente el ID y nombre del canal

### Para Usuarios VIP
1. Obtén un token VIP del administrador
2. Usa el enlace: `https://t.me/tu_bot?start=token_vip`
3. El bot te registrará automáticamente como VIP por 30 días

### Para Canal Gratuito
1. Los usuarios solicitan acceso al canal
2. El bot procesa automáticamente las solicitudes después del delay configurado

## Estructura del Proyecto

- `main.py` - Bot principal de Telegram
- `bot.py` - Lógica del negocio y manejo de base de datos
- `menu_factory.py` - Sistema de menús factory para navegación consistente
- `free_channel_handler.py` - Procesador de solicitudes del canal gratuito
- `database.sqlite` - Base de datos SQLite (se crea automáticamente)

## Base de Datos

El bot utiliza SQLite con las siguientes tablas:
- `config` - Configuración del bot
- `channels` - Canales registrados (gratuito y VIP)
- `vip_tokens` - Tokens VIP generados
- `vip_users` - Usuarios VIP registrados
- `free_channel_requests` - Solicitudes del canal gratuito
