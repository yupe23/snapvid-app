from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import uuid
import threading
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# نخزن حالة كل عملية تنزيل هنا: progress, status, filename
jobs = {}

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
SOCIAL_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "fb.watch",
    "www.fb.watch",
}


def normalize_youtube_url(url):
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "").split(":")[0]
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"} and path:
        return f"https://www.youtube.com/watch?v={path}"

    if host.endswith("youtube.com"):
        video_id = None
        qs = parse_qs(parsed.query)
        if qs.get("v"):
            video_id = qs["v"][0]
        elif path.startswith("shorts/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("embed/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("live/"):
            video_id = path.split("/", 1)[1]

        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    return url.strip()


def detect_platform(url):
    normalized = normalize_youtube_url(url) if "youtube" in url.lower() or "youtu.be" in url.lower() else url
    parsed = urlparse(normalized)
    host = parsed.netloc.lower().replace("www.", "").split(":")[0]

    if host in YOUTUBE_HOSTS or host.endswith("youtube.com") or host.endswith("youtu.be"):
        return "youtube"
    if host in SOCIAL_HOSTS or host.endswith("tiktok.com") or host.endswith("instagram.com") or host.endswith("facebook.com"):
        if "instagram" in host:
            return "instagram"
        if "facebook" in host or host.endswith("fb.watch"):
            return "facebook"
        return "tiktok"
    return None


def format_youtube_error(exc):
    message = str(exc).lower()

    if "age" in message or "restricted" in message:
        return "This YouTube video is age-restricted and cannot be downloaded here."
    if "private" in message:
        return "This YouTube video is private."
    if "geo" in message or "country" in message or "region" in message:
        return "This YouTube video is geo-blocked or unavailable in your region."
    if "live" in message or "livestream" in message:
        return "Live streams are not supported for download in this app."
    if "unavailable" in message or "removed" in message:
        return "This YouTube video is unavailable or has been removed."
    return "Unable to download this YouTube video. The link may be private, age-restricted, removed, or region-blocked."


def get_best_quality_label(info):
    formats = info.get("formats") or []
    video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("ext") in {"mp4", "webm"}]
    if not video_formats:
        return "best available"

    best = max(video_formats, key=lambda item: (item.get("height") or 0, item.get("tbr") or 0, item.get("format_id") or ""))
    height = best.get("height") or ""
    return f"{height}p" if height else best.get("format_id", "best available")


def validate_url(url):
    platform = detect_platform(url)
    if platform in {"youtube", "tiktok", "instagram", "facebook"}:
        return platform
    return None


def probe_youtube(url):
    probe_opts = {
        "quiet": True,
        "noprogress": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not isinstance(info, dict):
        raise yt_dlp.utils.DownloadError("Could not extract YouTube video information.")

    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            raise yt_dlp.utils.DownloadError("This YouTube playlist does not contain downloadable videos.")
        info = entries[0]

    if info.get("live_status") in {"is_live", "was_live", "post_live"}:
        raise yt_dlp.utils.DownloadError("Live streams are not supported in this app.")

    if info.get("availability") and info.get("availability") != "public":
        raise yt_dlp.utils.DownloadError(f"YouTube availability error: {info.get('availability')}")

    if info.get("age_restricted"):
        raise yt_dlp.utils.DownloadError("Age-restricted video.")

    if info.get("is_private"):
        raise yt_dlp.utils.DownloadError("Private video.")

    return info


def run_download(job_id, url):
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    url = normalize_youtube_url(url) if detect_platform(url) == "youtube" else url
    platform = detect_platform(url)

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
        "noplaylist": True,
    }

    if platform == "youtube":
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ydl_opts["merge_output_format"] = "mp4"

    try:
        if platform == "youtube":
            info = probe_youtube(url)
            jobs[job_id]["quality"] = get_best_quality_label(info)
            jobs[job_id]["available_formats"] = len(info.get("formats") or [])

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = os.path.basename(ydl.prepare_filename(info))
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
        jobs[job_id]["error"] = format_youtube_error(e) if platform == "youtube" else str(e)


def run_download_audio(job_id, url):
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    url = normalize_youtube_url(url) if detect_platform(url) == "youtube" else url
    platform = detect_platform(url)

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
        "noplaylist": True,
    }

    try:
        if platform == "youtube":
            info = probe_youtube(url)
            jobs[job_id]["quality"] = get_best_quality_label(info)
            jobs[job_id]["available_formats"] = len(info.get("formats") or [])

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
        jobs[job_id]["error"] = format_youtube_error(e) if platform == "youtube" else str(e)


@app.route("/")
def splash():
    return render_template("splash.html")


@app.route("/app")
def index():
    return render_template("index.html")


@app.route("/mp3")
def mp3_page():
    return render_template("mp3.html")


@app.route("/google8d8ce31a6193e415.html")
def google_verify():
    return send_file("google8d8ce31a6193e415.html")


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "الرابط فارغ"}), 400

    platform = validate_url(url)
    if not platform:
        return jsonify({"success": False, "error": "الدعم حاليا للروابط: YouTube / TikTok / Instagram / Facebook"}), 400

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

    platform = validate_url(url)
    if not platform:
        return jsonify({"success": False, "error": "الدعم حاليا للروابط: YouTube / TikTok / Instagram / Facebook"}), 400

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
