import io
import math
import time
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ReportLab Core & Flowables
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ReportLab Drawing & Spider (Radar) Chart Engine
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.spider import SpiderChart

# ==========================================
# 1. CONFIG & SESSION STATE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Executive Candidate Assessment",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ADMIN_PIN = "2273"  # PIN Rahasia Admin / HR

# Custom CSS Styling (Termasuk Fixed Floating Timer)
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Anti-Select / Anti Copy-Paste Text */
    body, div, p, span, h1, h2, h3, label {
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }
    input, textarea {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }

    /* Fixed Timer Canvas */
    iframe[title="st.iframe"] {
        position: fixed !important;
        top: 15px !important;
        right: 20px !important;
        z-index: 999999 !important;
        width: 220px !important;
        height: 60px !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TOTAL_TIME_SECONDS = 30 * 60  # Durasi: 30 Menit
MAX_COG_QUESTIONS = 15        # Target jumlah soal kognitif

if "test_started" not in st.session_state:
    st.session_state.test_started = False
if "test_finished" not in st.session_state:
    st.session_state.test_finished = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}
if "saved_to_gsheets" not in st.session_state:
    st.session_state.saved_to_gsheets = False

if "theta" not in st.session_state:
    st.session_state.theta = 0.0
if "cog_step" not in st.session_state:
    st.session_state.cog_step = 0
if "cog_history" not in st.session_state:
    st.session_state.cog_history = []
if "used_cog_ids" not in st.session_state:
    st.session_state.used_cog_ids = set()

if "sjt_responses" not in st.session_state:
    st.session_state.sjt_responses = {}

# ==========================================
# 2. BANK SOAL & PARAMETER PSIKOMETRI
# ==========================================

