import streamlit as st
import sqlite3
from datetime import datetime
from google import genai
import plotly.graph_objects as go
import json
import os
from streamlit_drawable_canvas import st_canvas

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Şampiyonun LGS Karargâhı")

DOGRU_SIFRE = "1234"
GEMINI_API_KEY = "AQ.Ab8RN6ISfgTLZu44H--l4mSQMq_uxk-TJanYkpHn346OXLQEeg"

# Profil Resmi CSS Ayarı
st.markdown("""
<style>
[data-testid="stImage"] img {
    border-radius: 50%;
    border: 4px solid #4CAF50;
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.3);
    object-fit: cover;
}
</style>
""", unsafe_allow_html=True)

TUM_DERSLER = ["Türkçe", "Matematik", "Fen Bilimleri", "İnkılap Tarihi", "İngilizce", "Din Kültürü"]

# Veri Tabanı Bağlantıları
def veri_getir(query, params=()):
    conn = sqlite3.connect('lgs_takip.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data

def veri_kaydet(query, params=()):
    conn = sqlite3.connect('lgs_takip.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# Garantili ve Hızlı Yapay Zeka Soru Üretici
def ai_soru_paketi_hazirla(ders, adet=5):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        Sen Türkiye MEB müfredat uzmanı bir LGS öğretmenisin.
        Sadece Türkiye MEB 7. Sınıf {ders} müfredat kazanımlarına bağlı kalarak {adet} adet LGS tarzı yeni nesil soru hazırla.
        Soru metinleri anlaşılır olsun. 'cozum' kısmı maksimum 2-3 cümle ile samimi ve emojili olsun.
        Çıktıyı sadece şu JSON liste formatında ver, başka hiçbir açıklama yazma:
        [
          {{"konu": "Konu Adı", "soru": "Soru Metni", "A": "A şıkkı", "B": "B şıkkı", "C": "C şıkkı", "D": "D şıkkı", "cevap": "Doğru Şık (A, B, C veya D)", "cozum": "Çözüm açıklaması."}}
        ]
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()
        return json.loads(text)
    except:
        return None

# Bellek Yönetimi
if "soru_paketi" not in st.session_state: st.session_state.soru_paketi = {}
if "aktif_index" not in st.session_state: st.session_state.aktif_index = {}
if "kontrol_edildi" not in st.session_state: st.session_state.kontrol_edildi = {}
if "veli_secilen_ders" not in st.session_state: st.session_state.veli_secilen_ders = TUM_DERSLER[0]
if "show_popup_ders" not in st.session_state: st.session_state.show_popup_ders = None

# 🎯 Odaklanmış Pop-up Çözüm Penceresi
@st.dialog("🎯 LGS Çözüm Karargâhı", width="large")
def pop_up_pencere(ders, bugun):
    havuz = st.session_state.soru_paketi.get(ders, [])
    idx = st.session_state.aktif_index.get(ders, 0)
    
    if idx < len(havuz):
        soru = havuz[idx]
        
        col_sol, col_orta, col_sag = st.columns([1, 4, 1])
        with col_sol:
            if idx > 0:
                if st.button("⬅️ Önceki", key=f"p_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] -= 1
                    st.rerun()
        with col_orta:
            st.info(f"📌 Soru {idx + 1} / {len(havuz)} | Konu: {soru.get('konu', '')}")
        with col_sag:
            if idx < len(havuz) - 1:
                if st.button("Sonraki ➡️", key=f"n_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] += 1
                    st.rerun()

        st.divider()
        
        col_soru, col_cizim = st.columns([1, 1])
        with col_soru:
            st.markdown(f"### {soru.get('soru', '')}")
            secenek = st.radio(
                "Cevabını İşaretle:", 
                [f"A) {soru.get('A', '')}", f"B) {soru.get('B', '')}", f"C) {soru.get('C', '')}", f"D) {soru.get('D', '')}"], 
                index=None, key=f"r_{ders}_{idx}"
            )
            
            is_checked = st.session_state.kontrol_edildi[ders][idx]
            if not is_checked:
                if st.button("Cevabı Kontrol Et 🚀", key=f"c_{ders}_{idx}", type="primary"):
                    if secenek is None:
                        st.warning("⚠️ Lütfen önce bir şık işaretle!")
                    else:
                        st.session_state.kontrol_edildi[ders][idx] = True
                        if secenek[0] == soru.get('cevap', ''):
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, ders, soru.get('konu', '')))
                        else:
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, ders, soru.get('konu', ''), "Hata"))
                        st.rerun()
            else:
                st.subheader("💡 Yapay Zeka Çözüm Özeti")
                if secenek and secenek[0] == soru.get('cevap', ''):
                    st.success(f"🎉 Doğru! {soru.get('cozum', '')}")
                else:
                    st.error(f"❌ Yanlış. Doğru Seçenek: {soru.get('cevap', '')}")
                    st.warning(soru.get('cozum', ''))
                
                st.divider()
                if idx < len(havuz) - 1:
                    if st.button("Sıradaki Soruya Geç ➡️", key=f"go_{ders}_{idx}", use_container_width=True):
                        st.session_state.aktif_index[ders] += 1
                        st.rerun()
                else:
                    st.balloons()
                    st.success("🏆 Harika! Bugünkü tüm görevlerini tamamladın!")
                    if st.button("🏁 Çalışmayı Bitir ve Raporla", key=f"fin_{ders}"):
                        st.session_state.show_popup_ders = None
                        st.rerun()
        
        with col_cizim:
            st.caption("✏️ Karalama ve İşlem Alanı:")
            firca = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"s_{ders}_{idx}")
            st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=firca, stroke_color="#000000", background_color="#eeeeee", height=360, drawing_mode="freedraw", key=f"can_{ders}_{idx}")

