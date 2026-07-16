import streamlit as st
import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import urllib.parse
import hashlib
import re

# Konfigurasi Halaman Utama
st.set_page_config(
    page_title="OSINT Suite Ultimate Pro Platform",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Ultimate OSINT Web Application")
st.write("iqbalmantam property (*Open Source Intelligence*) & Background Check.")

# Pilihan Menu di Sidebar (Kini ada 11 Fitur Utama!)
menu = st.sidebar.selectbox(
    "Pilih Fitur OSINT:", 
    [
        "Username Tracker (Deep)", 
        "Image EXIF Extractor", 
        "Email Breach Checker", 
        "Google Dorking Assistant",
        "IP & Domain Geolocation",
        "Phone Number OSINT Helper",
        "Social Media Target Finder",
        "Corporate Background Check",
        "Legal & Court Record Finder",
        "Hacked Password Checker",
        "Hash Tools & Identifier"
    ]
)

# -------------------------------------------------------------------------
# FITUR 1: USERNAME TRACKER (DEEP HUNT)
# -------------------------------------------------------------------------
if menu == "Username Tracker (Deep)":
    st.header("👤 Social Media Username Tracker (Deep Hunt)")
    st.write("Periksa keberadaan username target di berbagai macam ekosistem platform digital.")
    
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
                "TikTok": f"https://www.tiktok.com/@{username}",
                "Spotify": f"https://open.spotify.com/user/{username}",
                "Steam (Community)": f"https://steamcommunity.com/id/{username}",
                "SoundCloud": f"https://soundcloud.com/{username}",
                "Behance": f"https://www.behance.net/{username}",
                "DeviantArt": f"https://www.deviantart.com/{username}",
                "Twitch": f"https://www.twitch.tv/{username}"
            }
            
            st.info(f"Memulai pemindaian mendalam untuk username: **{username}**")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            for i, (name, url) in enumerate(platforms.items()):
                status_text.text(f"Memeriksa {name}...")
                try:
                    response = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
                    if response.status_code == 200:
                        results.append({"Kategori": "Aktif", "Platform": name, "Status": "Ditemukan ✅", "Link": url})
                    elif response.status_code == 404:
                        results.append({"Kategori": "Kosong", "Platform": name, "Status": "Tidak Ada ❌", "Link": "-"})
                    else:
                        results.append({"Kategori": "Mencurigakan", "Platform": name, "Status": f"Status {response.status_code} ⚠️", "Link": url})
                except requests.exceptions.RequestException:
                    results.append({"Kategori": "Error", "Platform": name, "Status": "Error/RTO 🛑", "Link": "-"})
                
                progress_bar.progress((i + 1) / len(platforms))
            
            status_text.text("Pemindaian mendalam selesai!")
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
    st.write("Periksa apakah email target pernah bocor dalam insiden peretasan publik.")
    
    email_input = st.text_input("Masukkan Alamat Email Target:", placeholder="contoh: target@email.com")
    
    if st.button("Cek Kebocoran Email"):
        if email_input.strip() == "" or "@" not in email_input:
            st.warning("Silakan masukkan alamat email yang valid.")
        else:
            st.info(f"Memeriksa database kebocoran untuk: **{email_input}**")
            url = f"https://api.leakcheck.net/public?check={email_input}"
            
            try:
                response = requests.get(url, timeout=7)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("found", 0) > 0:
                        st.error(f"🚨 BAHAYA! Ditemukan {data['found']} kebocoran yang melibatkan email ini!")
                        st.subheader("Sumber Kebocoran Terdeteksi:")
                        for breach in data.get("sources", []):
                            st.write(f"• **{breach}**")
                        st.warning("Rekomendasi: Segera ganti kata sandi email target.")
                    else:
                        st.success("✅ Aman! Email ini tidak ditemukan dalam database kebocoran publik saat ini.")
                else:
                    st.error("Gagal terhubung ke database LeakCheck.")
            except Exception as e:
                st.error(f"Terjadi kesalahan koneksi: {str(e)}")

