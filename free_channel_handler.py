import asyncio
import time
from bot import AdminBot

class FreeChannelHandler:
    def __init__(self):
        self.admin_bot = AdminBot()
        self.running = False

    async def process_free_channel_requests(self):
        while self.running:
            delay = self.admin_bot.get_free_channel_delay()
            
            pending_requests = self.admin_bot.get_pending_free_requests()
            
            for user_id, username, requested_at in pending_requests:
                request_time = time.mktime(time.strptime(requested_at, '%Y-%m-%d %H:%M:%S'))
                current_time = time.time()
                
                if current_time - request_time >= delay:
                    print(f"Aprobando acceso para usuario {username} (ID: {user_id})")
                    self.admin_bot.mark_request_processed(user_id, requested_at)
                    
            await asyncio.sleep(10)

    def start(self):
        self.running = True
        asyncio.create_task(self.process_free_channel_requests())

    def stop(self):
        self.running = False

    def simulate_request(self, user_id, username):
        self.admin_bot.add_free_channel_request(user_id, username)
        print(f"Solicitud simulada para {username} (ID: {user_id})")

if __name__ == "__main__":
    handler = FreeChannelHandler()
    handler.start()
    
    print("Simulador de canal gratuito iniciado...")
    print("Comandos:")
    print("  add <user_id> <username> - Simular solicitud de usuario")
    print("  delay <seconds> - Cambiar delay actual")
    print("  status - Ver estado actual")
    print("  quit - Salir")
    
    try:
        while True:
            command = input("> ").strip().split()
            
            if not command:
                continue
                
            if command[0] == "add" and len(command) >= 3:
                user_id = int(command[1])
                username = command[2]
                handler.simulate_request(user_id, username)
                
            elif command[0] == "delay" and len(command) >= 2:
                delay_seconds = int(command[1])
                handler.admin_bot.set_free_channel_delay(delay_seconds)
                print(f"Delay cambiado a {delay_seconds} segundos")
                
            elif command[0] == "status":
                current_delay = handler.admin_bot.get_free_channel_delay()
                pending_requests = handler.admin_bot.get_pending_free_requests()
                print(f"Delay actual: {current_delay} segundos")
                print(f"Solicitudes pendientes: {len(pending_requests)}")
                
            elif command[0] == "quit":
                break
                
            else:
                print("Comando no reconocido")
                
    except KeyboardInterrupt:
        pass
    finally:
        handler.stop()
        print("Simulador detenido")