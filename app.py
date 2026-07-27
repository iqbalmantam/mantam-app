import math
import time
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIG & SESSION STATE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Executive Candidate Assessment",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CUSTOM CSS: HILANGKAN HEADER & ANTI COPY-PASTE ---
st.markdown(
    """
    <style>
    /* 1. Sembunyikan Streamlit Header & Footer */
    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0%;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Anti Copy-Paste: Disable Text Selection */
    body, div, p, span, h1, h2, h3, label {
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }
    
    /* Allow typing in inputs */
    input, textarea {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TOTAL_TIME_SECONDS = 30 * 60  # Durasi: 30 Menit

# Inisialisasi Session State Utama
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

# Session State untuk Tes Kognitif (IRT / CAT)
if "theta" not in st.session_state:
    st.session_state.theta = 0.0  # Ability level awal (Z-score)
if "cog_step" not in st.session_state:
    st.session_state.cog_step = 0
if "cog_history" not in st.session_state:
    st.session_state.cog_history = []
if "used_cog_ids" not in st.session_state:
    st.session_state.used_cog_ids = set()

# Session State untuk Tes SJT
if "sjt_responses" not in st.session_state:
    st.session_state.sjt_responses = {}

# ==========================================
# 2. BANK SOAL & PARAMETER PSIKOMETRI
# ==========================================

COGNITIVE_BANK = [
    {
        "id": "C01",
        "category": "Verbal Reasoning",
        "a": 1.2,
        "b": -1.5,
        "c": 0.25,
        "q": "OPOSIT : BERLAWANAN = SINKRON : ...",
        "opts": [
            "A. Serentak / Sejalan",
            "B. Terpisah",
            "C. Berurutan",
            "D. Acak",
        ],
        "ans": "A. Serentak / Sejalan",
    },
    {
        "id": "C02",
        "category": "Numerical Reasoning",
        "a": 1.5,
        "b": -0.8,
        "c": 0.25,
        "q": "Satu tim efisiensi memotong konsumsi bahan bakar dari 800 liter menjadi 680 liter. Berapa persentase efisiensi energi yang dicapai?",
        "opts": ["A. 12%", "B. 15%", "C. 17.5%", "D. 20%"],
        "ans": "B. 15%",
    },
    {
        "id": "C03",
        "category": "Abstract Logic",
        "a": 1.8,
        "b": 0.0,
        "c": 0.25,
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
        "id": "C04",
        "category": "Numerical Matrix",
        "a": 2.0,
        "b": 0.8,
        "c": 0.20,
        "q": "Analisis deret performa operasional: 4, 9, 25, 49, 121, [ ? ]. Berapakah nilai variabel berikutnya?",
        "opts": ["A. 144", "B. 169", "C. 196", "D. 225"],
        "ans": "B. 169",
    },
    {
        "id": "C05",
        "category": "Complex Deductive",
        "a": 2.2,
        "b": 1.6,
        "c": 0.20,
        "q": "Sistem X hanya aktif jika Y aktif dan Z non-aktif. Jika Z aktif saat Y aktif, maka kondisi Sistem X adalah:",
        "opts": [
            "A. Selalu Aktif",
            "B. Mutlak Non-Aktif",
            "C. Berjalan sebagian",
            "D. Tergantung variabel Y",
        ],
        "ans": "B. Mutlak Non-Aktif",
    },
    {
        "id": "C06",
        "category": "Data Interpretation",
        "a": 2.1,
        "b": 2.2,
        "c": 0.20,
        "q": "Jika ROI proyek A adalah 18% dalam 3 tahun dan proyek B adalah 12% dalam 2 tahun (compounded annually), proyek mana yang secara efektif menghasilkan laju pertumbuhan tahunan (CAGR) lebih tinggi?",
        "opts": [
            "A. Proyek A",
            "B. Proyek B",
            "C. Keduanya Setara",
            "D. Tidak cukup data",
        ],
        "ans": "B. Proyek B",
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
]

# ==========================================
# 3. HELPER FUNCTIONS & ALGORITMA
# ==========================================


def irt_3pl(theta, a, b, c):
    """Probabilitas IRT 3-Parameter Logistic dengan safeguard numerik"""
    val = -a * (theta - b)
    val = max(min(val, 50), -50)  # Safeguard math.exp overflow
    return c + (1 - c) / (1 + math.exp(val))


def update_theta_mle(theta_current, history):
    """Pembaruan Estimasi Theta (MLE) yang stabil secara numerik"""
    if not history:
        return theta_current

    num, den, eps = 0.0, 0.0, 1e-9

    for item in history:
        a, b, c = item["a"], item["b"], item["c"]
        u = item["response"]
        p = irt_3pl(theta_current, a, b, c)
        p = max(min(p, 0.999), 0.001)

        val = -a * (theta_current - b)
        val = max(min(val, 50), -50)
        exp_val = math.exp(val)

        dp = a * (1 - c) * exp_val / ((1 + exp_val) ** 2)
        num += dp * (u - p) / (p * (1 - p) + eps)
        den += (dp**2) / (p * (1 - p) + eps)

    if den == 0:
        return theta_current

    delta = num / den
    delta = max(min(delta, 0.75), -0.75)
    new_theta = theta_current + delta
    return max(min(new_theta, 3.0), -3.0)


def get_next_question(theta_current, used_ids):
    """Cari soal dengan Maximum Item Information pada Theta saat ini"""
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
    """Timer Mundur 30 Menit yang Tampil di Atas Halaman Utama"""
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, TOTAL_TIME_SECONDS - int(elapsed))

    mins, secs = divmod(remaining, 60)
    timer_str = f"{mins:02d}:{secs:02d}"

    if remaining <= 0 and not st.session_state.test_finished:
        st.session_state.test_finished = True
        st.rerun()

    bg_color = "#FFEBEB" if remaining < 300 else "#EBF3FF"
    text_color = "#D32F2F" if remaining < 300 else "#0F52BA"
    border_color = "#FFCDD2" if remaining < 300 else "#BBDEFB"

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border: 2px solid {border_color};
            padding: 12px 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <span style="font-size: 16px; font-weight: 600; color: #333333;">⏱️ SISA WAKTU UJIAN: </span>
            <span style="font-size: 24px; font-weight: 800; color: {text_color}; font-family: monospace;">{timer_str}</span>
            {"<span style='color: #D32F2F; font-weight: bold; margin-left: 10px;'>(⚠️ Kurang dari 5 menit!)</span>" if remaining < 300 else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def save_to_google_sheets(cand, theta, iq_equivalent, fit_status, comp_scores):
    """Kirim Hasil Otomatis ke Google Sheets dengan Safe Error Handling"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)

        new_row = pd.DataFrame(
            [
                {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Nama": cand.get("name", ""),
                    "Email": cand.get("email", ""),
                    "Posisi": cand.get("position", ""),
                    "Pengalaman": cand.get("exp", 0),
                    "Skor_Theta": round(theta, 2),
                    "Estimasi_IQ": iq_equivalent,
                    "Status_Kesesuaian": fit_status,
                    "Leadership": comp_scores.get("Leadership", 0),
                    "Stress_Tolerance": comp_scores.get("Stress_Tolerance", 0),
                    "Execution": comp_scores.get("Execution", 0),
                    "Integrity": comp_scores.get("Integrity", 0),
                    "Strategic_Thinking": comp_scores.get(
                        "Strategic_Thinking", 0
                    ),
                }
            ]
        )

        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.session_state.saved_to_gsheets = True
        return True
    except Exception as e:
        st.warning(f"⚠️ Data tersimpan secara lokal, namun gagal sync ke Google Sheets: {e}")
        return False


# ==========================================
# 4. USER INTERFACE FLOW
# ==========================================

st.title("🛡️ System Asesmen General Kandidat")
st.caption(
    "Standardized Adaptive Testing & Behavioral Competency Evaluation System"
)

# --- PHASE 1: REGISTRASI ---
if not st.session_state.test_started and not st.session_state.test_finished:
    st.subheader("Formulir Data Diri Kandidat")
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            fullname = st.text_input("Nama Lengkap*")
            email = st.text_input("Email Profesional*")
        with col2:
            position = st.selectbox(
                "Posisi Dilamar*",
                [
                    "General Management",
                    "Software Engineer",
                    "Data & Analytics",
                    "Operations & Logistics",
                    "Finance & Strategy",
                ],
            )
            experience = st.slider("Pengalaman Kerja (Tahun)", 0, 20, 3)

        st.info(
            "📌 **Instruksi Ujian:**\n"
            "- Durasi total tes adalah **30 Menit**.\n"
            "- Terdiri dari 2 Bagian: **Penalaran Kognitif Adaptif** dan **Skenario Kepemimpinan (SJT)**.\n"
            "- Tingkat kesulitan soal disesuaikan secara otomatis berdasarkan performa Anda."
        )

        submit = st.form_submit_button("Mulai Sesi Asesmen")
        if submit:
            if fullname and email:
                st.session_state.candidate_info = {
                    "name": fullname,
                    "email": email,
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

    total_expected_steps = len(COGNITIVE_BANK) + len(SJT_BANK)
    current_step = st.session_state.cog_step + len(
        st.session_state.sjt_responses
    )
    st.progress(min(current_step / total_expected_steps, 1.0))

    next_q = get_next_question(
        st.session_state.theta, st.session_state.used_cog_ids
    )

    # BAGIAN A: TES KOGNITIF ADAPTIF
    if next_q and st.session_state.cog_step < len(COGNITIVE_BANK):
        st.markdown(
            f"### Bagian 1: Penalaran Kognitif (Soal {st.session_state.cog_step + 1})"
        )
        st.caption(f"Kategori Domain: **{next_q['category']}**")

        with st.container():
            st.markdown(f"**{next_q['q']}**")
            user_ans = st.radio(
                "Pilih Jawaban Anda:",
                next_q["opts"],
                key=f"cog_radio_{next_q['id']}",
            )

            if st.button("Simpan & Lanjutkan »", key=f"btn_{next_q['id']}"):
                is_correct = 1 if user_ans == next_q["ans"] else 0
                st.session_state.used_cog_ids.add(next_q["id"])
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

    # BAGIAN B: SJT KEPRIBADIAN
    else:
        st.markdown("### Bagian 2: Skenario Situasional & Kepemimpinan (SJT)")
        sjt_index = len(st.session_state.sjt_responses)

        if sjt_index < len(SJT_BANK):
            q_sjt = SJT_BANK[sjt_index]
            st.caption(f"Dimensi Kompetensi: **{q_sjt['dimension']}**")
            st.markdown(f"**{q_sjt['scenario']}**")

            sjt_choice = st.radio(
                "Pilih Tindakan Efektif Menurut Anda:",
                list(q_sjt["options"].values()),
                key=f"sjt_radio_{q_sjt['id']}",
            )

            if st.button("Kirim Jawaban SJT »", key=f"sjt_btn_{q_sjt['id']}"):
                selected_key = [
                    k for k, v in q_sjt["options"].items() if v == sjt_choice
                ][0]
                st.session_state.sjt_responses[q_sjt["id"]] = q_sjt["scores"][
                    selected_key
                ]
                st.rerun()
        else:
            st.success("Seluruh bagian tes telah diisi. Klik tombol di bawah untuk mengevaluasi hasil.")
            if st.button("🟢 SELESAIKAN DAN EVALUASI HASIL"):
                st.session_state.test_finished = True
                st.rerun()

# --- PHASE 3: REPORT & DASHBOARD HASIL ---
elif st.session_state.test_finished:
    cand = st.session_state.candidate_info

    # Hitung Skor Akhir
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

    # Simpan Otomatis ke Google Sheets
    if not st.session_state.saved_to_gsheets:
        save_to_google_sheets(
            cand,
            st.session_state.theta,
            iq_equivalent,
            fit_status,
            comp_scores,
        )

    st.balloons()
    st.success(
        "✅ Asesmen Berhasil Diselesaikan! Data telah diverifikasi."
    )

    st.header(f"Laporan Asesmen Psikologi: {cand.get('name', 'Kandidat')}")
    st.caption(
        f"Posisi: {cand.get('position')} | Pengalaman: {cand.get('exp')} Tahun | Email: {cand.get('email')}"
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Skor Kognitif Laten (Theta Z-Score)",
            f"{st.session_state.theta:+.2f}",
        )
    with col2:
        st.metric("Estimasi Kapasitas Intelektual", f"IQ ~{iq_equivalent}")
    with col3:
        st.metric("Kesesuaian Kualifikasi", fit_status)

    st.markdown("---")

    # RADAR CHART COMPETENCIES
    st.subheader("📊 Profil Kompetensi Perilaku (SJT Assessment)")

    categories = list(comp_scores.keys())
    values = list(comp_scores.values())

    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(
        data=go.Scatterpolar(r=values, theta=categories, fill="toself")
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=False,
    )

    r_col1, r_col2 = st.columns([1, 1])
    with r_col1:
        st.plotly_chart(fig, use_container_width=True)

    with r_col2:
        st.markdown("### Kesimpulan & Rekomendasi HR")
        if st.session_state.theta > 0.8:
            st.write(
                "🟢 **Kandidat Sangat Direkomendasikan (High Potential).** Memiliki kemampuan penalaran kognitif tingkat tinggi dan adaptif terhadap tantangan strategis."
            )
        elif st.session_state.theta >= -0.2:
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