# -------------------------------------------------------------------------
# FITUR 4: GOOGLE DORKING ASSISTANT
# -------------------------------------------------------------------------
elif menu == "Google Dorking Assistant":
    st.header("🔏 Google Dorking Generator & Assistant")
    st.write("Buat kueri pencarian spesifik Google (Dork) untuk menemukan informasi sensitif.")
    
    domain_target = st.text_input("Masukkan Domain/Situs Target (Opsional):", placeholder="misal: targetperusahaan.com")
    keyword_target = st.text_input("Masukkan Kata Kunci / Nama Target:", placeholder="misal: \"rahasia\"")
    
    st.subheader("Pilih Jenis Informasi yang Ingin Dicari:")
    site_str = f"site:{domain_target} " if domain_target else ""
    
    dorks = {
        "📂 Cari File Dokumen Sensitif (PDF, DOCX, XLSX)": f"{site_str}filetype:pdf OR filetype:docx OR filetype:xlsx {keyword_target}",
        "🔑 Cari Halaman Login Admin / Panel Belakang": f"{site_str}inurl:login OR inurl:admin OR inurl:wp-login",
        "🗂️ Cari Direktori Folder Terbuka (Index of)": f"{site_str}intitle:\"index of\" \"parent directory\"",
        "📄 Cari File Konfigurasi / Backup database (SQL, ENV)": f"{site_str}filetype:sql OR filetype:env OR filetype:bak OR filetype:log",
        "📝 Cari Dokumen Berlabel Rahasia/Internal": f"{site_str}\"internal use only\" OR \"confidential\" {keyword_target}"
    }
    
    for label, dork_query in dorks.items():
        with st.expander(label):
            st.code(dork_query, language="text")
            encoded_query = urllib.parse.quote_plus(dork_query)
            google_url = f"https://www.google.com/search?q={encoded_query}"
            st.markdown(f"[🚀 Jalankan Dorking Langsung di Google]({google_url})")

# -------------------------------------------------------------------------
# FITUR 5: IP & DOMAIN GEOLOCATION
# -------------------------------------------------------------------------
elif menu == "IP & Domain Geolocation":
    st.header("🌐 IP Address & Domain Geolocation Tracker")
    st.write("Lacak lokasi fisik, negara, ISP, dan koordinat peta dari alamat IP atau nama Domain.")
    
    ip_input = st.text_input("Masukkan IP Address atau Domain (contoh: 8.8.8.8):", placeholder="8.8.8.8")
    
    if st.button("Lacak Lokasi IP"):
        if ip_input.strip() == "":
            st.warning("Silakan masukkan IP atau Domain terlebih dahulu.")
        else:
            st.info(f"Mengambil data intelijen untuk target: **{ip_input}**")
            url = f"http://ip-api.com/json/{ip_input}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
            
            try:
                response = requests.get(url, timeout=7)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        st.success("✅ Data Intelijen IP Berhasil Didapatkan!")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 🗺️ Data Geografis")
                            st.write(f"🌐 **IP Target:** {data.get('query')}")
                            st.write(f"🏳️ **Negara:** {data.get('country')} ({data.get('countryCode')})")
                            st.write(f"🏙️ **Kota/Wilayah:** {data.get('city')}, {data.get('regionName')}")
                        with col2:
                            st.markdown("### 🏢 Data Provider & Jaringan")
                            st.write(f"📡 **ISP:** {data.get('isp')}")
                            st.write(f"🏢 **Organisasi:** {data.get('org')}")
                            st.write(f"📍 **Koordinat:** Lat: {data.get('lat')}, Lon: {data.get('lon')}")
                        map_url = f"https://www.google.com/maps/search/?api=1&query={data.get('lat')},{data.get('lon')}"
                        st.markdown(f"[📍 Lihat Lokasi Persis di Google Maps]({map_url})")
                    else:
                        st.error(f"Gagal melacak target. Alasan: {data.get('message')}")
            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")

# -------------------------------------------------------------------------
# FITUR 6: PHONE NUMBER OSINT HELPER
# -------------------------------------------------------------------------
elif menu == "Phone Number OSINT Helper":
    st.header("📱 Phone Number OSINT Assistant")
    st.write("Analisis format nomor telepon internasional dan dapatkan tautan investigasi langsung.")
    
    phone_input = st.text_input("Masukkan Nomor Telepon Target (Gunakan Kode Negara):", placeholder="628123456789")
    
    if st.button("Analisis Nomor Telepon"):
        if phone_input.strip() == "" or not phone_input.isdigit():
            st.warning("Silakan masukkan nomor telepon yang valid.")
        else:
            st.success("Analisis Awal Selesai!")
            negara_prediksi = "Tidak Diketahui"
            if phone_input.startswith("62"): negara_prediksi = "Indonesia 🇮🇩"
            elif phone_input.startswith("1"): negara_prediksi = "Amerika Serikat / Kanada 🇺🇸🇨🇦"
                
            st.write(f"• **Nomor Input:** `+{phone_input}`")
            st.write(f"• **Prediksi Negara Asal:** {negara_prediksi}")
            
            truecaller_url = f"https://www.truecaller.com/search/global/{phone_input}"
            syncme_url = f"https://sync.me/search/?number={phone_input}"
            
            st.markdown(f"1. 👤 [Cari Nama Pemilik di **Truecaller Web**]({truecaller_url})")
            st.markdown(f"2. 🔄 [Cari Informasi Sosial Target di **Sync.ME**]({syncme_url})")