COGNITIVE_BANK = [
    {
        "id": "C01",
        "category": "Verbal Reasoning",
        "a": 1.2, "b": -1.5, "c": 0.25,
        "q": "OPOSIT : BERLAWANAN = SINKRON : ...",
        "opts": ["A. Serentak / Sejalan", "B. Terpisah", "C. Berurutan", "D. Acak"],
        "ans": "A. Serentak / Sejalan",
    },
    {
        "id": "C02",
        "category": "Numerical Reasoning",
        "a": 1.5, "b": -0.8, "c": 0.25,
        "q": "Satu tim efisiensi memotong konsumsi bahan bakar dari 800 liter menjadi 680 liter. Berapa persentase efisiensi energi yang dicapai?",
        "opts": ["A. 12%", "B. 15%", "C. 17.5%", "D. 20%"],
        "ans": "B. 15%",
    },
    {
        "id": "C03",
        "category": "Verbal Analogy",
        "a": 1.1, "b": -1.1, "c": 0.25,
        "q": "INFLASI : MATA UANG = DEPRESIASI : ...",
        "opts": ["A. Saham", "B. Aset Tetap", "C. Hutang", "D. Obligasi"],
        "ans": "B. Aset Tetap",
    },
    {
        "id": "C04",
        "category": "Numerical Series",
        "a": 1.3, "b": -0.6, "c": 0.25,
        "q": "Deret Angka: 3, 6, 12, 24, 48, [ ? ]. Angka berikutnya adalah:",
        "opts": ["A. 72", "B. 84", "C. 96", "D. 108"],
        "ans": "C. 96",
    },
    {
        "id": "C05",
        "category": "Abstract Logic",
        "a": 1.8, "b": 0.0, "c": 0.25,
        "q": "Semua analis data menguasai Python. Sebagian manajer produk tidak menguasai Python. Maka:",
        "opts": [
            "A. Semua manajer produk adalah analis data",
            "B. Sebagian manajer produk bukan analis data",
            "C. Analis data tidak ada yang menjadi manajer produk",
            "D. Tidak ada kesimpulan yang sah",
        ],
        "ans": "B. Sebagian manajer produk bukan analis data",
    },
    {
        "id": "C06",
        "category": "Numerical Reasoning",
        "a": 1.6, "b": 0.2, "c": 0.25,
        "q": "Perusahaan A dan B memiliki total anggaran Rp 450 Juta. Jika anggaran B adalah 25% lebih besar dari anggaran A, berapa besarnya anggaran A?",
        "opts": ["A. Rp 200 Juta", "B. Rp 225 Juta", "C. Rp 250 Juta", "D. Rp 275 Juta"],
        "ans": "A. Rp 200 Juta",
    },
    {
        "id": "C07",
        "category": "Verbal Logic",
        "a": 1.4, "b": -0.2, "c": 0.25,
        "q": "Jika semua proyek X bernilai tinggi dan sebagian proyek X berisiko tinggi, maka kesimpulan yang paling tepat adalah:",
        "opts": [
            "A. Semua proyek berisiko tinggi bernilai tinggi",
            "B. Sebagian proyek bernilai tinggi berisiko tinggi",
            "C. Tidak ada proyek berisiko yang bernilai tinggi",
            "D. Proyek bernilai rendah pasti tidak berisiko",
        ],
        "ans": "B. Sebagian proyek bernilai tinggi berisiko tinggi",
    },
    {
        "id": "C08",
        "category": "Data Interpretation",
        "a": 1.7, "b": 0.4, "c": 0.20,
        "q": "Penjualan Kuartal 1 adalah Rp 100 Juta. Jika naik 10% di Q2 dan naik lagi 20% di Q3, berapa total akumulasi nilai penjualan di Q3?",
        "opts": ["A. Rp 130 Juta", "B. Rp 132 Juta", "C. Rp 135 Juta", "D. Rp 140 Juta"],
        "ans": "B. Rp 132 Juta",
    },
    {
        "id": "C09",
        "category": "Numerical Matrix",
        "a": 2.0, "b": 0.8, "c": 0.20,
        "q": "Analisis deret kuadrat bilangan prima: 4, 9, 25, 49, 121, [ ? ]. Berapakah nilai variabel berikutnya?",
        "opts": ["A. 144", "B. 169", "C. 196", "D. 225"],
        "ans": "B. 169",
    },
    {
        "id": "C10",
        "category": "Complex Logic",
        "a": 1.9, "b": 1.0, "c": 0.20,
        "q": "Karyawan A lebih senior dari B tetapi junior dari C. D lebih senior dari C. Siapa yang paling junior di antara keempatnya?",
        "opts": ["A. Karyawan A", "B. Karyawan B", "C. Karyawan C", "D. Karyawan D"],
        "ans": "B. Karyawan B",
    },
    {
        "id": "C11",
        "category": "Numerical Optimization",
        "a": 2.1, "b": 1.2, "c": 0.20,
        "q": "Mesin A memproduksi 100 unit/jam dan Mesin B memproduksi 150 unit/jam. Jika keduanya digunakan bersamaan untuk membuat 1.000 unit dan Mesin B baru dinyalakan 1 jam setelah Mesin A beroperasi, berapa jam total waktu kerja Mesin A?",
        "opts": ["A. 3.6 Jam", "B. 4.0 Jam", "C. 4.6 Jam", "D. 5.0 Jam"],
        "ans": "C. 4.6 Jam",
    },
    {
        "id": "C12",
        "category": "Complex Deductive",
        "a": 2.2, "b": 1.5, "c": 0.20,
        "q": "Sistem X hanya aktif jika Y aktif dan Z non-aktif. Jika Z aktif saat Y aktif, maka kondisi Sistem X adalah:",
        "opts": ["A. Selalu Aktif", "B. Mutlak Non-Aktif", "C. Berjalan sebagian", "D. Tergantung variabel Y"],
        "ans": "B. Mutlak Non-Aktif",
    },
    {
        "id": "C13",
        "category": "Data Interpretation",
        "a": 2.1, "b": 1.8, "c": 0.20,
        "q": "Jika ROI total Proyek A adalah 18% dalam 3 tahun dan Proyek B adalah 12% dalam 2 tahun (compounded annually), proyek mana yang secara efektif menghasilkan laju pertumbuhan tahunan (CAGR) lebih tinggi?",
        "opts": ["A. Proyek A", "B. Proyek B", "C. Keduanya Setara", "D. Tidak cukup data"],
        "ans": "B. Proyek B",
    },
    {
        "id": "C14",
        "category": "Advanced Analytics",
        "a": 2.3, "b": 2.0, "c": 0.20,
        "q": "Sebuah eksperimen A/B testing menunjukkan tingkat konversi Kontrol (A) sebesar 4% dan Variasi (B) sebesar 5%. Berapa peningkatan relatif (relative uplift) dari variasi B dibanding A?",
        "opts": ["A. 1%", "B. 20%", "C. 25%", "D. 125%"],
        "ans": "C. 25%",
    },
    {
        "id": "C15",
        "category": "Strategic Logic",
        "a": 2.4, "b": 2.2, "c": 0.20,
        "q": "Jika implikasi (p ➔ q) bernilai Salah, dan disjungsi (q ∨ r) bernilai Benar, manakah urutan nilai kebenaran dari p, q, dan r yang benar secara berurutan?",
        "opts": ["A. Benar, Salah, Benar", "B. Benar, Benar, Salah", "C. Salah, Salah, Benar", "D. Benar, Salah, Salah"],
        "ans": "A. Benar, Salah, Benar",
    },
    {
        "id": "C16",
        "category": "Business Acumen & Valuation",
        "a": 2.2, "b": 1.4, "c": 0.20,
        "q": "Sebuah unit bisnis mencatatkan Revenue Rp 10 Miliar dengan EBITDA Margin 20%. Jika valuasi bisnis didasarkan pada multiple 8x EBITDA, berapa nilai estimasi Enterprise Value (EV) bisnis tersebut?",
        "opts": ["A. Rp 12 Miliar", "B. Rp 16 Miliar", "C. Rp 20 Miliar", "D. Rp 24 Miliar"],
        "ans": "B. Rp 16 Miliar",
    },
    {
        "id": "C17",
        "category": "Financial Decision Making",
        "a": 2.1, "b": 1.6, "c": 0.20,
        "q": "Proyek A membutuhkan belanja modal (CAPEX) awal Rp 500 Juta dan menghasilkan Arus Kas Masuk Netto Rp 150 Juta/tahun selama 4 tahun. Berapa Payback Period untuk investasi ini?",
        "opts": ["A. 2.8 Tahun", "B. 3.3 Tahun", "C. 3.5 Tahun", "D. 4.0 Tahun"],
        "ans": "B. 3.3 Tahun",
    },
    {
        "id": "C18",
        "category": "Strategic Logic & Game Theory",
        "a": 2.5, "b": 2.1, "c": 0.20,
        "q": "Jika Perusahaan A menurunkan harga produk sebesar 10%, kompetitor B dipastikan akan menurunkan harga sebesar 15%. Jika elastisitas permintaan pasar bersifat inelastis (< 1), apa dampak jangka panjang bagi total pendapatan industri?",
        "opts": [
            "A. Total pendapatan industri akan meningkat tajam",
            "B. Total pendapatan industri akan menurun",
            "C. Pendapatan industri tetap stabil tanpa perubahan",
            "D. Laba bersih kompetitor B akan berlipat ganda",
        ],
        "ans": "B. Total pendapatan industri akan menurun",
    },
    {
        "id": "C19",
        "category": "Data-Driven Risk Analytics",
        "a": 2.3, "b": 1.9, "c": 0.20,
        "q": "Dalam analisis risiko operasional, sebuah proyek memiliki 30% peluang kegagalan dengan potensi kerugian Rp 1 Miliar, dan 70% peluang sukses dengan potensi keuntungan Rp 500 Juta. Berapa nilai Harapan Moneter (Expected Monetary Value / EMV) dari proyek tersebut?",
        "opts": ["A. + Rp 50 Juta", "B. + Rp 150 Juta", "C. + Rp 200 Juta", "D. - Rp 50 Juta"],
        "ans": "A. + Rp 50 Juta",
    },
    {
        "id": "C20",
        "category": "Strategic Resource Allocation",
        "a": 2.0, "b": 1.1, "c": 0.20,
        "q": "Divisi X menghasilkan Margin Kontribusi 40% sedangkan Divisi Y menghasilkan Margin Kontribusi 25%. Jika kapasitas produksi terbatas, divisi mana yang secara ekonomis harus diprioritaskan untuk pemenuhan pesanan tambahan?",
        "opts": [
            "A. Divisi Y karena margin lebih rendah butuh volume",
            "B. Divisi X karena memberikan profitabilitas per unit lebih tinggi",
            "C. Keduanya diberi alokasi 50:50 demi keadilan",
            "D. Tidak bisa ditentukan tanpa data biaya tetap (fixed cost)",
        ],
        "ans": "B. Divisi X karena memberikan profitabilitas per unit lebih tinggi",
    },
]

