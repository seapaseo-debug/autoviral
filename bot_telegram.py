import os
import re
import json
import queue
import threading
import time
import subprocess
import traceback

import telebot
from telebot import types

import autoviral as av

try:
    TOKEN = os.environ.get("BOT_TOKEN") or open("token.txt").read().strip()
except Exception:
    raise SystemExit("Buat dulu file token.txt berisi token BotFather.")

bot = telebot.TeleBot(TOKEN)

VAULT = "vault"
os.makedirs(VAULT, exist_ok=True)
KUOTA_FILE = "kuota.json"
META_FILE = "meta_user.json"

CHANNEL_VIP = "@KlipViral_Id"
LINK_CHANNEL = "https://t.me/KlipViral_Id"
LINK_YOUTUBE = "https://www.youtube.com/@FUNNYORCHANNEL"
LINK_TIKTOK = "https://www.tiktok.com/@allomesydan"
LINK_FACEBOOK = "https://www.facebook.com/share/1BirQm2EcW/"

PESAN_AKHIR = (
    "🛒 Mau punya mesin ini sendiri di HP kamu?\n"
    "Beli script KlipViral + panduan: http://lynk.id/lynkbyazl/6m2qld7mlr4x\n"
    "💸 Bebas biaya bulanan — sekali bayar, pakai sepuasnya!\n\n"
    "🎬 Mau tutorial klip viral lainnya?\n"
    "Gabung channel kami: " + LINK_CHANNEL
)

def baca_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def tulis_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def kuota_hari_ini(uid):
    d = baca_json(KUOTA_FILE, {})
    u = d.get(str(uid))
    if u and u.get("tanggal") == time.strftime("%Y-%m-%d"):
        return u.get("pakai", 0)
    return 0

def tandai_pakai(uid):
    d = baca_json(KUOTA_FILE, {})
    d[str(uid)] = {"tanggal": time.strftime("%Y-%m-%d"), "pakai": kuota_hari_ini(uid) + 1}
    tulis_json(KUOTA_FILE, d)

def simpan_meta(uid, url=None, best=None):
    d = baca_json(META_FILE, {})
    u = d.setdefault(str(uid), {})
    if url:
        u["url"] = url
    if best:
        u["best"] = best
    tulis_json(META_FILE, d)

def ambil_meta(uid):
    return baca_json(META_FILE, {}).get(str(uid), {})

def sudah_join(uid):
    try:
        st = bot.get_chat_member(CHANNEL_VIP, uid).status
        return st in ("member", "administrator", "creator")
    except Exception:
        return False

def durasi_video(url):
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download",
                            "--print", "%(duration)s", url],
                           capture_output=True, text=True, timeout=120)
        return float(r.stdout.strip() or 0)
    except Exception:
        return -1

def detik(v):
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)", str(v))
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    try:
        return float(v)
    except Exception:
        return None

def ambil_waktu(k, keys):
    if isinstance(k, dict):
        for key in keys:
            if key in k:
                t = detik(k[key])
                if t is not None:
                    return t
    return None

KEYS_MULAI = ["mulai", "start", "start_time", "waktu_mulai", "from"]
KEYS_SELESAI = ["selesai", "end", "end_time", "waktu_selesai", "to"]

def kirim_file(chat_id, path, caption=None, coba=3):
    for i in range(coba):
        try:
            with open(path, "rb") as f:
                bot.send_video(chat_id, f, caption=caption)
            return True
        except Exception:
            time.sleep(5)
    return False

def potong(src, mulai, dur, out, sensor=False):
    vf = "crop=ih*9/16:ih,scale=480:-2"
    if sensor:
        vf += ",boxblur=16:4"
    cmd = ["ffmpeg", "-y", "-ss", str(mulai), "-i", src, "-t", str(dur),
           "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
           "-c:a", "aac", "-b:a", "64k", out]
    subprocess.run(cmd, capture_output=True)
    return os.path.exists(out)

def download_video(url, out="video_original.mp4"):
    cmd = ["yt-dlp", "-f", "bv*[height<=480]+ba/b[height<=480]/b",
           "--merge-output-format", "mp4", "-o", out, url]
    subprocess.run(cmd, capture_output=True)
    return os.path.exists(out)

def menu_paket(lengkap=True):
    mk = types.InlineKeyboardMarkup()
    if lengkap:
        mk.add(types.InlineKeyboardButton("🆓 Gratis — 15 dtk (1 klip + 1 sensor)", callback_data="pick::free"))
    mk.add(types.InlineKeyboardButton("⭐ 5 — 5 klip 30 detik", callback_data="buy::30"))
    mk.add(types.InlineKeyboardButton("⭐ 10 — 5 klip 60 detik", callback_data="buy::60"))
    return mk

