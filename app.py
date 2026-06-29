import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import google.generativeai as genai
import plotly.graph_objects as go
import os
import random
from streamlit_drawable_canvas import st_canvas

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Şampiyonun LGS Karargâhı")

DOGRU_SIFRE = "1234"

# 🔑 En Son Aldığın %100 Doğru ve Güncel API Anahtarı Tanımlandı
API_ANAHTARI = "AQ.Ab8RN6L0_nT0dDIPbU28RhNfchFLJz04UDbzA1vCJNbl6gYdow"
genai.configure(api_key=API_ANAHTARI)

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

# Veritabanı Modülleri
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

# 🧠 HAFIZALI VE YANLIŞ ODAKLI YAPAY ZEKA MOTORU
def ai_soru_uret_ve_temizle(ders, adet=5):
    # Poyraz Efe'nin geçmiş yanlışlarını hafızaya alıyoruz
    yanlislar = veri_getir("SELECT DISTINCT konu_adi FROM cozumler WHERE ders = ? AND yanlis_sayisi > 0", (ders,))
    yanlis_konular = [y[0] for y in yanlislar if y[0]]
    
    konu_puanlama_ve_stresi = ""
    if yanlis_konular:
        konu_puanlama_ve_stresi = f"\nÖNEMLİ: Öğrenci daha önce şu konularda yanlış yapmıştır: {', '.join(yanlis_konular)}. Bu konuları pekiştirecek benzer tarzda mantık muhakeme sorularına ağırlık ver."

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Sen Türkiye MEB müfredatına tamamen hakim uzman bir LGS öğretmenisin.
        7. Sınıf {ders} müfredatına uygun, mantık muhakeme odaklı, LGS tarzı yeni nesil tam {adet} adet özgün soru hazırla. {konu_puanlama_ve_stresi}
        
        Her sorunun başlangıcına mutlaka 'SORU_BASLA' ifadesini koy.
        Format kurallarına kesinlikle uy:
        
        SORU_BASLA
        KONU: [Konu Adı]
        SORU: [Soru Metni]
        A: [A Seçeneği]
        B: [B Seçeneği]
        C: [C Seçeneği]
        D: [D Seçeneği]
        CEVAP: [Sadece A, B, C veya D harfi]
        COZUM: [Çözüm ve püf noktası açıklaması]
        """
        response = model.generate_content(prompt)
        metin = response.text
        
        bloklar = metin.split("SORU_BASLA")
        sonuclar = []
        
        for blok in bloklar:
            if "SORU:" in blok and "CEVAP:" in blok:
                satirlar = [s.strip() for s in blok.strip().split("\n") if s.strip()]
                obj = {"konu": "Genel Tekrar", "soru": "Soru yüklenemedi.", "A": "", "B": "", "C": "", "D": "", "cevap": "A", "cozum": "Açıklama yok."}
                for s in satirlar:
                    if s.upper().startswith("KONU:"): obj["konu"] = s[5:].strip()
                    elif s.upper().startswith("SORU:"): obj["soru"] = s[5:].strip()
                    elif s.upper().startswith("A:"): obj["A"] = s[2:].strip()
                    elif s.upper().startswith("B:"): obj["B"] = s[2:].strip()
                    elif s.upper().startswith("C:"): obj["C"] = s[2:].strip()
                    elif s.upper().startswith("D:"): obj["D"] = s[2:].strip()
                    elif s.upper().startswith("CEVAP:"): obj["cevap"] = s[6:].strip().upper()
                    elif s.upper().startswith("COZUM:"): obj["cozum"] = s[6:].strip()
                if obj["soru"] != "Soru yüklenemedi.":
                    sonuclar.append(obj)
                    
        return sonuclar[:adet] if len(sonuclar) >= adet else sonuclar
    except Exception as e:
        return [{"konu": "Bağlantı", "soru": f"Yapay zeka motoru çalıştırılırken bir pürüz oluştu: {str(e)}", "A": "-", "B": "-", "C": "-", "D": "-", "cevap": "A", "cozum": "Bağlantı kontrolü."}]

# State Yönetimi
if "soru_paketi" not in st.session_state: st.session_state.soru_paketi = {}
if "aktif_index" not in st.session_state: st.session_state.aktif_index = {}
if "kontrol_edildi" not in st.session_state: st.session_state.kontrol_edildi = {}
if "veli_secilen_ders" not in st.session_state: st.session_state.veli_secilen_ders = TUM_DERSLER[0]
if "show_popup_ders" not in st.session_state: st.session_state.show_popup_ders = None

# ==========================================
# 🎯 ÖZEL POP-UP DIALOG MODÜLÜ
# ==========================================
@st.dialog("🎯 LGS Çözüm Karargâhı", width="large")
def pop_up_pencere(ders, bugun):
    havuz = st.session_state.soru_paketi.get(ders, [])
    idx = st.session_state.aktif_index.get(ders, 0)
    
    if idx < len(havuz):
        soru = havuz[idx]
        
        col_sol, col_orta, col_sag = st.columns([1, 4, 1])
        with col_sol:
            if idx > 0:
                if st.button("⬅️ Önceki Soru", key=f"p_pop_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] -= 1
                    st.rerun()
        with col_orta:
            st.info(f"📌 Soru {idx + 1} / {len(havuz)} | Ders: {ders} | Konu: {soru.get('konu')}")
        with col_sag:
            if idx < len(havuz) - 1:
                if st.button("Sonraki Soru ➡️", key=f"n_pop_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] += 1
                    st.rerun()

        st.divider()
        
        col_s, col_c = st.columns([1, 1])
        with col_s:
            st.markdown(f"#### {soru.get('soru')}")
            secenek = st.radio(
                "Cevabını Seç:",
                [f"A) {soru.get('A')}", f"B) {soru.get('B')}", f"C) {soru.get('C')}", f"D) {soru.get('D')}"],
                index=None, key=f"r_pop_{ders}_{idx}"
            )
            
            is_checked = st.session_state.kontrol_edildi[ders][idx]
            if not is_checked:
                if st.button("Cevabı Kontrol Et 🚀", key=f"chk_pop_{ders}_{idx}", type="primary", use_container_width=True):
                    if secenek is None:
                        st.warning("Lütfen bir şık seçin!")
                    else:
                        st.session_state.kontrol_edildi[ders][idx] = True
                        s_harf = secenek[0]
                        dogru_harf = soru.get('cevap', 'A').strip().upper()
                        
                        if s_harf == dogru_harf:
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, ders, soru.get('konu')))
                        else:
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, ders, soru.get('konu'), f"Hata: {s_harf} seçildi"))
                        st.rerun()
            else:
                st.markdown("---")
                s_harf = secenek[0] if secenek else ""
                dogru_harf = soru.get('cevap', 'A').strip().upper()
                if s_harf == dogru_harf:
                    st.success(f"🎉 Doğru! {soru.get('cozum')}")
                else:
                    st.error(f"❌ Yanlış! Doğru Cevap: {dogru_harf}")
                    st.warning(soru.get('cozum', 'Açıklama mevcut değil.'))
                
                st.write("")
                if idx < len(havuz) - 1:
                    if st.button("Sıradaki Soruya Geç ➡️", key=f"next_pop_{ders}_{idx}", use_container_width=True):
                        st.session_state.aktif_index[ders] += 1
                        st.rerun()
                else:
                    st.balloons()
                    st.success("🏆 Harika! Bu dersin tüm sorularını başarıyla bitirdin!")
                    if st.button("🏁 Raporla ve Kapat", key=f"close_pop_{ders}", type="primary", use_container_width=True):
                        st.session_state.show_popup_ders = None
                        st.rerun()
        with col_c:
            st.caption("✏️ Karalama Tahtası:")
            firca = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"br_pop_{ders}_{idx}")
            st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=firca, stroke_color="#000000", background_color="#eeeeee", height=380, drawing_mode="freedraw", key=f"can_pop_{ders}_{idx}")

# --- BAŞLIK ALANI ---
col_logo, col_baslik = st.columns([1, 7])
with col_logo:
    if os.path.exists("profil.jpg"): st.image("profil.jpg", width=120)
    else: st.info("📷 Profil")
with col_baslik:
    st.title("🏆 Şampiyonun LGS Karargâhı 🚀")
    st.caption("Poyraz Efe'nin LGS Çalışma Paneli")
st.divider()

panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)
st.divider()

# ==========================================
# 👨‍🏫 VELİ / YÖNETİCİ PANELİ
# ==========================================
if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Analiz Raporları")
    st.session_state.show_popup_ders = None
    
    if not st.session_state.get("veli_giris_yapildi"):
        girilen_sifre = st.text_input("Giriş Şifresi:", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if girilen_sifre == DOGRU_SIFRE: 
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else: st.error("❌ Hatalı şifre!")
    else:
        if st.button("🔒 Paneli Kilitle"):
            st.session_state.veli_giris_yapildi = False
            st.rerun()
            
        tab1, tab2, tab3 = st.tabs(["📊 Genel Durum Grafiği", "📆 Günlük Ödev / Hedef Takibi", "🎯 Yeni Hedef Belirle"])
        
        with tab1:
            st.subheader("📈 Ders Bazlı Kümülatif Başarı Grafiği")
            hedefler_data = veri_getir("SELECT ders, SUM(hedef_soru) FROM hedefler GROUP BY ders")
            cozumler_data = veri_getir("SELECT ders, SUM(dogru_sayisi), SUM(yanlis_sayisi) FROM cozumler GROUP BY ders")
            grafik_haritasi = {h[0]: {"hedef": h[1], "dogru": 0, "yanlis": 0} for h in hedefler_data}
            for c in cozumler_data:
                if c[0] in grafik_haritasi: 
                    grafik_haritasi[c[0]]["dogru"] = c[1]
                    grafik_haritasi[c[0]]["yanlis"] = c[2]
            if grafik_haritasi:
                dersler_list = list(grafik_haritasi.keys())
                fig = go.Figure(data=[
                    go.Bar(name='Toplam Verilen Hedef', x=dersler_list, y=[grafik_haritasi[d]["hedef"] for d in dersler_list], marker_color='#1f77b4'),
                    go.Bar(name='Doğru Çözülen', x=dersler_list, y=[grafik_haritasi[d]["dogru"] for d in dersler_list], marker_color='green'),
                    go.Bar(name='Yanlış Çözülen', x=dersler_list, y=[grafik_haritasi[d]["yanlis"] for d in dersler_list], marker_color='red')
                ])
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Henüz kümülatif veri bulunamadı.")
            
        with tab2:
            st.subheader("📆 Gün Bazlı Ödev Tamamlama Analizi")
            secilen_tarih = st.date_input("Takip Etmek İstediğiniz Günü Seçin:", datetime.now() - timedelta(days=1))
            tarih_str = secilen_tarih.strftime('%Y-%m-%d')
            
            gunluk_hedefler = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (tarih_str,))
            gunluk_cozumler = veri_getir("SELECT ders, SUM(toplam_cozulen), SUM(dogru_sayisi) FROM cozumler WHERE tarih = ? GROUP BY ders", (tarih_str,))
            
            hedef_dict = {gh[0]: gh[1] for gh in gunluk_hedefler}
            cozum_dict = {gc[0]: {"cozulen": gc[1], "dogru": gc[2]} for gc in gunluk_cozumler}
            
            st.write(f"### 🗓️ {secilen_tarih.strftime('%d.%m.%Y')} Tarihli Rapor")
            
            if list(hedef_dict.keys()):
                for d in TUM_DERSLER:
                    if d in hedef_dict:
                        v_hedef = hedef_dict[d]
                        c_durum = cozum_dict.get(d, {"cozulen": 0, "dogru": 0})
                        oran = min(int((c_durum["cozulen"] / v_hedef) * 100), 100) if v_hedef > 0 else 0
                        
                        col_d1, col_d2, col_d3 = st.columns([2, 5, 2])
                        with col_d1:
                            st.markdown(f"**{d}**")
                            st.caption(f"Hedef: {v_hedef} | Çözülen: {c_durum['cozulen']}")
                        with col_d2:
                            st.progress(oran / 100)
                        with col_d3:
                            if oran >= 100: st.success(f"🎯 %{oran} ({c_durum['dogru']} D)")
                            elif oran > 0: st.warning(f"⏳ %{oran} ({c_durum['dogru']} D)")
                            else: st.error("❌ Dokunulmadı")
            else:
                st.info("Seçilen tarihte atanmış bir hedef bulunamadı.")
                
        with tab3:
            st.subheader("🎯 Yeni Günlük Soru Hedefi Belirle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            cols_veli = st.columns(3)
            for i, d in enumerate(TUM_DERSLER):
                if cols_veli[i % 3].button(d, key=f"v_sel_{d}", type="primary" if st.session_state.veli_secilen_ders == d else "secondary", use_container_width=True):
                    st.session_state.veli_secilen_ders = d
                    st.rerun()
            hedef_soru = st.number_input(f"{st.session_state.veli_secilen_ders} Hedefi", min_value=1, value=5)
            if st.button("Hedefi Kaydet", type="primary", use_container_width=True):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, st.session_state.veli_secilen_ders, hedef_soru))
                st.success("Hedef başarıyla kaydedildi!")

# ==========================================
# 📱 ÖĞRENCİ / TABLET PANELİ
# ==========================================
else:
    bugun = datetime.now().strftime('%Y-%m-%d')
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    hedef_adetler = {h[0]: h[1] for h in bugunun_hedefleri}
    
    st.markdown("### 📚 Bugünkü Ders Görevlerin")
    cols_ogr = st.columns(3)
    
    for i, d in enumerate(TUM_DERSLER):
        is_active = d in hedef_adetler
        button_style = "primary" if is_active else "secondary"
        
        if cols_ogr[i % 3].button(d, key=f"ogr_btn_{d}", disabled=not is_active, type=button_style, use_container_width=True):
            st.session_state.show_popup_ders = d
            if d not in st.session_state.soru_paketi:
                with st.spinner("Yapay zeka geçmiş hataları analiz ediyor ve soruları hazırlıyor... 🧠⏳"):
                    cevap = ai_soru_uret_ve_temizle(d, adet=hedef_adetler[d])
                    if cevap:
                        st.session_state.soru_paketi[d] = cevap
                        st.session_state.aktif_index[d] = 0
                        st.session_state.kontrol_edildi[d] = [False] * len(cevap)
            st.rerun()

    # Pop-up Tetikleme Alanı
    if st.session_state.show_popup_ders and st.session_state.show_popup_ders in st.session_state.soru_paketi:
        pop_up_pencere(st.session_state.show_popup_ders, bugun)
                
    if not het_adetler if False else not hedef_adetler:
        st.success("🎉 Bugünlük atanmış bir görevin yok, harika!")