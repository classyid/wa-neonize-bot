import asyncio
import logging
import os
import signal
import sys
from neonize.aioze.client import NewAClient
from neonize.events import (
    ConnectedEv,
    MessageEv,
    PairStatusEv,
    event,
)
from neonize.utils import log
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

# Mengatur level logging
log.setLevel(logging.INFO)

# Event untuk sinyal penghentian program
stop_event = asyncio.Event()

# Membuat client instance
client = NewAClient("wa_session.sqlite3")

@client.event(ConnectedEv)
async def on_connected(_: NewAClient, __: ConnectedEv):
    """Handler untuk event saat client terhubung"""
    log.info("⚡ Client terhubung ke WhatsApp")
    log.info("Bot siap menerima pesan. Kirim 'ping' untuk mencoba.")

@client.event(PairStatusEv)
async def on_pair_status(_: NewAClient, message: PairStatusEv):
    """Handler untuk event saat status pair berubah (login berhasil)"""
    try:
        user_id = message.ID.User if hasattr(message.ID, 'User') else "unknown"
        log.info(f"Berhasil login sebagai {user_id}")
    except Exception as e:
        log.error(f"Error saat mendapatkan user ID: {e}")

@client.event(MessageEv)
async def on_message(client: NewAClient, message: MessageEv):
    """Handler untuk event saat menerima pesan"""
    try:
        # Mendapatkan teks dari pesan
        text = ""
        if hasattr(message.Message, 'conversation') and message.Message.conversation:
            text = message.Message.conversation
        elif hasattr(message.Message, 'extendedTextMessage') and message.Message.extendedTextMessage.text:
            text = message.Message.extendedTextMessage.text
        else:
            # Bukan pesan teks, mungkin media atau jenis lain
            return
        
        # Mendapatkan info chat jika tersedia
        chat = None
        if hasattr(message.Info.MessageSource, 'Chat'):
            chat = message.Info.MessageSource.Chat
        else:
            log.error("Tidak bisa mendapatkan chat ID dari pesan")
            return
        
        # Mendapatkan info sender jika tersedia
        sender = ""
        if hasattr(message.Info.MessageSource, 'Sender'):
            sender = message.Info.MessageSource.Sender
        
        # Log pesan yang diterima
        log.info(f"Pesan dari {sender}: {text}")
        
        # Fitur commands
        if text.lower() == "ping":
            try:
                # Gunakan send_message langsung ke chat daripada reply_message
                await client.send_message(chat, Message(conversation="pong"))
                log.info("Berhasil mengirim 'pong'")
            except Exception as e:
                log.error(f"Error saat mengirim 'pong': {e}")
                import traceback
                log.error(traceback.format_exc())
        elif text.lower() == "stop" or text.lower() == "exit" or text.lower() == "quit":
            # Jika pesan adalah perintah untuk berhenti
            try:
                await client.send_message(chat, Message(conversation="Mematikan bot..."))
                log.info("Berhasil mengirim pesan 'Mematikan bot...'")
            except Exception as e:
                log.error(f"Error saat mengirim pesan shutdown: {e}")
            
            log.info("Menerima perintah stop dari pengguna")
            await stop_bot()
            
    except Exception as e:
        log.error(f"Error saat memproses pesan: {e}")
        import traceback
        log.error(traceback.format_exc())

async def stop_bot():
    """Fungsi untuk menghentikan bot dengan bersih"""
    log.info("Proses penghentian bot dimulai...")
    try:
        # Logout dari WhatsApp
        log.info("Melakukan logout dari WhatsApp...")
        await client.logout()
        log.info("Logout berhasil")
    except Exception as e:
        log.error(f"Error saat logout: {e}")
    
    # Set event untuk mengakhiri loop utama
    stop_event.set()

# Fungsi interupsi untuk menangani SIGINT (Ctrl+C)
def interrupted(*_):
    log.info("Menerima sinyal interupsi (Ctrl+C)")
    asyncio.create_task(stop_bot())

# Daftarkan handler SIGINT
signal.signal(signal.SIGINT, lambda s, f: asyncio.get_event_loop().create_task(stop_bot()))

async def main():
    """Fungsi utama"""
    log.info("Memulai client WhatsApp...")
    log.info("QR code akan muncul jika perlu login. Silakan scan...")
    log.info("Tekan Ctrl+C untuk berhenti atau kirim pesan 'stop' ke bot")
    
    try:
        # Connect dan tunggu hingga interrupsi
        connection_task = asyncio.create_task(client.connect())
        
        # Menunggu event penghentian
        await stop_event.wait()
        log.info("Event penghentian diterima, menutup program...")
        
    except Exception as e:
        log.error(f"Error saat menjalankan client: {e}")
    finally:
        log.info("Client berhenti")

if __name__ == "__main__":
    # Jalankan di loop asyncio
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log.info("Program dihentikan oleh pengguna")
    finally:
        log.info("Program selesai")
