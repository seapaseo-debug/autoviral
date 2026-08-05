import os
import re
import json
import shutil
import subprocess
import time
import threading
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import yt_dlp

# ==========================================================
#                 AUTO VIRAL AI v3.0
# ==========================================================

VERSION = "3.0"

DEFAULT_DURATION = 10
DEFAULT_TOP_KLIP = 5

OUTPUT_DIR = "klip_viral"
GALLERY_DIR = "/sdcard/Download/viral_clips"

BAR_LENGTH = 40

KATA_VIRAL = {
    "lucu": [
        "lucu", "ngakak", "ketawa",
        "gemas", "kocak"
    ],
    "kontroversi": [
        "rahasia", "sebenarnya",
        "faktanya", "banyak yang salah"
    ],
    "kejutan": [
        "ternyata",
        "tiba tiba",
        "nggak nyangka",
        "mengejutkan"
    ],
    "emosional": [
        "sedih",
        "haru",
        "menangis",
        "marah",
        "bahagia"
    ],
    "hook": [
        "tahu nggak",
        "pernah nggak",
        "bayangin",
        "gimana kalau"
    ]
}

# ==========================================================
# WARNA TERMINAL
# ==========================================================

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

try:
    from lolcat import Lolcat
    LC = Lolcat()
    LOLCAT = True
except Exception:
    LOLCAT = False


def cprint(text):
    if LOLCAT:
        LC.cprint(text)
    else:
        print(text)


# ==========================================================
# UI
# ==========================================================

def line():
    os.system(f'echo "{"=" * 65}" | lolcat')

def title(text):
    line()
    cprint(f" {text}")
    line()


def success(text):
    print(f"{GREEN}✅ {text}{RESET}")


def warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def error(text):
    print(f"{RED}❌ {text}{RESET}")

def info(text):
    print(f"{CYAN}➜ {text}{RESET}")

def print_sep(text=""):
    line()
    if text:
        cprint(f" {text}")
    line()

def progress(percent, text=""):
    filled = int(BAR_LENGTH * percent / 100)
    empty = BAR_LENGTH - filled

    bar = "█" * filled + "░" * empty

    print(
        f"\r{CYAN}[{bar}] {percent:3d}% {text}{RESET}",
        end="",
        flush=True
    )


# ==========================================================
# SPLASH SCREEN
# ==========================================================

def show_loading_screen():

    os.system("clear")

    cprint("")
    cprint("╔══════════════════════════════════════════════════════╗")
    cprint("║                AUTOVIRAL AI v3.0                     ║")
    cprint("║         Ultimate YouTube Clip Generator              ║")
    cprint("╚══════════════════════════════════════════════════════╝")
    cprint("")

    modules = [
        "Loading AI Engine",
        "Loading Speech Recognition",
        "Loading FFmpeg",
        "Loading Video Analyzer",
        "Loading Clip Generator",
        "Preparing Workspace"
    ]

    for module in modules:

        print(f"{CYAN}{module}{RESET}")

        for i in range(101):

            progress(i)

            time.sleep(0.01)

        print(f" {GREEN}DONE{RESET}")

    print()

    success("System Ready")

    time.sleep(1)

    os.system("clear")


# ==========================================================
# CLEANUP
# ==========================================================

def cleanup():

    title("MEMBERSIHKAN FILE LAMA")

    files = [
        "audio_podcast.mp3",
        "video_original.mp4",
        "transkrip_viral.txt",
        "kandidat_viral.json",
        "temp_chunk.wav"
    ]

    for file in files:

        if os.path.exists(file):

            os.remove(file)

            success(file)

    if os.path.exists(OUTPUT_DIR):

        shutil.rmtree(OUTPUT_DIR)

    if os.path.exists(GALLERY_DIR):

        shutil.rmtree(GALLERY_DIR)

    success("Workspace bersih.")


# ==========================================================
# INPUT USER
# ==========================================================