SJT_BANK = [
    {
        "id": "SJT01",
        "dimension": "Agility & Crisis Management",
        "scenario": "Terjadi kegagalan sistem utama 1 jam sebelum presentasi krisis di depan Dewan Direksi. Anggota tim teknis Anda panik dan saling menyalahkan. Apa langkah pertama Anda?",
        "options": {
            "A": "Mengambil alih komunikasi langsung dengan Direksi untuk meminta penundaan jadwal.",
            "B": "Menghentikan perdebatan tim, membagi fokus pada pengerjaan rencana cadangan (Plan B) berbasis data manual.",
            "C": "Mendampingi teknis internal secara rinci untuk memicu perbaikan bug sistem saat itu juga.",
            "D": "Mencatat akar masalah internal untuk bahan evaluasi tindakan disipliner setelah rapat selesai.",
        },
        "scores": {
            "A": {"Leadership": 2, "Stress_Tolerance": 1, "Execution": 1},
            "B": {"Leadership": 4, "Stress_Tolerance": 4, "Execution": 5},
            "C": {"Leadership": 3, "Stress_Tolerance": 2, "Execution": 3},
            "D": {"Leadership": 1, "Stress_Tolerance": 1, "Execution": 1},
        },
    },
    {
        "id": "SJT02",
        "dimension": "Integrity & Strategic Decision",
        "scenario": "Anda menemukan bahwa strategi yang diusulkan atasan memiliki celah efisiensi anggaran dan berpotensi merugikan perusahaan dalam jangka panjang, meskipun menguntungkan target jangka pendek.",
        "options": {
            "A": "Menjalankan instruksi atasan secara profesional karena itu tanggung jawab pimpinan.",
            "B": "Menyusun dokumen analisis dampak teknis dan mengajukan alternatif solusi secara tertutup kepada atasan.",
            "C": "Menyampaikan keberatan secara terbuka saat rapat divisi agar rekan tim lain menyadari risikonya.",
            "D": "Mengubah pelaksanaan strategi di lapangan secara diam-diam agar risiko tidak terjadi.",
        },
        "scores": {
            "A": {"Leadership": 1, "Integrity": 1, "Strategic_Thinking": 1},
            "B": {"Leadership": 5, "Integrity": 5, "Strategic_Thinking": 5},
            "C": {"Leadership": 2, "Integrity": 3, "Strategic_Thinking": 2},
            "D": {"Leadership": 1, "Integrity": 1, "Strategic_Thinking": 2},
        },
    },
    {
        "id": "SJT03",
        "dimension": "Team Development & Delegation",
        "scenario": "Tim Anda gagal mencapai target kuartalan karena dua anggota senior menolak mengadopsi alur kerja digital baru. Bagaimana tindakan kepemimpinan Anda?",
        "options": {
            "A": "Memberikan peringatan tertulis tegas dan memindahkan mereka ke proyek non-strategis.",
            "B": "Mengadakan sesi coaching personal untuk memahami hambatan mereka serta menetapkan periode transisi intensif.",
            "C": "Mengambil alih seluruh pekerjaan teknis mereka agar target divisi tetap tercapai.",
            "D": "Membiarkan mereka bekerja dengan cara lama selama kualitas hasil tetap terjaga.",
        },
        "scores": {
            "A": {"Leadership": 2, "Execution": 3, "Stress_Tolerance": 2},
            "B": {"Leadership": 5, "Execution": 4, "Stress_Tolerance": 4},
            "C": {"Leadership": 1, "Execution": 2, "Stress_Tolerance": 1},
            "D": {"Leadership": 1, "Execution": 1, "Stress_Tolerance": 1},
        },
    },
    {
        "id": "SJT04",
        "dimension": "Conflict Resolution",
        "scenario": "Dua manajer divisi di bawah kepemimpinan Anda berselisih sengit terkait alokasi sumber daya anggaran yang terbatas, hingga menghambat koordinasi tim.",
        "options": {
            "A": "Membuat keputusan sepihak membagi anggaran 50:50 tanpa negosiasi lebih lanjut.",
            "B": "Memfasilitasi diskusi berbasis data indikator kinerja dan tujuan strategis perusahaan bersama kedua manajer.",
            "C": "Menyerahkan keputusan pembagian anggaran kepada manajemen puncak (Direksi).",
            "D": "Memberikan anggaran penuh kepada divisi yang mencetak pendapatan terbesar.",
        },
        "scores": {
            "A": {"Leadership": 2, "Strategic_Thinking": 2, "Integrity": 3},
            "B": {"Leadership": 5, "Strategic_Thinking": 5, "Integrity": 4},
            "C": {"Leadership": 1, "Strategic_Thinking": 1, "Integrity": 2},
            "D": {"Leadership": 2, "Strategic_Thinking": 3, "Integrity": 1},
        },
    },
    {
        "id": "SJT05",
        "dimension": "Change Management",
        "scenario": "Perusahaan memutuskan melakukan restrukturisasi organisasi. Banyak anggota tim Anda merasa cemas dan produktivitas menurun drastis.",
        "options": {
            "A": "Mengadakan balai warga (townhall) internal divisi secara transparan untuk menyampaikan visi perubahan dan membuka ruang tanya jawab.",
            "B": "Meminta tim tetap fokus bekerja dan mengabaikan rumor hingga perubahan resmi berlaku.",
            "C": "Menjanjikan kepada tim bahwa tidak akan ada pemutusan hubungan kerja agar mereka tenang.",
            "D": "Fokus pada penyelesaian target pribadi dan menyerahkan komunikasi restrukturisasi kepada HRD.",
        },
        "scores": {
            "A": {"Leadership": 5, "Stress_Tolerance": 5, "Strategic_Thinking": 4},
            "B": {"Leadership": 2, "Stress_Tolerance": 2, "Strategic_Thinking": 2},
            "C": {"Leadership": 1, "Stress_Tolerance": 1, "Integrity": 1},
            "D": {"Leadership": 1, "Stress_Tolerance": 1, "Strategic_Thinking": 1},
        },
    },
    {
        "id": "SJT06",
        "dimension": "Stakeholder Management",
        "scenario": "Klien utama menuntut penambahan fitur baru di luar ruang lingkup proyek (scope creep) tanpa mau menambah biaya dan waktu pengerjaan.",
        "options": {
            "A": "Menolak mentah-mentah permintaan klien agar tim tidak mengalami burnout.",
            "B": "Menerima semua permintaan klien demi menjaga hubungan baik walau tim harus lembur ekstrem.",
            "C": "Melakukan negosiasi berbasis analisis dampak (impact analysis) dan menawarkan opsi penyesuaian prioritas fitur.",
            "D": "Mengalihkan negosiasi sepenuhnya kepada tim legal perusahaan.",
        },
        "scores": {
            "A": {"Leadership": 2, "Execution": 2, "Strategic_Thinking": 2},
            "B": {"Leadership": 1, "Execution": 2, "Stress_Tolerance": 1},
            "C": {"Leadership": 5, "Execution": 5, "Strategic_Thinking": 5},
            "D": {"Leadership": 2, "Execution": 1, "Strategic_Thinking": 2},
        },
    },
    {
        "id": "SJT07",
        "dimension": "Resource Optimization",
        "scenario": "Di tengah beban kerja puncak, salah satu anggota kunci di tim Anda mendadak mengajukan izin sakit jangka panjang.",
        "options": {
            "A": "Meminta anggota tim lain mengambil alih seluruh tugas rekan yang sakit tanpa penyesuaian tenggat.",
            "B": "Mengevaluasi ulang prioritas proyek, melakukan redistribusi tugas, dan mengajukan bantuan tenaga kontraktor temporary.",
            "C": "Menunda seluruh tenggat waktu proyek sampai anggota kunci tersebut sembuh dan kembali bekerja.",
            "D": "Mengerjakan sendiri seluruh sisa beban kerja anggota yang sakit.",
        },
        "scores": {
            "A": {"Leadership": 2, "Stress_Tolerance": 1, "Execution": 3},
            "B": {"Leadership": 5, "Stress_Tolerance": 5, "Execution": 5},
            "C": {"Leadership": 1, "Stress_Tolerance": 2, "Execution": 1},
            "D": {"Leadership": 2, "Stress_Tolerance": 2, "Execution": 2},
        },
    },
    {
        "id": "SJT08",
        "dimension": "Ethics & Compliance",
        "scenario": "Anda mendapati laporan keuangan proyek menunjukkan ketidaksesuaian kecil akibat kelalaian tim, namun belum terdeteksi oleh auditor eksternal.",
        "options": {
            "A": "Mengabaikannya selama nominalnya relatif kecil dan tidak menimbulkan kerugian besar.",
            "B": "Melakukan koreksi internal secara transparan, melaporkan temuan ke bagian audit internal, serta menyusun tindakan pencegahan.",
            "C": "Menutupi ketidaksesuaian tersebut dengan merevisi catatan keuangan kuartal berikutnya.",
            "D": "Menimpakan kesalahan sepenuhnya kepada anggota tim yang lalai.",
        },
        "scores": {
            "A": {"Leadership": 1, "Integrity": 1, "Strategic_Thinking": 1},
            "B": {"Leadership": 5, "Integrity": 5, "Strategic_Thinking": 4},
            "C": {"Leadership": 1, "Integrity": 1, "Strategic_Thinking": 1},
            "D": {"Leadership": 1, "Integrity": 1, "Strategic_Thinking": 1},
        },
    },
]

