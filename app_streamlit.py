import os
import subprocess

import streamlit as st

st.set_page_config(page_title="AutoViral AI", page_icon="🎬")

# ffmpeg statis (Streamlit Cloud tidak punya ffmpeg bawaan)
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    st.warning(f"⚠️ ffmpeg statis gagal dimuat: {e}")

import autoviral as av

# amankan folder gallery di server (bukan Android)
try:
    os.makedirs(av.GALLERY_DIR, exist_ok=True)
except Exception:
    av.GALLERY_DIR = av.OUTPUT_DIR

st.title("🎬 AutoViral AI")
st.caption("Tempel link YouTube → klip viral vertikal otomatis. (Versi gratis: 480p)")

url = st.text_input("🔗 Link YouTube")
durasi = st.number_input("⏱ Menit diproses", 1, 30, 10)
jumlah = st.number_input("🎬 Jumlah klip", 1, 5, 3)

def download_video_lite(link):
    if os.path.exists("video_original.mp4"):
        return
    cmd = [
        "yt-dlp", "-f", "best[height<=480]/best",
        "--merge-output-format", "mp4",
        "--retries", "5",
        "-o", "video_original.mp4",
        link, "--quiet", "--no-warnings",
    ]
    subprocess.run(cmd, check=False)

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
                download_video_lite(url)
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