# --- ÜST BAŞLIK ALANI ---
col_logo, col_baslik = st.columns([1, 7])
with col_logo:
    if os.path.exists("profil.jpg"): st.image("profil.jpg", width=120)
    else: st.info("📷 Profil")
with col_baslik:
    st.title("🏆 Şampiyonun LGS Karargâhı 🚀")
    st.caption("Hedeflerine adım adım, pes etmeden!")
st.divider()

panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)
st.divider()

# --- VELİ PANELİ ---
if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Analiz Raporları")
    if not st.session_state.get("veli_giris_yapildi"):
        girilen_sifre = st.text_input("Şifre:", type="password")
        if st.button("Giriş Yap"):
            if girilen_sifre == DOGRU_SIFRE: st.session_state.veli_giris_yapildi = True; st.rerun()
            else: st.error("❌ Hatalı şifre!")
    else:
        tab1, tab2 = st.tabs(["📊 Performans Grafiği", "🎯 Hedef Belirle"])
        with tab1:
            hedefler_data = veri_getir("SELECT ders, SUM(hedef_soru) FROM hedefler GROUP BY ders")
            cozumler_data = veri_getir("SELECT ders, SUM(dogru_sayisi), SUM(yanlis_sayisi) FROM cozumler GROUP BY ders")
            grafik_haritasi = {h[0]: {"hedef": h[1], "dogru": 0, "yanlis": 0} for h in hedefler_data}
            for c in cozumler_data:
                if c[0] in grafik_haritasi: grafik_haritasi[c[0]]["dogru"] = c[1]; grafik_haritasi[c[0]]["yanlis"] = c[2]
            if grafik_haritasi:
                dersler_list = list(grafik_haritasi.keys())
                fig = go.Figure(data=[
                    go.Bar(name='Hedef', x=dersler_list, y=[grafik_haritasi[d]["hedef"] for d in dersler_list], marker_color='#1f77b4'),
                    go.Bar(name='Doğru', x=dersler_list, y=[grafik_haritasi[d]["dogru"] for d in dersler_list], marker_color='rgb(34, 139, 34)'),
                    go.Bar(name='Yanlış', x=dersler_list, y=[grafik_haritasi[d]["yanlis"] for d in dersler_list], marker_color='rgb(178, 34, 34)')
                ])
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Veri bulunamadı.")
        with tab2:
            tarih = st.date_input("Tarih", datetime.now()).strftime('%Y-%m-%d')
            cols_veli = st.columns(3)
            for i, d in enumerate(TUM_DERSLER):
                if cols_veli[i % 3].button(d, key=f"v_{d}", type="primary" if st.session_state.veli_secilen_ders == d else "secondary", use_container_width=True):
                    st.session_state.veli_secilen_ders = d; st.rerun()
            hedef_soru = st.number_input(f"{st.session_state.veli_secilen_ders} Hedefi", min_value=1, value=5)
            if st.button("Hedefi Kaydet"):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, st.session_state.veli_secilen_ders, hedef_soru))
                st.success("Kaydedildi!")

# --- ÖĞRENCİ PANELİ ---
else:
    bugun = datetime.now().strftime('%Y-%m-%d')
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    hedef_adetler = {h[0]: h[1] for h in bugunun_hedefleri}
    
    st.markdown("### 📚 Bugünkü Görevlerin (Çözmek İstediğin Kutuya Tıkla)")
    cols_ogr = st.columns(3)
    
    for i, d in enumerate(TUM_DERSLER):
        is_active = d in hedef_adetler
        if cols_ogr[i % 3].button(d, key=f"o_{d}", disabled=not is_active, type="primary" if is_active else "secondary", use_container_width=True):
            if d not in st.session_state.soru_paketi:
                with st.spinner("Senin için sorular hazırlanıyor... ⏳"):
                    sorular = ai_soru_paketi_hazirla(d, adet=hedef_adetler[d])
                    if sorular:
                        st.session_state.soru_paketi[d] = sorular
                        st.session_state.aktif_index[d] = 0
                        st.session_state.kontrol_edildi[d] = [False] * len(sorular)
                        st.session_state.show_popup_ders = d
                        st.rerun()
                    else:
                        st.error("⚠️ Kısa süreli bir bağlantı sorunu oldu. Lütfen kutucuğa bir kez daha tıkla Polat.")
            else:
                st.session_state.show_popup_ders = d
                st.rerun()

    # Aktif pop-up'ı tetikleme alanı
    if st.session_state.show_popup_ders:
        pop_up_pencere(st.session_state.show_popup_ders, bugun)
        
    if not hedef_adetler:
        st.success("🎉 Bugünlük hedefin yok. Dinlenebilirsin!")