# ==========================================
# 3. HELPER FUNCTIONS & ALGORITMA IRT (PRECISION FIX)
# ==========================================

def irt_3pl(theta, a, b, c):
    """Fungsi Kerapatan Probabilitas 3PL IRT"""
    val = -a * (theta - b)
    val = max(min(val, 50), -50)
    return c + (1.0 - c) / (1.0 + math.exp(val))

def update_theta_mle(theta_current, history):
    """
    Perhitungan Estimasi Kemampuan (Ability Theta) Menggunakan Maximum Likelihood Estimation (MLE)
    Rumus turunan dp/dtheta telah diperbaiki secara presisi menurut standar psikometri IRT 3PL.
    """
    if not history:
        return theta_current

    num, den, eps = 0.0, 0.0, 1e-9
    for item in history:
        a, b, c = item["a"], item["b"], item["c"]
        u = item["response"]
        p = irt_3pl(theta_current, a, b, c)
        p = max(min(p, 0.999), 0.001)

        # Turunan Resmi 3PL IRT
        p_star = (p - c) / (1.0 - c + eps)
        dp = a * (1.0 - c) * p_star * (1.0 - p_star)
        
        num += dp * (u - p) / (p * (1.0 - p) + eps)
        den += (dp ** 2) / (p * (1.0 - p) + eps)

    if den <= eps:
        return theta_current

    delta = num / den
    delta = max(min(delta, 0.75), -0.75) # Bounding delta agar konvergensi stabil
    new_theta = theta_current + delta
    return max(min(new_theta, 3.0), -3.0)

