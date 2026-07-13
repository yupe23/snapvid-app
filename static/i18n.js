const TRANSLATIONS = {
  ar: {
    dir: "rtl",
    mode_video: "🎬 فيديو",
    mode_mp3: "🎵 MP3",
    input_label_video: "الصق رابط الفيديو (فيسبوك / إنستغرام)",
    input_label_mp3: "الصق رابط الفيديو لاستخراج الصوت (فيسبوك / إنستغرام)",
    btn_download: "تنزيل الآن",
    btn_extract: "استخراج MP3",
    btn_starting: "جارٍ البدء...",
    btn_downloading: "جارٍ التنزيل...",
    btn_extracting: "جارٍ الاستخراج...",
    err_empty_url: "دخل الرابط أولاً",
    err_conn: "تعذر الاتصال بالسيرفر — تأكد أن app.py شغال",
    err_status: "خطأ في جلب الحالة",
    status_starting: "بدء الاتصال",
    status_downloading: "تنزيل",
    status_extracting: "استخراج الصوت",
    status_merging: "دمج الملف",
    status_merging_mp3: "تحويل إلى MP3",
    status_done: "اكتمل",
    status_error: "خطأ",
    progress_label_video: "جارٍ التنزيل",
    progress_label_mp3: "جارٍ الاستخراج",
    success_video: "اكتمل التنزيل بنجاح",
    success_mp3: "اكتمل استخراج MP3 بنجاح",
    downloaded_label: "تم التنزيل",
    mp3_ready_label: "MP3 · جاهز",
    save_btn: "حفظ",
    youtube_note: "روابط يوتيوب غير مدعومة في هذا التطبيق."
  },
  fr: {
    dir: "ltr",
    mode_video: "🎬 Vidéo",
    mode_mp3: "🎵 MP3",
    input_label_video: "Collez le lien de la vidéo (Facebook / Instagram)",
    input_label_mp3: "Collez le lien pour extraire l'audio (Facebook / Instagram)",
    btn_download: "Télécharger",
    btn_extract: "Extraire en MP3",
    btn_starting: "Démarrage...",
    btn_downloading: "Téléchargement...",
    btn_extracting: "Extraction...",
    err_empty_url: "Entrez d'abord un lien",
    err_conn: "Connexion au serveur impossible — vérifiez que app.py est lancé",
    err_status: "Erreur lors de la récupération du statut",
    status_starting: "Connexion",
    status_downloading: "Téléchargement",
    status_extracting: "Extraction audio",
    status_merging: "Fusion du fichier",
    status_merging_mp3: "Conversion en MP3",
    status_done: "Terminé",
    status_error: "Erreur",
    progress_label_video: "Téléchargement en cours",
    progress_label_mp3: "Extraction en cours",
    success_video: "Téléchargement terminé avec succès",
    success_mp3: "Extraction MP3 terminée avec succès",
    downloaded_label: "Téléchargé",
    mp3_ready_label: "MP3 · prêt",
    save_btn: "Enregistrer",
    youtube_note: "Les liens YouTube ne sont pas pris en charge dans cette application."
  },
  en: {
    dir: "ltr",
    mode_video: "🎬 Video",
    mode_mp3: "🎵 MP3",
    input_label_video: "Paste the video link (Facebook / Instagram)",
    input_label_mp3: "Paste the video link to extract audio (Facebook / Instagram)",
    btn_download: "Download Now",
    btn_extract: "Extract MP3",
    btn_starting: "Starting...",
    btn_downloading: "Downloading...",
    btn_extracting: "Extracting...",
    err_empty_url: "Enter a link first",
    err_conn: "Couldn't reach the server — make sure app.py is running",
    err_status: "Error fetching status",
    status_starting: "Connecting",
    status_downloading: "Downloading",
    status_extracting: "Extracting audio",
    status_merging: "Merging file",
    status_merging_mp3: "Converting to MP3",
    status_done: "Done",
    status_error: "Error",
    progress_label_video: "Downloading",
    progress_label_mp3: "Extracting",
    success_video: "Download completed successfully",
    success_mp3: "MP3 extraction completed successfully",
    downloaded_label: "Downloaded",
    mp3_ready_label: "MP3 · ready",
    save_btn: "Save",
    youtube_note: "YouTube links are not supported in this app."
  }
};

function getLang() {
  return localStorage.getItem('snapvid_lang') || 'ar';
}

function setLang(code) {
  localStorage.setItem('snapvid_lang', code);
  applyLang(code);
}

function applyLang(code) {
  const t = TRANSLATIONS[code] || TRANSLATIONS.ar;
  document.documentElement.lang = code;
  document.documentElement.dir = t.dir;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key] !== undefined) el.textContent = t[key];
  });

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === code);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  applyLang(getLang());
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => setLang(btn.dataset.lang));
  });
});