def get_user_input():

    title("AUTO VIRAL")

    url = input("🔗 Link YouTube : ").strip()

    durasi = input(
        f"⏱ Menit diproses [{DEFAULT_DURATION}] : "
    ).strip()

    jumlah = input(
        f"🎬 Jumlah klip [{DEFAULT_TOP_KLIP}] : "
    ).strip()

    durasi = int(durasi) if durasi.isdigit() else DEFAULT_DURATION
    jumlah = int(jumlah) if jumlah.isdigit() else DEFAULT_TOP_KLIP

    return url, durasi, jumlah

def download_audio(url):
    title("DOWNLOAD AUDIO")

    def progress_hook(d):

        if d["status"] == "downloading":

            percent = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "...").strip()
            eta = d.get("_eta_str", "--")

            try:
                value = float(percent.replace("%", "").strip())
            except Exception:
                value = 0

            filled = int(value / 5)
            bar = "█" * filled + "░" * (20 - filled)

            if value < 25:
                color = RED
            elif value < 50:
                color = YELLOW
            elif value < 75:
                color = GREEN
            else:
                color = CYAN

            print(
                f"\r{color}[{bar}] {percent:>6} | {speed:>10} | ETA {eta}{RESET}",
                end="",
                flush=True
            )

        elif d["status"] == "finished":

            print()

            success("Download selesai")
            info("Mengkonversi ke MP3...")

    ydl_opts = {

        "format": "bestaudio/best",

        "outtmpl": "audio_podcast.%(ext)s",

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        "ignoreerrors": False,

        "retries": 10,

        "fragment_retries": 10,

        "concurrent_fragment_downloads": 5,

        "progress_hooks": [progress_hook],

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "ios",
                    "web"
                ]
            }
        },

        "http_headers": {
            "User-Agent":
            "Mozilla/5.0"
        }

    }

    start = time.time()

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:

        error(f"Gagal download audio : {e}")

        raise

    elapsed = time.time() - start

    success(f"Audio berhasil didownload ({elapsed:.1f} detik)")

    if not os.path.exists("audio_podcast.mp3"):

        error("audio_podcast.mp3 tidak ditemukan!")

        raise FileNotFoundError("audio_podcast.mp3")

    return "audio_podcast.mp3"