def get_next_question(theta_current, used_ids):
    """Mencari Soal dengan Informasi Item Maksimum (Fisher Information)"""
    best_q = None
    max_info = -1.0
    for q in COGNITIVE_BANK:
        if q["id"] in used_ids:
            continue
        p = irt_3pl(theta_current, q["a"], q["b"], q["c"])
        info = (
            (q["a"] ** 2)
            * ((1 - p) / (p + 1e-9))
            * (((p - q["c"]) / (1 - q["c"] + 1e-9)) ** 2)
        )
        if info > max_info:
            max_info = info
            best_q = q
    return best_q

def render_timer():
    """Timer Client-Side JavaScript (Fixed & Non-blocking)"""
    if not st.session_state.start_time:
        return
    elapsed = time.time() - st.session_state.start_time
    remaining_time = max(0, int(TOTAL_TIME_SECONDS - elapsed))

    timer_code = """
    <div style="
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px 12px;
        color: #38BDF8;
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 14px;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    ">
        ⏱️ &nbsp; <b>Sisa Waktu:</b> &nbsp;
        <span id="js_timer" style="
            background-color: #0F172A;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 16px;
            color: #F43F5E;
            font-weight: bold;
        ">--:--</span>
    </div>

    <script>
        let timeLeft = TIME_LEFT_PLACEHOLDER;
        const timerDisplay = document.getElementById('js_timer');

        function updateTimer() {
            let minutes = Math.floor(timeLeft / 60);
            let seconds = timeLeft % 60;

            minutes = minutes < 10 ? '0' + minutes : minutes;
            seconds = seconds < 10 ? '0' + seconds : seconds;

            timerDisplay.textContent = minutes + ':' + seconds;

            if (timeLeft <= 0) {
                timerDisplay.textContent = "00:00 - HABIS!";
                clearInterval(timerInterval);
            } else {
                timeLeft--;
            }
        }

        updateTimer();
        const timerInterval = setInterval(updateTimer, 1000);
    </script>
    """.replace("TIME_LEFT_PLACEHOLDER", str(remaining_time))

    st.components.v1.html(timer_code, height=50)

