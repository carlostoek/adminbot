import os
import sqlite3
import asyncio
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class AdminBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        admin_id_str = os.getenv('ADMIN_ID')
        self.admin_id = int(admin_id_str) if admin_id_str else 0
        self.database_path = os.getenv('DATABASE_PATH', './database.sqlite')
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_tokens (
                token TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used BOOLEAN DEFAULT FALSE,
                duration_days INTEGER DEFAULT 30
            )
        ''')
        
        # Add duration_days column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(vip_tokens)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'duration_days' not in columns:
            cursor.execute('ALTER TABLE vip_tokens ADD COLUMN duration_days INTEGER DEFAULT 30')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_end TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS free_channel_requests (
                user_id INTEGER,
                username TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, requested_at)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY,
                channel_name TEXT,
                channel_type TEXT CHECK(channel_type IN ('free', 'vip')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                days INTEGER NOT NULL,
                cost REAL NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO config (key, value) VALUES ('free_channel_delay', '60')
        ''')
        
        conn.commit()
        conn.close()

    def get_free_channel_delay(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM config WHERE key = "free_channel_delay"')
        result = cursor.fetchone()
        conn.close()
        return int(result[0]) if result else 60

    def set_free_channel_delay(self, delay_seconds):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE config SET value = ? WHERE key = "free_channel_delay"', (str(delay_seconds),))
        conn.commit()
        conn.close()

    def generate_vip_token(self, duration_days=30):
        token = str(uuid.uuid4())
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO vip_tokens (token, duration_days) VALUES (?, ?)', (token, duration_days))
        conn.commit()
        conn.close()
        return token



    def validate_vip_token(self, token):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vip_tokens WHERE token = ? AND used = FALSE', (token,))
        token_data = cursor.fetchone()
        conn.close()
        return token_data is not None

    def register_vip_user(self, user_id, username, token):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Obtener la duración del token
        cursor.execute('SELECT duration_days FROM vip_tokens WHERE token = ?', (token,))
        token_data = cursor.fetchone()
        duration_days = token_data[0] or 30  # Usar 30 días como valor por defecto
        
        subscription_end = datetime.now() + timedelta(days=duration_days)
        cursor.execute('''
            INSERT OR REPLACE INTO vip_users (user_id, username, subscription_end, status)
            VALUES (?, ?, ?, 'active')
        ''', (user_id, username, subscription_end))
        
        cursor.execute('UPDATE vip_tokens SET used = TRUE WHERE token = ?', (token,))
        conn.commit()
        conn.close()

    def get_vip_users(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, subscription_end, status FROM vip_users ORDER BY subscription_end')
        users = cursor.fetchall()
        conn.close()
        return users

    def get_expiring_vip_users(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        cursor.execute('''
            SELECT user_id, username, subscription_end 
            FROM vip_users 
            WHERE status = 'active' AND subscription_end BETWEEN ? AND ?
        ''', (now, tomorrow))
        
        users = cursor.fetchall()
        conn.close()
        return users

    def expire_old_subscriptions(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute('''
            UPDATE vip_users 
            SET status = 'expired' 
            WHERE status = 'active' AND subscription_end < ?
        ''', (now,))
        
        conn.commit()
        conn.close()

    def add_free_channel_request(self, user_id, username):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO free_channel_requests (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        conn.commit()
        conn.close()

    def get_pending_free_requests(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, requested_at 
            FROM free_channel_requests 
            WHERE processed = FALSE
        ''')
        requests = cursor.fetchall()
        conn.close()
        return requests

    def mark_request_processed(self, user_id, requested_at):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE free_channel_requests 
            SET processed = TRUE 
            WHERE user_id = ? AND requested_at = ?
        ''', (user_id, requested_at))
        conn.commit()
        conn.close()

    # Funciones para manejo de canales
    def add_channel(self, channel_id, channel_name, channel_type):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO channels (channel_id, channel_name, channel_type)
            VALUES (?, ?, ?)
        ''', (channel_id, channel_name, channel_type))
        conn.commit()
        conn.close()

    def get_channel(self, channel_type):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT channel_id, channel_name 
            FROM channels 
            WHERE channel_type = ? AND is_active = TRUE
        ''', (channel_type,))
        channel = cursor.fetchone()
        conn.close()
        return channel

    def get_all_channels(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT channel_id, channel_name, channel_type, is_active
            FROM channels
            ORDER BY channel_type
        ''')
        channels = cursor.fetchall()
        conn.close()
        return channels

    def delete_channel(self, channel_id):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        conn.commit()
        conn.close()

    def toggle_channel_status(self, channel_id, is_active):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE channels 
            SET is_active = ? 
            WHERE channel_id = ?
        ''', (is_active, channel_id))
        conn.commit()
        conn.close()

    # Funciones para manejo de tarifas VIP
    def add_vip_rate(self, name, days, cost):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO vip_rates (name, days, cost)
            VALUES (?, ?, ?)
        ''', (name, days, cost))
        conn.commit()
        conn.close()

    def get_vip_rates(self):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, days, cost, is_active
            FROM vip_rates
            ORDER BY days
        ''')
        rates = cursor.fetchall()
        conn.close()
        return rates

    def get_vip_rate(self, rate_id):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, days, cost, is_active FROM vip_rates WHERE id = ?', (rate_id,))
        rate = cursor.fetchone()
        conn.close()
        return rate

    def update_vip_rate(self, rate_id, name=None, days=None, cost=None):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Get current rate data
        current_rate = self.get_vip_rate(rate_id)
        if not current_rate:
            return False
        
        current_name, current_days, current_cost = current_rate[1], current_rate[2], current_rate[3]
        
        # Use provided values or keep current ones
        update_name = name if name is not None else current_name
        update_days = days if days is not None else current_days
        update_cost = cost if cost is not None else current_cost
        
        cursor.execute('''
            UPDATE vip_rates 
            SET name = ?, days = ?, cost = ?
            WHERE id = ?
        ''', (update_name, update_days, update_cost, rate_id))
        conn.commit()
        conn.close()
        return True

    def delete_vip_rate(self, rate_id):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vip_rates WHERE id = ?', (rate_id,))
        conn.commit()
        conn.close()

    def toggle_vip_rate_status(self, rate_id, is_active):
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE vip_rates 
            SET is_active = ? 
            WHERE id = ?
        ''', (is_active, rate_id))
        conn.commit()
        conn.close()

    # Funciones para envío de mensajes a canales
    async def send_message_to_channel(self, channel_type, message_text, file_path=None, file_id=None, file_type=None, disable_downloads=False, context=None):
        """
        Envía un mensaje al canal especificado.
        
        Args:
            channel_type (str): 'vip' o 'free'
            message_text (str): Texto del mensaje
            file_path (str, optional): Ruta al archivo adjunto (legacy)
            file_id (str, optional): ID del archivo en Telegram
            file_type (str, optional): Tipo de archivo ('photo', 'video', 'document')
            disable_downloads (bool): Si deshabilitar descargas
            context: Contexto de Telegram para enviar el mensaje
        
        Returns:
            bool: True si se envió correctamente, False en caso de error
        """
        if not context or not context.bot:
            return False
        
        channel = self.get_channel(channel_type)
        if not channel:
            return False
        
        channel_id, channel_name = channel
        
        try:
            if file_id and file_type:
                # Enviar mensaje con archivo adjunto usando file_id
                kwargs = {
                    "chat_id": channel_id,
                    "caption": message_text,
                    "parse_mode": 'HTML',
                    "protect_content": disable_downloads
                }
                
                if file_type == 'photo':
                    await context.bot.send_photo(photo=file_id, **kwargs)
                elif file_type == 'video':
                    await context.bot.send_video(video=file_id, **kwargs)
                elif file_type == 'document':
                    await context.bot.send_document(document=file_id, **kwargs)
                else:
                    # Fallback para tipos desconocidos
                    await context.bot.send_document(document=file_id, **kwargs)
            else:
                # Enviar solo texto
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=message_text,
                    parse_mode='HTML',
                    protect_content=disable_downloads
                )
            
            return True
            
        except Exception as e:
            print(f"Error enviando mensaje al canal {channel_type}: {e}")
            return False

    def save_message_draft(self, channel_type, message_text, file_path=None, file_id=None, file_type=None, disable_downloads=False):
        """
        Guarda un borrador de mensaje en la base de datos.
        
        Args:
            channel_type (str): 'vip' o 'free'
            message_text (str): Texto del mensaje
            file_path (str, optional): Ruta al archivo adjunto (legacy)
            file_id (str, optional): ID del archivo en Telegram
            file_type (str, optional): Tipo de archivo ('photo', 'video', 'document')
            disable_downloads (bool): Si deshabilitar descargas
        
        Returns:
            int: ID del borrador guardado
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_type TEXT NOT NULL,
                message_text TEXT NOT NULL,
                file_path TEXT,
                file_id TEXT,
                file_type TEXT,
                disable_downloads BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT INTO message_drafts (channel_type, message_text, file_path, file_id, file_type, disable_downloads)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (channel_type, message_text, file_path, file_id, file_type, disable_downloads))
        
        draft_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return draft_id

    def get_message_draft(self, draft_id):
        """
        Obtiene un borrador de mensaje por ID.
        
        Args:
            draft_id (int): ID del borrador
        
        Returns:
            tuple: Datos del borrador o None si no existe
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, channel_type, message_text, file_path, file_id, file_type, disable_downloads, created_at
            FROM message_drafts
            WHERE id = ?
        ''', (draft_id,))
        
        draft = cursor.fetchone()
        conn.close()
        
        return draft

    def delete_message_draft(self, draft_id):
        """
        Elimina un borrador de mensaje.
        
        Args:
            draft_id (int): ID del borrador
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM message_drafts WHERE id = ?', (draft_id,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    bot = AdminBot()
    print("Database initialized successfully!")