def transcribe_audio(audio_file, max_minutes):
    print_sep("🎤 [TRANSCRIP ENGINE]")
    print("🧠 Mentranskrip audio dengan AI (mohon tunggu...)")
    print()

    spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠧', '⠇', '⠏']

    print("\033[93m   ⏳ Memuat file audio...\033[0m", end="", flush=True)
    for _ in range(10):
        for s in spinners:
            print(f"\r\033[93m   {s} Memuat file audio...\033[0m", end="", flush=True)
            time.sleep(0.05)
    print("\r\033[92m   ✅ Audio berhasil dimuat!          \033[0m")

    audio = AudioSegment.from_mp3(audio_file)

    max_ms = max_minutes * 60 * 1000
    if len(audio) > max_ms:
        audio = audio[:max_ms]

    print("\033[93m   ✂️ Memotong audio berdasarkan jeda...\033[0m", end="", flush=True)

    for _ in range(10):
        for s in spinners:
            print(f"\r\033[93m   {s} Memotong audio...\033[0m", end="", flush=True)
            time.sleep(0.05)

    print("\r\033[92m   ✅ Audio siap diproses!            \033[0m\n")

    chunks = split_on_silence(
        audio,
        min_silence_len=1500,
        silence_thresh=-35,
        keep_silence=300
    )

    recognizer = sr.Recognizer()

    transcriptions = []
    current_time = 0.0
    total_chunks = len(chunks)
    start_time = time.time()

    for i, chunk in enumerate(chunks):

        if chunk.duration_seconds < 1:
            current_time += chunk.duration_seconds
            continue

        chunk.export("temp_chunk.wav", format="wav")

        try:

            with sr.AudioFile("temp_chunk.wav") as source:
                audio_data = recognizer.record(source)

            text = recognizer.recognize_google(
                audio_data,
                language="id-ID"
            )

            start_seg = current_time
            end_seg = start_seg + chunk.duration_seconds

            transcriptions.append({
                "start": start_seg,
                "end": end_seg,
                "text": text.strip()
            })

        except Exception:
            end_seg = current_time + chunk.duration_seconds

        current_time = end_seg

        progress = (i + 1) / total_chunks * 100

        filled = int(progress / 2.5)
        bar = "█" * filled + "░" * (40 - filled)

        elapsed = time.time() - start_time

        if i > 0:
            avg = elapsed / (i + 1)
            eta = avg * (total_chunks - i - 1)
        else:
            eta = 0

        spinner = spinners[i % len(spinners)]

        sys.stdout.write(f"\033[2K\r   {spinner} [{bar}] {progress:5.1f}% | {i+1}/{total_chunks} | ETA {eta:5.1f}s")
        sys.stdout.flush()

    print()

    total_time = time.time() - start_time
    total_words = sum(len(x["text"].split()) for x in transcriptions)

    print("   " + "─" * 56)
    print(f"   📊 Total Chunk   : {total_chunks}")
    print(f"   ✅ Berhasil      : {len(transcriptions)}")
    print(f"   📝 Total Kata    : {total_words}")
    print(f"   ⏱️ Waktu Proses  : {total_time:.2f} detik")

    if os.path.exists("temp_chunk.wav"):
        os.remove("temp_chunk.wav")

    with open(
        "transkrip_viral.txt",
        "w",
        encoding="utf-8"
    ) as f:

        for t in transcriptions:

            sm = int(t["start"] // 60)
            ss = int(t["start"] % 60)

            em = int(t["end"] // 60)
            es = int(t["end"] % 60)

            f.write(
                f"[{sm:02d}:{ss:02d} - {em:02d}:{es:02d}] "
                f"{t['text']}\n"
            )

    print_sep("✅ Transkrip selesai disimpan!")

    return transcriptions

def analyze_viral(transcriptions, top_n):

    print_sep("🧠 [2] ANALISIS KONTEN VIRAL")

    hasil = []

    for t in transcriptions:

        durasi = t["end"] - t["start"]

        if durasi < 15:
            continue

        if durasi > 60:
            continue

        text = t["text"]
        text_lower = text.lower()

        skor = 0

        # ===========================
        # Keyword viral
        # ===========================

        for kategori, keywords in KATA_VIRAL.items():

            for kw in keywords:

                if kw in text_lower:
                    skor += 2

        # ===========================
        # Hook
        # ===========================

        if "?" in text:
            skor += 3

        if "!" in text:
            skor += 2

        # ===========================
        # Angka
        # ===========================

        if re.search(r"\d+", text):
            skor += 1

        # ===========================
        # Panjang kalimat
        # ===========================

        jumlah_kata = len(text.split())

        if jumlah_kata >= 12:
            skor += 2

        if jumlah_kata >= 20:
            skor += 2

        # ===========================
        # Bonus emosi
        # ===========================

        if any(
            kata in text_lower
            for kata in [
                "ternyata",
                "rahasia",
                "nggak nyangka",
                "gila",
                "serius",
                "wow",
                "viral",
                "parah"
            ]
        ):
            skor += 3

        hasil.append({

            "start": t["start"],

            "end": t["end"],

            "text": text,

            "duration": durasi,

            "skor_viral": skor

        })

    hasil.sort(
        key=lambda x: x["skor_viral"],
        reverse=True
    )

    top_kandidat = hasil[:top_n]

    print()

    print("🏆 HASIL ANALISIS\n")

    for i, item in enumerate(top_kandidat, start=1):

        sm = int(item["start"] // 60)
        ss = int(item["start"] % 60)

        em = int(item["end"] // 60)
        es = int(item["end"] % 60)

        print("─" * 60)

        print(
            f"#{i} | "
            f"Skor {item['skor_viral']} | "
            f"{sm:02d}:{ss:02d} - {em:02d}:{es:02d}"
        )

        print()

        print(item["text"])

        print()

    with open(

        "kandidat_viral.json",

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            top_kandidat,

            f,

            indent=2,

            ensure_ascii=False

        )

    print_sep(
        f"✅ Ditemukan {len(top_kandidat)} kandidat viral"
    )

    return top_kandidat

def process_clip(args):

    nomor, item = args

    start = max(0, int(item["start"]))

    durasi = int(item["end"] - item["start"])

    output = os.path.join(
        OUTPUT_DIR,
        f"klip_{nomor:02d}_viral.mp4"
    )

    cmd = [

        "ffmpeg",

        "-hide_banner",

        "-loglevel","error",

        "-y",

        "-ss",str(start),

        "-t",str(durasi),

        "-i","video_original.mp4",

        "-vf",
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=720:1280",

        "-preset","ultrafast",

        "-threads","0",

        "-c:v","libx264",

        "-crf","24",

        "-c:a","aac",

        "-b:a","128k",

        output

    ]

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    shutil.copy2(
        output,
        os.path.join(
            GALLERY_DIR,
            os.path.basename(output)
        )
    )

    return nomor

def cut_and_save(kandidat, url):
    print_sep("✂️ [3] MEMOTONG VIDEO")

    if not os.path.exists("video_original.mp4"):
        print("📥 Download video original (mohon tunggu)...")
        
        # TRIK 1: Coba Android Client dulu (paling cepat)
        cmd = [
            "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--extractor-args", "youtube:player_client=android",
            "--retries", "5", "-o", "video_original.mp4", url, "--quiet"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            success("Video original siap!")
        except Exception:
            warning("Gagal via Android, mencoba fallback iOS (anti-gagal)...")
            # TRIK 2: Fallback ke iOS Client (Paling ampuh untuk video gambar statis/podcast)
            cmd_ios = [
                "yt-dlp", "-f", "best",
                "--extractor-args", "youtube:player_client=ios",
                "--retries", "5", "-o", "video_original.mp4", url, "--quiet"
            ]
            try:
                subprocess.run(cmd_ios, check=True)
                success("Video original siap (via iOS)!")
            except Exception:
                error("Gagal download video. Coba gunakan link YouTube yang lain.")
                return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(GALLERY_DIR, exist_ok=True)

    total = len(kandidat)
    workers = min(4, os.cpu_count() or 2)

    print(f"\n⚡ Memproses {total} klip secara paralel ({workers} workers)...")

    # PERBAIKAN INDENTASI DI SINI
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for nomor, item in enumerate(kandidat, start=1):
            futures.append(executor.submit(process_clip, (nomor, item)))

        selesai = 0
        for future in as_completed(futures):
            future.result()
            selesai += 1
            print(f"\r✅ {selesai}/{total} klip selesai", end="", flush=True)

    print()
    print_sep("🎉 Semua klip selesai dipotong")
    print(f"📂 Output: {OUTPUT_DIR}")
    print(f"📱 Gallery: {GALLERY_DIR}")

def main():

    mulai = time.time()

    try:

        show_loading_screen()

        cleanup()

        url, durasi, jumlah = get_user_input()

        if not url:

            print("\n❌ Link YouTube kosong!")

            return

        if "youtube.com" not in url and "youtu.be" not in url:

            print("\n❌ Link YouTube tidak valid!")

            return

        print()

        audio_file = download_audio(url)

        transcriptions = transcribe_audio(
            audio_file,
            durasi
        )

        if len(transcriptions) == 0:

            print("\n❌ Tidak ada hasil transkrip.")

            return

        kandidat = analyze_viral(
            transcriptions,
            jumlah
        )

        if len(kandidat) == 0:

            print("\n❌ Tidak ditemukan bagian viral.")

            return

        cut_and_save(
            kandidat,
            url
        )

        selesai = time.time() - mulai

        print()

        print("═" * 60)

        print("🎉 AUTO VIRAL AI SELESAI")

        print("═" * 60)

        print(f"🎬 Total Klip   : {len(kandidat)}")

        print(f"⏱️ Total Waktu  : {selesai:.1f} detik")

        print(f"📂 Output       : {OUTPUT_DIR}")

        print(f"📱 Gallery      : {GALLERY_DIR}")

        print("═" * 60)

    except KeyboardInterrupt:

        print("\n")

        print("⚠️ Proses dibatalkan pengguna.")

    except Exception as e:

        print("\n")

        print(f"❌ ERROR : {e}")


if __name__ == "__main__":

    main()
