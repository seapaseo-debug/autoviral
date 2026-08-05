import os
import subprocess
import gradio as gr
import autoviral as av

# amankan folder gallery di server (bukan Android)
try:
    os.makedirs(av.GALLERY_DIR, exist_ok=True)
except Exception:
    av.GALLERY_DIR = av.OUTPUT_DIR

def download_video_lite(url):
    """Download video ukuran kecil biar muat di hosting gratis."""
    if os.path.exists("video_original.mp4"):
        return
    cmd = [
        "yt-dlp", "-f", "best[height<=480]/best",
        "--merge-output-format", "mp4",
        "--retries", "5",
        "-o", "video_original.mp4",
        url, "--quiet", "--no-warnings",
    ]
    subprocess.run(cmd, check=False)

def proses(url, durasi, jumlah):
    url = (url or "").strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        return "❌ Link YouTube tidak valid.", []
    try:
        durasi = int(durasi or av.DEFAULT_DURATION)
        jumlah = int(jumlah or av.DEFAULT_TOP_KLIP)
    except Exception:
        return "❌ Input menit/jumlah harus angka.", []
    try:
        av.cleanup()
        audio = av.download_audio(url)
        transkrip = av.transcribe_audio(audio, durasi)
        if not transkrip:
            return "❌ Tidak ada hasil transkrip.", []
        kandidat = av.analyze_viral(transkrip, jumlah)
        if not kandidat:
            return "❌ Tidak ditemukan momen viral.", []
        download_video_lite(url)
        av.cut_and_save(kandidat, url)
        clips = [
            os.path.join(av.OUTPUT_DIR, f)
            for f in sorted(os.listdir(av.OUTPUT_DIR))
            if f.endswith(".mp4")
        ]
        if not clips:
            return "❌ Gagal memotong klip.", []
        return f"✅ Selesai! {len(clips)} klip siap di-download.", clips
    except Exception as e:
        return f"❌ Error: {e}", []

demo = gr.Interface(
    fn=proses,
    inputs=[
        gr.Textbox(label="🔗 Link YouTube"),
        gr.Number(value=10, label="⏱ Menit diproses"),
        gr.Number(value=3, label="🎬 Jumlah klip"),
    ],
    outputs=[
        gr.Textbox(label="Status"),
        gr.Files(label="📥 Download klip"),
    ],
    title="🎬 AutoViral AI",
    description="Tempel link YouTube → klip viral vertikal otomatis. (Versi gratis: 480p)",
)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