def menu_unlock():
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⭐ 3 — Buka versi bersih klip sensor", callback_data="buy::unlock"))
    return mk

def menu_gerbang():
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🚪 Join Channel VIP", url=LINK_CHANNEL))
    mk.add(types.InlineKeyboardButton("✅ Sudah join! Proses video saya", callback_data="gate::check"))
    return mk

antrean = queue.Queue()

def worker():
    while True:
        chat_id, url, paket = antrean.get()
        try:
            bot.send_message(chat_id, "⏳ Video kamu lagi diproses... sabar 10-20 menit ya!")
            av.cleanup()
            audio = av.download_audio(url)
            transkrip = av.transcribe_audio(audio, 10)
            kandidat = av.analyze_viral(transkrip, 5)
            if not kandidat:
                bot.send_message(chat_id, "❌ Maaf, tidak ditemukan momen viral di video ini.")
                antrean.task_done()
                continue
            if not download_video(url):
                bot.send_message(chat_id, "❌ Gagal download video original.")
                antrean.task_done()
                continue
            dur = paket["durasi"]
            outs = []
            for i, k in enumerate(kandidat):
                mulai = ambil_waktu(k, KEYS_MULAI)
                if mulai is None:
                    continue
                if potong("video_original.mp4", mulai, dur, f"klip_{i+1}.mp4"):
                    outs.append(f"klip_{i+1}.mp4")
            if not outs:
                with open("debug.log", "a") as f:
                    f.write("KANDIDAT: " + repr(kandidat) + "\n")
                bot.send_message(chat_id, "❌ Gagal memotong klip. (detail di debug.log)")
                antrean.task_done()
                continue
            if paket["gratis"]:
                mulai_best = ambil_waktu(kandidat[0], KEYS_MULAI)
                selesai_best = ambil_waktu(kandidat[0], KEYS_SELESAI)
                best = outs[0]
                free_clip = None
                if len(outs) >= 2:
                    free_clip = outs[1]
                elif mulai_best is not None and selesai_best is not None and (selesai_best - (mulai_best + dur)) >= 10:
                    if potong("video_original.mp4", mulai_best + dur, min(dur, selesai_best - mulai_best - dur), "klip_tambahan.mp4"):
                        free_clip = "klip_tambahan.mp4"
                vault_file = os.path.join(VAULT, f"best_{chat_id}.mp4")
                os.replace(best, vault_file)
                simpan_meta(chat_id, url=url, best=vault_file)
                if mulai_best is not None:
                    potong("video_original.mp4", mulai_best, dur, "preview_sensor.mp4", sensor=True)
                    kirim_file(chat_id, "preview_sensor.mp4",
                               caption="🔒 Ini momen PALING viral di videomu (skor tertinggi). Versi bersihnya cuma 3 ⭐!")
                if free_clip:
                    bot.send_message(chat_id, f"✅ Ini klip gratis kamu ({dur} detik):")
                    kirim_file(chat_id, free_clip)
                else:
                    bot.send_message(chat_id, "😅 Video ini cuma punya 1 momen viral. Versi bersihnya bisa dibuka pakai 3 ⭐!")
                bot.send_message(chat_id, "💡 Mau versi bersih & klip lebih panjang? Pencet tombol 👇", reply_markup=menu_unlock())
                bot.send_message(chat_id, PESAN_AKHIR)
                tandai_pakai(chat_id)
            else:
                simpan_meta(chat_id, url=url)
                bot.send_message(chat_id, f"✅ Selesai! {len(outs)} klip {dur} detik siap dipakai:")
                for c in outs:
                    kirim_file(chat_id, c)
                bot.send_message(chat_id, "💡 Suka hasilnya? Bagikan bot ini ke teman kreator kamu! 🚀")
                bot.send_message(chat_id, PESAN_AKHIR)
        except Exception as e:
            with open("debug.log", "a") as f:
                f.write(traceback.format_exc() + "\n")
            try:
                bot.send_message(chat_id, f"❌ Error: {e}")
            except Exception:
                pass
        antrean.task_done()

threading.Thread(target=worker, daemon=True).start()

@bot.callback_query_handler(func=lambda c: c.data.startswith("pick::"))
def pilih(c):
    uid = c.message.chat.id
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
    if not ambil_meta(uid).get("url"):
        bot.send_message(uid, "Kirim link YouTube dulu ya.")
        return
    if kuota_hari_ini(uid) >= 1:
        bot.send_message(uid, "⛔ Kuota gratis hari ini sudah dipakai. Besok gratis lagi! Atau lanjut sekarang pakai Bintang ⭐ 👇", reply_markup=menu_paket(lengkap=False))
        return
    bot.send_message(uid,
        "🎁 Klip gratismu hampir siap!\n"
        "Untuk mencegah spam, join dulu Channel VIP kami & dukung sosial media kami:\n\n"
        f"▶️ YouTube: {LINK_YOUTUBE}\n"
        f"🎵 TikTok: {LINK_TIKTOK}\n"
        f"📘 Facebook: {LINK_FACEBOOK}",
        reply_markup=menu_gerbang())

