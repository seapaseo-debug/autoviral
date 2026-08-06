import os
import subprocess

import streamlit as st

st.set_page_config(page_title="AutoViral AI", page_icon="🎬")

# ffmpeg terbundel (Streamlit Cloud tidak bisa download ffmpeg)
try:
    import imageio_ffmpeg
    import shutil as _sh
    _ff = imageio_ffmpeg.get_ffmpeg_exe()
    _bin = "/tmp/ffbin"
    os.makedirs(_bin, exist_ok=True)
    _target = os.path.join(_bin, "ffmpeg")
    if not os.path.exists(_target):
        try:
            os.symlink(_ff, _target)
        except Exception:
            _sh.copy2(_ff, _target)
            os.chmod(_target, 0o755)
    os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
    try:
        from pydub import AudioSegment
        AudioSegment.converter = _target
    except Exception:
        pass
except Exception as e:
    st.warning(f"⚠️ ffmpeg gagal dimuat: {e}")

import autoviral as av

# amankan folder gallery di server (bukan Android)
try:
    os.makedirs(av.GALLERY_DIR, exist_ok=True)
except Exception:
    av.GALLERY_DIR = av.OUTPUT_DIR

# daftar "penyamaran" klien YouTube buat menghindari 403
CLIENTS = ["ios,android", "tv,android_vr", "web,mweb"]

def download_audio_lite(url):
    if os.path.exists("audio_podcast.mp3"):
        return "audio_podcast.mp3"
    for clients in CLIENTS:
        cmd = [
            "yt-dlp", "-f", "bestaudio/best",
            "--extractor-args", f"youtube:player_client={clients}",
            "-x", "--audio-format", "mp3",
            "--retries", "3",
            "-o", "audio_podcast.%(ext)s",
            url, "--quiet", "--no-warnings",
        ]
        subprocess.run(cmd, check=False)
        if os.path.exists("audio_podcast.mp3"):
            return "audio_podcast.mp3"
    raise RuntimeError("YouTube memblokir download dari server ini (403).")

def download_video_lite(url):
    if os.path.exists("video_original.mp4"):
        return True
    for clients in CLIENTS:
        cmd = [
            "yt-dlp", "-f", "best[height<=480]/best",
            "--merge-output-format", "mp4",
            "--extractor-args", f"youtube:player_client={clients}",
            "--retries", "3",
            "-o", "video_original.mp4",
            url, "--quiet", "--no-warnings",
        ]
        subprocess.run(cmd, check=False)
        if os.path.exists("video_original.mp4"):
            return True
    return False

# ganti downloader bawaan dengan versi anti-403
av.download_audio = download_audio_lite

st.title("🎬 AutoViral AI")
st.caption("Tempel link YouTube → klip viral vertikal otomatis. (Versi gratis: 480p)")

url = st.text_input("🔗 Link YouTube")
durasi = st.number_input("⏱ Menit diproses", 1, 30, 10)
jumlah = st.number_input("🎬 Jumlah klip", 1, 5, 3)

if st.button("🚀 PROSES!", type="primary"):
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        st.error("❌ Link YouTube tidak valid.")
    else:
        try:
            with st.spinner("🧹 Bersih-bersih & 📥 download audio..."):
                av.cleanup()
                audio = av.download_audio(url)
            with st.spinner("🎤 Transkrip audio (ini lama, sabar ya)..."):
                transkrip = av.transcribe_audio(audio, int(durasi))
            if not transkrip:
                st.error("❌ Tidak ada hasil transkrip.")
                st.stop()
            with st.spinner("🧠 Analisis momen viral..."):
                kandidat = av.analyze_viral(transkrip, int(jumlah))
            if not kandidat:
                st.error("❌ Tidak ditemukan momen viral.")
                st.stop()
            with st.spinner("✂️ Download video & potong klip..."):
                if not download_video_lite(url):
                    st.error("❌ YouTube memblokir download video dari server gratis (403). Coba link lain atau ulangi lagi.")
                    st.stop()
                av.cut_and_save(kandidat, url)
            clips = [
                os.path.join(av.OUTPUT_DIR, f)
                for f in sorted(os.listdir(av.OUTPUT_DIR))
                if f.endswith(".mp4")
            ]
            if not clips:
                st.error("❌ Gagal memotong klip.")
            else:
                st.success(f"✅ Selesai! {len(clips)} klip siap.")
                for c in clips:
                    st.video(c)
                    with open(c, "rb") as f:
                        st.download_button(
                            f"📥 Download {os.path.basename(c)}",
                            data=f.read(),
                            file_name=os.path.basename(c),
                        )
        except Exception as e:
            st.error(f"❌ Error: {e}")