def save_to_google_sheets(cand, theta, iq_equivalent, fit_status, comp_scores):
    """Sinkronisasi data ke Google Sheets dengan Safe Exception Handling"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)

        new_row = pd.DataFrame(
            [
                {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Nama": cand.get("name", "N/A"),
                    "Email": cand.get("email", "N/A"),
                    "Level_Jabatan": cand.get("level", "N/A"),
                    "Posisi": cand.get("position", "N/A"),
                    "Pengalaman": cand.get("exp", 0),
                    "Skor_Theta": round(theta, 2),
                    "Estimasi_IQ": iq_equivalent,
                    "Status_Kesesuaian": fit_status,
                    "Leadership": comp_scores.get("Leadership", 0),
                    "Stress_Tolerance": comp_scores.get("Stress_Tolerance", 0),
                    "Execution": comp_scores.get("Execution", 0),
                    "Integrity": comp_scores.get("Integrity", 0),
                    "Strategic_Thinking": comp_scores.get("Strategic_Thinking", 0),
                }
            ]
        )

        if existing_data is not None and not existing_data.empty:
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        else:
            updated_df = new_row

        conn.update(data=updated_df)
        st.session_state.saved_to_gsheets = True
        return True
    except Exception as e:
        st.toast("ℹ️ Data tersimpan secara lokal (Google Sheets offline).")
        return False

# ==========================================
# GENERATE RADAR DRAWING (NATIVE REPORTLAB)
# ==========================================
def draw_reportlab_radar(labels, values):
    d = Drawing(220, 180)
    chart = SpiderChart()
    chart.x = 25
    chart.y = 20
    chart.width = 170
    chart.height = 140
    chart.data = [values]
    chart.labels = labels
    
    # Custom Styling
    chart.strands[0].strokeColor = colors.HexColor('#0F52BA')
    chart.strands[0].fillColor = colors.HexColor('#0F52BA33')
    chart.strands[0].strokeWidth = 2
    
    chart.strandLabels.fontName = 'Helvetica'
    chart.strandLabels.fontSize = 7
    chart.strandLabels.fillColor = colors.HexColor('#333333')
    
    chart.spokes.strokeColor = colors.HexColor('#CBD5E1')
    chart.spokes.strokeWidth = 0.5
    
    d.add(chart)
    return d

# ==========================================
# GENERATE PDF REPORT ENGINE
# ==========================================
def generate_candidate_pdf(cand_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F52BA'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=8,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#333333')
    )

    bold_label_style = ParagraphStyle(
        'BoldLabel',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1E293B')
    )

    story = []

    # 1. Header Dokumen
    story.append(Paragraph("Executive Candidate Assessment Report", title_style))
    story.append(Paragraph("Standardized Adaptive Testing & Behavioral Competency Evaluation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F52BA'), spaceAfter=10))

    # 2. Data Diri Kandidat
    story.append(Paragraph("📌 Data Diri Kandidat", h2_style))
    info_table_data = [
        [Paragraph("Nama Lengkap:", bold_label_style), Paragraph(str(cand_data.get('Nama', '-')), body_style),
         Paragraph("Level Jabatan:", bold_label_style), Paragraph(str(cand_data.get('Level_Jabatan', '-')), body_style)],
        [Paragraph("Email Profesional:", bold_label_style), Paragraph(str(cand_data.get('Email', '-')), body_style),
         Paragraph("Posisi / Divisi:", bold_label_style), Paragraph(str(cand_data.get('Posisi', '-')), body_style)],
        [Paragraph("Pengalaman Kerja:", bold_label_style), Paragraph(f"{cand_data.get('Pengalaman', 0)} Tahun", body_style),
         Paragraph("Waktu Ujian:", bold_label_style), Paragraph(str(cand_data.get('Timestamp', '-')), body_style)],
    ]
    t_info = Table(info_table_data, colWidths=[110, 150, 100, 160])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 8))

    # 3. Kognitif Metrics
    story.append(Paragraph("🧠 Evaluasi Kognitif (IRT)", h2_style))
    theta_val = float(cand_data.get('Skor_Theta', 0))
    iq_val = str(cand_data.get('Estimasi_IQ', '-'))
    fit_val = str(cand_data.get('Status_Kesesuaian', '-'))

    metrics_table_data = [
        [Paragraph("Skor Theta (Ability)", bold_label_style), Paragraph("Estimasi IQ", bold_label_style), Paragraph("Status Kesesuaian", bold_label_style)],
        [Paragraph(f"<font size=12 color='#0F52BA'><b>{theta_val:+.2f}</b></font>", body_style),
         Paragraph(f"<font size=12 color='#0F52BA'><b>IQ ~{iq_val}</b></font>", body_style),
         Paragraph(f"<font size=12 color='#0F52BA'><b>{fit_val}</b></font>", body_style)]
    ]
    t_metrics = Table(metrics_table_data, colWidths=[173, 173, 174])
    t_metrics.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 8))

    # 4. Generate Radar Chart Vektor (Native ReportLab Engine)
    labels = ["Leadership", "Stress Tol.", "Execution", "Integrity", "Strategic Think."]
    raw_vals = [
        float(cand_data.get('Leadership', 0)),
        float(cand_data.get('Stress_Tolerance', 0)),
        float(cand_data.get('Execution', 0)),
        float(cand_data.get('Integrity', 0)),
        float(cand_data.get('Strategic_Thinking', 0))
    ]
    radar_drawing = draw_reportlab_radar(labels, raw_vals)

    # 5. Tabel SJT Samping-Sampingan dengan Radar Vektor
    story.append(Paragraph("📊 Profil Kompetensi Perilaku (SJT)", h2_style))
    
    sjt_table_data = [
        [Paragraph("Dimensi Kompetensi", bold_label_style), Paragraph("Skor", bold_label_style)],
        [Paragraph("Leadership & Team Management", body_style), Paragraph(str(cand_data.get('Leadership', 0)), body_style)],
        [Paragraph("Stress Tolerance & Agility", body_style), Paragraph(str(cand_data.get('Stress_Tolerance', 0)), body_style)],
        [Paragraph("Execution & Drive for Results", body_style), Paragraph(str(cand_data.get('Execution', 0)), body_style)],
        [Paragraph("Integrity & Ethics", body_style), Paragraph(str(cand_data.get('Integrity', 0)), body_style)],
        [Paragraph("Strategic Thinking", body_style), Paragraph(str(cand_data.get('Strategic_Thinking', 0)), body_style)],
    ]
    t_sjt = Table(sjt_table_data, colWidths=[200, 60])
    t_sjt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    side_by_side_table = Table([[t_sjt, radar_drawing]], colWidths=[270, 250])
    side_by_side_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(side_by_side_table)
    story.append(Spacer(1, 10))

    # 6. Kesimpulan & Rekomendasi HR
    story.append(Paragraph("📋 Kesimpulan & Rekomendasi HR", h2_style))
    if theta_val > 0.8:
        recom_text = "<b>HIGH RECOMMENDED (Sangat Direkomendasikan):</b> Memiliki kapasitas kognitif tingkat tinggi serta pemikiran strategis yang sangat adaptif."
    elif theta_val >= -0.2:
        recom_text = "<b>RECOMMENDED WITH CONSIDERATION (Direkomendasikan dengan Pertimbangan):</b> Memiliki kapabilitas analisis yang memadai untuk lingkup kerja operasional standar."
    else:
        recom_text = "<b>NOT RECOMMENDED (Kurang Direkomendasikan):</b> Kapasitas penalaran kognitif berada di bawah kualifikasi minimum."

    story.append(Paragraph(recom_text, body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<font size=7 color='#666666'>* Catatan Kerahasiaan: Laporan ini dihasilkan secara otomatis menggunakan sistem pemodelan psikometri Item Response Theory (IRT) 3PL dan bersifat rahasia.</font>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. USER INTERFACE FLOW
# ==========================================

# Guard jika waktu 30 menit telah habis
if st.session_state.test_started and not st.session_state.test_finished:
    elapsed_time = time.time() - st.session_state.start_time
    if elapsed_time >= TOTAL_TIME_SECONDS:
        st.session_state.test_finished = True
        st.rerun()

st.title("🛡️ System Asesmen General Kandidat")
st.caption("Standardized Adaptive Testing & Behavioral Competency Evaluation System")

# --- PHASE 1: REGISTRASI & MODE ADMIN DI HALAMAN AWAL ---
if not st.session_state.test_started and not st.session_state.test_finished:
    
    # 🔐 AKSES KONTROL REKAP LAPORAN (UNTUK ADMIN/HR DI HALAMAN AWAL)
    with st.expander("🔐 Akses Laporan Hasil (Khusus Admin / HR)", expanded=False):
        admin_input = st.text_input("Masukkan PIN Admin/HR:", type="password", key="admin_pin_main")
        if admin_input == ADMIN_PIN:
            st.success("🔓 Akses Diberikan! Berikut Rekap Database Hasil Asesmen Kandidat:")
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_results = conn.read(ttl=0)
                if df_results is not None and not df_results.empty:
                    st.dataframe(df_results, use_container_width=True)

                    st.markdown("---")
                    st.subheader("🔍 Detail & Summary Penilaian Kandidat")

                    df_results["Select_Label"] = (
                        df_results["Nama"].astype(str)
                        + " | "
                        + df_results["Email"].astype(str)
                        + " ("
                        + df_results["Timestamp"].astype(str)
                        + ")"
                    )

                    selected_candidate_label = st.selectbox(
                        "Pilih Kandidat untuk Melihat Summary Penilaian:",
                        options=df_results["Select_Label"].tolist(),
                        index=len(df_results) - 1,
                    )

                    cand_data = df_results[
                        df_results["Select_Label"] == selected_candidate_label
                    ].iloc[0]

                    st.markdown("### 📄 Executive Summary Laporan Kandidat")

                    pdf_bytes = generate_candidate_pdf(cand_data)
                    cand_name_clean = str(cand_data.get('Nama', 'Kandidat')).replace(' ', '_')
                    
                    st.download_button(
                        label="📥 Download Laporan PDF Resmi",
                        data=pdf_bytes,
                        file_name=f"Executive_Summary_{cand_name_clean}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )

                    st.write(f"**Nama Lengkap:** {cand_data.get('Nama', '-')}")
                    st.write(f"**Email:** {cand_data.get('Email', '-')}")
                    st.write(f"**Level Jabatan:** {cand_data.get('Level_Jabatan', '-')}")
                    st.write(f"**Posisi/Divisi:** {cand_data.get('Posisi', '-')}")
                    st.write(f"**Pengalaman:** {cand_data.get('Pengalaman', 0)} Tahun")
                    st.write(f"**Waktu Ujian:** {cand_data.get('Timestamp', '-')}")

                    st.markdown("---")

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(
                            "Skor Kognitif Laten (Theta)",
                            f"{float(cand_data.get('Skor_Theta', 0)):+.2f}",
                        )
                    with c2:
                        st.metric(
                            "Estimasi IQ", f"IQ ~{cand_data.get('Estimasi_IQ', '-')}"
                        )
                    with c3:
                        st.metric(
                            "Status Kesesuaian",
                            f"{cand_data.get('Status_Kesesuaian', '-')}",
                        )

                    st.markdown("---")
                    st.subheader("📊 Profil Radar Kompetensi Perilaku (SJT)")

                    comp_dimensions = [
                        "Leadership",
                        "Stress_Tolerance",
                        "Execution",
                        "Integrity",
                        "Strategic_Thinking",
                    ]
                    comp_values = [
                        float(cand_data.get(dim, 0)) for dim in comp_dimensions
                    ]

                    comp_dimensions.append(comp_dimensions[0])
                    comp_values.append(comp_values[0])

                    max_radar_val = max(max(comp_values), 10)

                    fig_cand = go.Figure(
                        data=go.Scatterpolar(
                            r=comp_values, 
                            theta=comp_dimensions, 
                            fill="toself",
                            line=dict(color="#0F52BA"),
                            fillcolor="rgba(15, 82, 186, 0.2)"
                        )
                    )
                    fig_cand.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        polar=dict(
                            bgcolor="rgba(0,0,0,0)",
                            radialaxis=dict(visible=True, range=[0, max_radar_val], color="#888888"),
                            angularaxis=dict(color="#888888")
                        ),
                        showlegend=False,
                        margin=dict(l=30, r=30, t=20, b=20),
                        height=350
                    )

                    rc1, rc2 = st.columns([1, 1])
                    with rc1:
                        st.plotly_chart(fig_cand, use_container_width=True)

                    with rc2:
                        st.markdown("### Kesimpulan & Rekomendasi HR")
                        theta_val = float(cand_data.get("Skor_Theta", 0))
                        if theta_val > 0.8:
                            st.write(
                                "🟢 **Kandidat Sangat Direkomendasikan (High Potential).** Memiliki kemampuan penalaran kognitif tingkat tinggi dan adaptif terhadap tantangan strategis."
                            )
                        elif theta_val >= -0.2:
                            st.write(
                                "🟡 **Kandidat Direkomendasikan dengan Pertimbangan.** Memiliki kapabilitas analisis yang memadai untuk lingkup kerja operasional standar."
                            )
                        else:
                            st.write(
                                "🔴 **Kurang Direkomendasikan.** Kapasitas penalaran kognitif berada di bawah standar kualifikasi minimum."
                            )

                        st.markdown("**Catatan Kerahasiaan:**")
                        st.caption(
                            "Hasil tes ini bersifat rahasia dan dikalkulasi secara otomatis menggunakan pemodelan Item Response Theory (IRT)."
                        )
                else:
                    st.info("Belum ada data kandidat yang tersimpan di Google Sheets.")

            except Exception as e:
                st.info("💡 Mode Offline Active. Data lokal belum terhubung dengan Google Sheets secrets.")
        elif admin_input != "":
            st.error("❌ PIN Salah. Akses Ditolak.")

    st.markdown("---")

    st.subheader("Formulir Data Diri Kandidat")
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            fullname = st.text_input("Nama Lengkap*")
            email = st.text_input("Email Profesional*")
            level = st.selectbox(
                "Level Jabatan*",
                [
                    "Staf / Officer",
                    "Supervisor / Team Lead",
                    "Manager / Head",
                    "Executive / General Management",
                ],
            )
        with col2:
            position = st.selectbox(
                "Posisi / Divisi Dilamar*",
                [
                    "Operations, HR & Admin",
                    "Software Engineering & IT",
                    "Data & Analytics",
                    "Finance, Accounting & Strategy",
                    "Sales & Marketing",
                    "General Management / Business Unit",
                ],
            )
            experience = st.slider("Pengalaman Kerja (Tahun)", 0, 20, 3)

        st.info(
            "📌 **Instruksi Ujian:**\n"
            "- Durasi total tes adalah **30 Menit**.\n"
            "- Terdiri dari 2 Bagian: **Penalaran Kognitif Adaptif (15 Soal)** dan **Skenario Kepemimpinan / SJT (8 Soal)**.\n"
            "- Tingkat kesulitan soal disesuaikan secara otomatis berdasarkan jawaban Anda."
        )

        submit = st.form_submit_button("Mulai Sesi Asesmen")
        if submit:
            if fullname and email:
                st.session_state.candidate_info = {
                    "name": fullname,
                    "email": email,
                    "level": level,
                    "position": position,
                    "exp": experience,
                }
                st.session_state.test_started = True
                st.session_state.start_time = time.time()
                st.rerun()
            else:
                st.error("Mohon lengkapi semua kolom wajib.")

# --- PHASE 2: PENGERJAAN TES ---
elif st.session_state.test_started and not st.session_state.test_finished:
    render_timer()

    total_expected_steps = MAX_COG_QUESTIONS + len(SJT_BANK)
    current_step = st.session_state.cog_step + len(st.session_state.sjt_responses)
    st.progress(min(current_step / total_expected_steps, 1.0))

    # BAGIAN A: TES KOGNITIF ADAPTIF
    if st.session_state.cog_step < MAX_COG_QUESTIONS:
        next_q = get_next_question(st.session_state.theta, st.session_state.used_cog_ids)
        if next_q:
            st.session_state.used_cog_ids.add(next_q["id"])
            st.markdown(
                f"### Bagian 1: Penalaran Kognitif (Soal {st.session_state.cog_step + 1} dari {MAX_COG_QUESTIONS})"
            )
            st.caption(f"Kategori Domain: **{next_q['category']}**")

            with st.container():
                st.markdown(f"**{next_q['q']}**")
                user_ans = st.radio(
                    "Pilih Jawaban Anda:",
                    next_q["opts"],
                    index=None,
                    key=f"cog_radio_{next_q['id']}",
                )

                if st.button("Simpan & Lanjutkan »", key=f"btn_{next_q['id']}"):
                    if user_ans is None:
                        st.warning("⚠️ Harap pilih salah satu jawaban terlebih dahulu.")
                    else:
                        is_correct = 1 if user_ans == next_q["ans"] else 0
                        st.session_state.cog_history.append(
                            {
                                "a": next_q["a"],
                                "b": next_q["b"],
                                "c": next_q["c"],
                                "response": is_correct,
                            }
                        )
                        st.session_state.theta = update_theta_mle(
                            st.session_state.theta, st.session_state.cog_history
                        )
                        st.session_state.cog_step += 1
                        st.rerun()
        else:
            st.session_state.cog_step = MAX_COG_QUESTIONS
            st.rerun()

    # BAGIAN B: SJT KEPRIBADIAN
    else:
        st.markdown("### Bagian 2: Skenario Situasional & Kepemimpinan (SJT)")
        sjt_index = len(st.session_state.sjt_responses)

        if sjt_index < len(SJT_BANK):
            q_sjt = SJT_BANK[sjt_index]
            st.caption(
                f"Soal {sjt_index + 1} dari {len(SJT_BANK)} | Dimensi Kompetensi: **{q_sjt['dimension']}**"
            )
            st.markdown(f"**{q_sjt['scenario']}**")

            sjt_choice = st.radio(
                "Pilih Tindakan Efektif Menurut Anda:",
                list(q_sjt["options"].values()),
                index=None,
                key=f"sjt_radio_{q_sjt['id']}",
            )

            if st.button("Kirim Jawaban SJT »", key=f"sjt_btn_{q_sjt['id']}"):
                if sjt_choice is None:
                    st.warning("⚠️ Harap pilih salah satu opsi tindakan.")
                else:
                    selected_key = [
                        k for k, v in q_sjt["options"].items() if v == sjt_choice
                    ][0]
                    st.session_state.sjt_responses[q_sjt["id"]] = q_sjt["scores"][selected_key]
                    st.rerun()
        else:
            st.success(
                "Seluruh bagian tes telah diisi. Klik tombol di bawah untuk mengevaluasi hasil."
            )
            if st.button("🟢 SELESAIKAN DAN EVALUASI HASIL"):
                st.session_state.test_finished = True
                st.rerun()

# --- PHASE 3: TERIMA KASIH & SELESAI ---
elif st.session_state.test_finished:
    cand = st.session_state.candidate_info

    iq_equivalent = int(100 + (st.session_state.theta * 15))
    iq_equivalent = max(70, min(145, iq_equivalent))
    fit_status = "Tinggi (Recommended)" if st.session_state.theta > 0.5 else "Moderat"

    comp_scores = {
        "Leadership": 0,
        "Stress_Tolerance": 0,
        "Execution": 0,
        "Integrity": 0,
        "Strategic_Thinking": 0,
    }
    for resp in st.session_state.sjt_responses.values():
        for k, v in resp.items():
            comp_scores[k] = comp_scores.get(k, 0) + v

    # Simpan otomatis ke Google Sheets
    if not st.session_state.saved_to_gsheets:
        save_to_google_sheets(
            cand,
            st.session_state.theta,
            iq_equivalent,
            fit_status,
            comp_scores,
        )

    st.balloons()
    
    # TAMPILAN UNTUK KANDIDAT
    st.success("✅ **Asesmen Berhasil Diselesaikan!**")
    st.info(
        f"Terima kasih **{cand.get('name', 'Kandidat')}**, jawaban Anda telah berhasil direkam dan dikirim ke tim HR. "
        "Hasil tes bersifat rahasia dan akan dievaluasi secara internal. Anda dipersilakan untuk menutup halaman ini."
    )

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888888; font-size: 13px; font-weight: 500;'>"
    "Created by Iqbal Mantam"
    "</div>",
    unsafe_allow_html=True,
)
