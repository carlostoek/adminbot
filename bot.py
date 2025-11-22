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
                used BOOLEAN DEFAULT FALSE
            )
        ''')
        
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

    def generate_vip_token(self):
        token = str(uuid.uuid4())
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO vip_tokens (token) VALUES (?)', (token,))
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
        
        subscription_end = datetime.now() + timedelta(days=30)
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

if __name__ == "__main__":
    bot = AdminBot()
    print("Database initialized successfully!")