# -------------------------------------------------------------------------
# FITUR 7: SOCIAL MEDIA TARGET FINDER
# -------------------------------------------------------------------------
elif menu == "Social Media Target Finder":
    st.header("🕵️‍♂️ Social Media Target Finder")
    st.write("Buka formulir pencarian orang secara mendalam langsung ke platform media sosial target.")
    
    full_name = st.text_input("Masukkan Nama Lengkap Target:", placeholder="misal: John Doe")
    
    if full_name:
        encoded_name = urllib.parse.quote_plus(full_name)
        st.markdown("### 📌 Tautan Pencarian Langsung:")
        st.markdown(f"- 👥 [Cari Profil Orang di **Facebook**](https://www.facebook.com/search/top/?q={encoded_name})")
        st.markdown(f"- 💼 [Cari Profil Profesional di **LinkedIn**](https://www.linkedin.com/search/results/all/?keywords={encoded_name})")
        st.markdown(f"- 📸 [Cari Akun/Tag di **Instagram via Google**](https://www.google.com/search?q=site:instagram.com+%22{encoded_name}%22)")
        st.markdown(f"- 🎥 [Cari Video/Kreator di **TikTok**](https://www.tiktok.com/search?q={encoded_name})")

# -------------------------------------------------------------------------
# NEW FITUR 8: CORPORATE BACKGROUND CHECK (CEK PERUSAHAAN)
# -------------------------------------------------------------------------
elif menu == "Corporate Background Check":
    st.header("🏢 Corporate & Business Registry Identifier")
    st.write("Periksa apakah nama seseorang atau entitas bisnis terdaftar di registrasi perusahaan resmi (Kemenkumham/International Open Data).")
    
    target_name = st.text_input("Masukkan Nama Orang atau Nama Perusahaan Target:", placeholder="misal: PT Maju Jaya atau Nama Tokoh")
    
    if target_name:
        encoded_corp = urllib.parse.quote_plus(target_name)
        
        st.markdown("### 📋 Jalur Pintas Pemeriksaan Korporasi (Legal Open Data):")
        st.write("Gunakan tautan resmi di bawah untuk mencocokkan data kepemilikan saham atau status perusahaan:")
        
        # Link ke AHU (Kemenkumham RI), OpenCorporates (Terbesar di dunia), dan LEI (Legal Entity Identifier)
        ahu_url = f"https://ahu.go.id/pencarian/profil-perusahaan?search={encoded_corp}"
        opencorp_url = f"https://opencorporates.com/companies?q={encoded_corp}&utf8=%E2%9C%93"
        gleif_url = f"https://www.gleif.org/en/lei-data/global-lei-index/lei-search#!query={encoded_corp}"
        
        st.markdown(f"- 🇮🇩 [Cari Legalitas & Profil PT di **AHU Online Kemenkumham RI**]({ahu_url})")
        st.markdown(f"- 🌐 [Cari Afiliasi Direktur/Perusahaan Global di **OpenCorporates**]({opencorp_url})")
        st.markdown(f"- 🏢 [Cari Entitas Keuangan Legal di **GLEIF Global LEI Index**]({gleif_url})")
        st.markdown(f"- 🔍 [Pencarian Google Dork khusus dokumen Akta/Dokumen Perusahaan](https://www.google.com/search?q=%22{encoded_corp}%22+filetype:pdf+OR+inurl:sk-kemenkumham)")

