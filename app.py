import streamlit as st
import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import urllib.parse

# Konfigurasi Halaman Utama
st.set_page_config(
    page_title="OSINT Tool Suite Pro",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Advanced OSINT Web Application")
st.write("iqbalmantam property (*Open Source Intelligence*).")

# Pilihan Menu di Sidebar
menu = st.sidebar.selectbox(
    "Pilih Fitur OSINT:", 
    ["Username Tracker", "Image EXIF Extractor", "Email Breach Checker", "Google Dorking Assistant"]
)

# -------------------------------------------------------------------------
# FITUR 1: USERNAME TRACKER
# -------------------------------------------------------------------------
if menu == "Username Tracker":
    st.header("👤 Social Media Username Tracker")
    st.write("Periksa apakah sebuah username terdaftar di berbagai platform populer.")
    
    username = st.text_input("Masukkan Username Target:", placeholder="misal: johndoe123")
    
    if st.button("Mulai Pelacakan"):
        if username.strip() == "":
            st.warning("Silakan masukkan username terlebih dahulu.")
        else:
            platforms = {
                "GitHub": f"https://github.com/{username}",
                "Twitter/X": f"https://x.com/{username}",
                "Instagram": f"https://instagram.com/{username}",
                "Reddit": f"https://www.reddit.com/user/{username}",
                "Pinterest": f"https://www.pinterest.com/{username}",
                "TikTok": f"https://www.tiktok.com/@{username}"
            }
            
            st.info(f"Memulai pemindaian untuk username: **{username}**")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            for i, (name, url) in enumerate(platforms.items()):
                status_text.text(f"Memeriksa {name}...")
                try:
                    response = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
                    if response.status_code == 200:
                        results.append({"Platform": name, "Status": "Ditemukan ✅", "Link": url})
                    elif response.status_code == 404:
                        results.append({"Platform": name, "Status": "Tidak Ada ❌", "Link": "-"})
                    else:
                        results.append({"Platform": name, "Status": f"Status {response.status_code} ⚠️", "Link": url})
                except requests.exceptions.RequestException:
                    results.append({"Platform": name, "Status": "Error/RTO 🛑", "Link": "-"})
                
                progress_bar.progress((i + 1) / len(platforms))
            
            status_text.text("Pemindaian selesai!")
            st.subheader("Hasil Investigasi")
            st.dataframe(results, use_container_width=True)

# -------------------------------------------------------------------------
# FITUR 2: IMAGE EXIF EXTRACTOR
# -------------------------------------------------------------------------
elif menu == "Image EXIF Extractor":
    st.header("🖼️ Image Metadata (EXIF) Extractor")
    st.write("Unggah gambar (JPEG/JPG) untuk melihat metadata tersembunyi seperti perangkat, waktu, dan GPS.")
    
    uploaded_file = st.file_uploader("Pilih file gambar...", type=["jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Preview Gambar yang Diunggah", width=400)
        
        if st.button("Ekstrak Metadata"):
            st.subheader("Hasil Ekstraksi Metadata")
            exif_data = image._getexif()
            
            if not exif_data:
                st.warning("Tidak ditemukan metadata EXIF pada gambar ini.")
            else:
                parsed_exif = {}
                gps_info = {}
                
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "GPSInfo":
                        for gps_tag_id in value:
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag] = value[gps_tag_id]
                    else:
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8', errors='ignore')
                            except:
                                value = str(value)
                        parsed_exif[tag] = str(value)
                
                if parsed_exif:
                    st.markdown("### 📱 Informasi Kamera & File")
                    st.json(parsed_exif)
                
                if gps_info:
                    st.markdown("### 📍 Koordinat GPS Ditemukan")
                    st.json(gps_info)
                else:
                    st.info("Metadata umum ditemukan, tetapi gambar tidak mengandung koordinat lokasi (GPS).")

# -------------------------------------------------------------------------
# FITUR 3: EMAIL BREACH CHECKER
# -------------------------------------------------------------------------
elif menu == "Email Breach Checker":
    st.header("📧 Email Data Breach Checker")
    st.write("Periksa apakah email target pernah bocor dalam insiden peretasan publik menggunakan database intelijen terbuka.")
    
    email_input = st.text_input("Masukkan Alamat Email Target:", placeholder="contoh: target@email.com")
    
    if st.button("Cek Kebocoran Email"):
        if email_input.strip() == "" or "@" not in email_input:
            st.warning("Silakan masukkan alamat email yang valid.")
        else:
            st.info(f"Memeriksa database kebocoran untuk: **{email_input}**")
            
            # Menggunakan API publik gratis dari IntelX / LeakCheck via public proxy terpercaya
            # Sebagai alternatif OSINT gratis yang tidak membutuhkan API Key berbayar
            url = f"https://api.leakcheck.net/public?check={email_input}"
            
            try:
                response = requests.get(url, timeout=7)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success") and data.get("found", 0) > 0:
                        st.error(f"🚨 BAHAYA! Ditemukan {data['found']} kebocoran yang melibatkan email ini!")
                        
                        # Tampilkan daftar sumber kebocoran
                        st.subheader("Sumber Kebocoran Terdeteksi:")
                        for breach in data.get("sources", []):
                            st.write(f"• **{breach}**")
                            
                        st.warning("Rekomendasi: Segera ganti kata sandi email target dan aktifkan Autentikasi Dua Faktor (2FA).")
                    else:
                        st.success("✅ Aman! Email ini tidak ditemukan dalam database kebocoran publik saat ini.")
                else:
                    st.error("Gagal terhubung ke database LeakCheck. Coba lagi beberapa saat lagi.")
            except Exception as e:
                st.error(f"Terjadi kesalahan koneksi: {str(e)}")

# -------------------------------------------------------------------------
# FITUR 4: GOOGLE DORKING ASSISTANT
# -------------------------------------------------------------------------
elif menu == "Google Dorking Assistant":
    st.header("🔏 Google Dorking Generator & Assistant")
    st.write("Buat kueri pencarian spesifik Google (Dork) untuk menemukan informasi sensitif yang terekspos secara publik.")
    
    domain_target = st.text_input("Masukkan Domain/Situs Target (Opsional):", placeholder="misal: targetperusahaan.com")
    keyword_target = st.text_input("Masukkan Kata Kunci / Nama Target:", placeholder="misal: \"rahasia\" atau \"confidential\"")
    
    st.subheader("Pilih Jenis Informasi yang Ingin Dicari:")
    
    # Membuat tombol dorking otomatis siap pakai
    site_str = f"site:{domain_target} " if domain_target else ""
    
    dorks = {
        "📂 Cari File Dokumen Sensitif (PDF, DOCX, XLSX)": f"{site_str}filetype:pdf OR filetype:docx OR filetype:xlsx {keyword_target}",
        "🔑 Cari Halaman Login Admin / Panel Belakang": f"{site_str}inurl:login OR inurl:admin OR inurl:wp-login",
        "🗂️ Cari Direktori Folder Terbuka (Index of)": f"{site_str}intitle:\"index of\" \"parent directory\"",
        "📄 Cari File Konfigurasi / Backup database (SQL, ENV)": f"{site_str}filetype:sql OR filetype:env OR filetype:bak OR filetype:log",
        "📝 Cari Dokumen Berlabel Rahasia/Internal": f"{site_str}\"internal use only\" OR \"confidential\" OR \"strictly private\" {keyword_target}"
    }
    
    for label, dork_query in dorks.items():
        with st.expander(label):
            st.code(dork_query, language="text")
            # Membuat URL Google Search otomatis
            encoded_query = urllib.parse.quote_plus(dork_query)
            google_url = f"https://www.google.com/search?q={encoded_query}"
            st.markdown(f"[🚀 Jalankan Dorking Langsung di Google]({google_url})")
