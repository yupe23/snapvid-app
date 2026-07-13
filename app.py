from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# نخزن حالة كل عملية تنزيل هنا: progress, status, filename
jobs = {}

BLOCKED_DOMAINS = ["youtube.com", "youtu.be", "music.youtube.com"]


def is_blocked(url):
    return any(domain in url.lower() for domain in BLOCKED_DOMAINS)


def run_download(job_id, url):
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = round((done / total) * 100, 1) if total else 0
            jobs[job_id]["progress"] = pct
            jobs[job_id]["status"] = "downloading"
        elif d["status"] == "finished":
            jobs[job_id]["status"] = "merging"

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "progress_hooks": [hook],
        "quiet": True,
        "noprogress": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = os.path.basename(ydl.prepare_filename(info))
            # بعد الدمج قد يتغير الامتداد إلى mp4
            base, _ = os.path.splitext(filename)
            final_name = base + ".mp4"
            if not os.path.exists(os.path.join(DOWNLOAD_DIR, final_name)):
                final_name = filename

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["filename"] = final_name
        jobs[job_id]["title"] = info.get("title", final_name)
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


def run_download_audio(job_id, url):
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = round((done / total) * 100, 1) if total else 0
            jobs[job_id]["progress"] = pct
            jobs[job_id]["status"] = "downloading"
        elif d["status"] == "finished":
            jobs[job_id]["status"] = "merging"

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestaudio/best",
        "progress_hooks": [hook],
        "quiet": True,
        "noprogress": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base = os.path.splitext(os.path.basename(ydl.prepare_filename(info)))[0]
            final_name = base + ".mp3"

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["filename"] = final_name
        jobs[job_id]["title"] = info.get("title", final_name)
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.route("/")
def splash():
    return render_template("splash.html")


@app.route("/app")
def index():
    return render_template("index.html")


@app.route("/mp3")
def mp3_page():
    return render_template("mp3.html")


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "الرابط فارغ"}), 400
    if is_blocked(url):
        return jsonify({"success": False, "error": "روابط يوتيوب غير مدعومة في هذا التطبيق"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "starting", "progress": 0}

    thread = threading.Thread(target=run_download, args=(job_id, url), daemon=True)
    thread.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/download-mp3", methods=["POST"])
def start_download_mp3():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "الرابط فارغ"}), 400
    if is_blocked(url):
        return jsonify({"success": False, "error": "روابط يوتيوب غير مدعومة في هذا التطبيق"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "starting", "progress": 0}

    thread = threading.Thread(target=run_download_audio, args=(job_id, url), daemon=True)
    thread.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"success": False, "error": "غير موجود"}), 404
    return jsonify({"success": True, **job})


@app.route("/api/file/<job_id>")
def get_file(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return jsonify({"success": False, "error": "الملف غير جاهز"}), 400
    path = os.path.join(DOWNLOAD_DIR, job["filename"])
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