# -------------------------------------------------------------------------
# NEW FITUR 9: LEGAL & COURT RECORD FINDER (CEK REKAM JEJAK HUKUM)
# -------------------------------------------------------------------------
elif menu == "Legal & Court Record Finder":
    st.header("⚖️ Public Legal & Court Record Finder")
    st.write("Lakukan background check terkait rekam jejak hukum publik, putusan pengadilan, sengketa, atau status perkara hukum seseorang.")
    
    legal_name = st.text_input("Masukkan Nama Lengkap Target (Gunakan tanda kutip untuk hasil presisi):", placeholder="misal: \"Nama Target\"")
    
    if legal_name:
        encoded_legal = urllib.parse.quote_plus(legal_name)
        
        st.markdown("### ⚖️ Repositori Data Putusan Hukum Publik:")
        st.write("Periksa keterlibatan kasus perdata/pidana target pada direktori keterbukaan informasi hukum berikut:")
        
        # Link Direktori Putusan Mahkamah Agung RI dan Mahkamah Konstitusi
        ma_url = f"https://putusan3.mahkamahagung.go.id/search.html?q={encoded_legal}"
        mk_url = f"https://www.mkri.id/index.php?page=web.Pencarian&search={encoded_legal}"
        
        st.markdown(f"- 🏛️ [Cari Rekam Kasus/Putusan Hukum di **Direktori Putusan Mahkamah Agung RI**]({ma_url})")
        st.markdown(f"- 📜 [Cari Sengketa/Perkara Konstitusi di **Mahkamah Konstitusi RI**]({mk_url})")
        st.markdown(f"- 📑 [Cari Dokumen Hukum Terbuka via Google Dorking](https://www.google.com/search?q=%22{encoded_legal}%22+filetype:pdf+AND+(%22putusan%22+OR+%22terdakwa%22+OR+%22gugatan%22))")

# -------------------------------------------------------------------------
# FITUR 10: HACKED PASSWORD CHECKER
# -------------------------------------------------------------------------
elif menu == "Hacked Password Checker":
    st.header("🦹‍♂️ Hacked Password Checker")
    st.write("Periksa secara anonim apakah sebuah password pernah bocor dalam kasus peretasan besar.")
    
    pwd_input = st.text_input("Masukkan Kata Sandi yang Ingin Dicek:", type="password")
    
    if st.button("Cek Keamanan Password"):
        if pwd_input.strip() == "":
            st.warning("Silakan masukkan kata sandi.")
        else:
            sha1_hash = hashlib.sha1(pwd_input.encode('utf-8')).hexdigest().upper()
            first5 = sha1_hash[:5]
            tail = sha1_hash[5:]
            url = f"https://api.pwnedpasswords.com/range/{first5}"
            
            try:
                response = requests.get(url, timeout=7)
                if response.status_code == 200:
                    hashes = (line.split(':') for line in response.text.splitlines())
                    match_count = 0
                    for h, count in hashes:
                        if h == tail:
                            match_count = int(count)
                            break
                    
                    if match_count > 0:
                        st.error(f"🚨 BERBAHAYA! Kata sandi ini telah bocor sebanyak **{match_count:,} kali**!")
                    else:
                        st.success("✅ Aman! Kata sandi ini belum pernah ditemukan dalam database peretasan.")
            except Exception as e:
                st.error(f"Terjadi kesalahan koneksi: {str(e)}")

# -------------------------------------------------------------------------
# FITUR 11: HASH TOOLS & IDENTIFIER
# -------------------------------------------------------------------------
elif menu == "Hash Tools & Identifier":
    st.header("🔐 Cryptographic Hash Generator & Identifier")
    st.write("Alat bantu forensik digital untuk mengidentifikasi jenis teks hash tidak dikenal.")
    
    tab1, tab2 = st.tabs(["🕵️ Identifikasi Hash", "⚙️ Generator Hash"])
    
    with tab1:
        hash_input = st.text_input("Tempel Teks Hash di Sini:").strip()
        if st.button("Identifikasi Jenis Hash"):
            if not hash_input: st.warning("Masukkan string hash.")
            else:
                is_hex = re.match(r"^[a-fA-F0-9]+$", hash_input)
                length = len(hash_input)
                if not is_hex: st.error("Teks input bukan format Hexadecimal.")
                else:
                    if length == 32: st.success("🎯 Kemungkinan Besar: **MD5**")
                    elif length == 40: st.success("🎯 Kemungkinan Besar: **SHA-1**")
                    elif length == 64: st.success("🎯 Kemungkinan Besar: **SHA-256**")
                    else: st.warning("Jenis hash tidak umum.")
                        
    with tab2:
        plain_text = st.text_area("Masukkan Teks Biasa:")
        algo = st.selectbox("Pilih Algoritma Hash:", ["MD5", "SHA-1", "SHA-256"])
        if st.button("Generate Hash"):
            if not plain_text: st.warning("Masukkan teks.")
            else:
                encoded_text = plain_text.encode('utf-8')
                if algo == "MD5": result = hashlib.md5(encoded_text).hexdigest()
                elif algo == "SHA-1": result = hashlib.sha1(encoded_text).hexdigest()
                elif algo == "SHA-256": result = hashlib.sha256(encoded_text).hexdigest()
                st.code(result, language="text")