@bot.callback_query_handler(func=lambda c: c.data.startswith("gate::"))
def gerbang(c):
    uid = c.message.chat.id
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
    if sudah_join(uid):
        url = ambil_meta(uid).get("url")
        if not url:
            bot.send_message(uid, "Kirim link YouTube dulu ya.")
            return
        antrean.put((uid, url, {"gratis": True, "durasi": 15}))
        bot.send_message(uid, f"📨 Terverifikasi! Posisi antrean: {antrean.qsize()}. Sabar 10-20 menit ya 😄")
    else:
        bot.send_message(uid, "👀 Eits, kamu belum join Channel VIP! Pencet tombol 🚪 dulu, lalu pencet ✅ lagi ya.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy::"))
def beli(c):
    uid = c.message.chat.id
    jenis = c.data.split("::")[1]
    meta = ambil_meta(uid)

    def jawab(teks):
        try:
            bot.answer_callback_query(c.id, teks)
        except Exception:
            try:
                bot.send_message(uid, teks)
            except Exception:
                pass

    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass

    if jenis == "unlock":
        best = meta.get("best")
        if not best or not os.path.exists(best):
            jawab("🔒 Belum ada klip terkunci. Kirim link YouTube dulu ya.")
            return
        judul, stars = "Buka versi bersih klip terbaik", 3
        payload = f"unlock::{uid}"
    else:
        url = meta.get("url")
        if not url:
            jawab("Kirim link YouTube dulu ya.")
            return
        dv = durasi_video(url)
        if dv > 3600:
            jawab("Video maksimal 60 menit.")
            return
        judul = f"Paket 5 klip {jenis} detik"
        stars = 5 if jenis == "30" else 10
        payload = f"paket::{jenis}::{uid}"
    try:
        bot.send_invoice(uid, title=judul,
                         description="Pembayaran otomatis via Telegram Stars",
                         invoice_payload=payload, provider_token="",
                         currency="XTR",
                         prices=[types.LabeledPrice("Stars", stars)])
    except Exception as e:
        jawab(f"❌ Gagal membuat tagihan: {e}")

@bot.pre_checkout_query_handler(func=lambda q: True)
def pcq(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def lunas(m):
    uid = m.chat.id
    bagian = m.successful_payment.invoice_payload.split("::")
    if bagian[0] == "unlock":
        meta = ambil_meta(uid)
        best = meta.get("best")
        if best and os.path.exists(best):
            kirim_file(uid, best, caption="🎉 Ini versi bersih klip terbaikmu! Selamat berkarya!")
        else:
            bot.send_message(uid, "⚠️ File tidak ditemukan. Kirim link YouTube lagi ya.")
    else:
        dur = int(bagian[1])
        url = ambil_meta(uid).get("url")
        if url:
            antrean.put((uid, url, {"gratis": False, "durasi": dur}))
            bot.send_message(uid, f"🎉 Pembayaran diterima! 5 klip {dur} detik masuk antrean.")

@bot.message_handler(func=lambda m: True)
def terima(m):
    uid = m.chat.id
    teks = (m.text or "").strip()
    if "youtube.com" in teks or "youtu.be" in teks:
        simpan_meta(uid, url=teks)
        dv = durasi_video(teks)
        if 0 < dv < 20:
            bot.send_message(uid, "❌ Video terlalu pendek. Minimal 20 detik ya.")
            return
        if dv > 1800:
            bot.send_message(uid, "⛔ Video di atas 30 menit khusus user Bintang ⭐. Pilih paket 👇", reply_markup=menu_paket(lengkap=False))
            return
        bot.send_message(uid, "🎬 Video terdeteksi! Pilih paket pengolahan 👇", reply_markup=menu_paket())
    else:
        bot.send_message(uid, "🎬 *KlipViral Bot*\nKirim link YouTube (20 dtk - 30 mnt), aku potong jadi klip viral vertikal otomatis.\n🆓 Gratis 1x/hari: 1 klip 15 dtk + 1 klip sensor (wajib join Channel VIP).\n⭐ Bintang: versi bersih & klip 30/60 dtk.\n📢 Komunitas: " + LINK_CHANNEL, parse_mode="Markdown")

print("🤖 Bot jalan...")
bot.infinity_polling()
