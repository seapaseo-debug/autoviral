import os
import queue
import threading

import telebot

import autoviral as av

# token dibaca dari file lokal (JANGAN taruh token di GitHub!)
try:
    TOKEN = os.environ.get("BOT_TOKEN") or open("token.txt").read().strip()
except Exception:
    raise SystemExit("Buat dulu file token.txt berisi token BotFather.")

bot = telebot.TeleBot(TOKEN)

antrean = queue.Queue()

def worker():
    while True:
        chat_id, url = antrean.get()
        try:
            bot.send_message(chat_id, "⏳ Video kamu lagi diproses... sabar 10-20 menit ya!")
            av.cleanup()
            audio = av.download_audio(url)
            transkrip = av.transcribe_audio(audio, 10)
            kandidat = av.analyze_viral(transkrip, 3)
            if not kandidat:
                bot.send_message(chat_id, "❌ Maaf, tidak ditemukan momen viral di video ini.")
            else:
                av.cut_and_save(kandidat, url)
                clips = [
                    os.path.join(av.OUTPUT_DIR, f)
                    for f in sorted(os.listdir(av.OUTPUT_DIR))
                    if f.endswith(".mp4")
                ]
                if not clips:
                    bot.send_message(chat_id, "❌ Gagal memotong klip.")
                else:
                    bot.send_message(chat_id, f"✅ Selesai! {len(clips)} klip siap dipakai:")
                    for c in clips:
                        with open(c, "rb") as f:
                            bot.send_document(chat_id, f)
                    bot.send_message(chat_id, "💡 Suka hasilnya? Bagikan bot ini ke teman kreator kamu! 🚀")
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error: {e}")
        antrean.task_done()

threading.Thread(target=worker, daemon=True).start()

@bot.message_handler(func=lambda m: True)
def terima(m):
    teks = (m.text or "").strip()
    if "youtube.com" in teks or "youtu.be" in teks:
        antrean.put((m.chat.id, teks))
        bot.send_message(m.chat.id, f"📨 Link diterima! Posisi antrean: {antrean.qsize()}. Aku kabari kalau klipnya siap ya.")
    else:
        bot.send_message(m.chat.id, "🎬 *KlipViral Bot*\nKirim link YouTube di sini, aku potong jadi klip viral vertikal otomatis.\n(Gratis: 3 klip per video)", parse_mode="Markdown")

print("🤖 Bot jalan...")
bot.infinity_polling()
