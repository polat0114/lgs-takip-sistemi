import streamlit as st
import sqlite3
from datetime import datetime
from google import genai
import plotly.graph_objects as go
import os
from streamlit_drawable_canvas import st_canvas

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Şampiyonun LGS Karargâhı")

DOGRU_SIFRE = "1234"
GEMINI_API_KEY = "AQ.Ab8RN6ISfgTLZu44H--l4mSQMq_uxk-TJanYkpHn346OXLQEeg"

# Profil Resmi İçin Yuvarlak Yapma Özel CSS
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

# ==========================================
# 🗄️ VERİTABANI GÜVENLİ BAĞLANTI MODÜLLERİ
# ==========================================
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

# ==========================================
# 🤖 SARSILMAZ VE ASLA ÇÖKMEYEN AI OKUYUCU
# ==========================================
def ai_soru_metni_parcala(ders, adet=5):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        Sen Türkiye MEB müfredat uzmanı bir LGS öğretmenisin.
        Sadece Türkiye MEB 7. Sınıf {ders} müfredatına bağlı kalarak {adet} adet LGS tarzı yeni nesil soru hazırla.
        Hiçbir kod bloğu, JSON veya markdown kod formatı kullanma. Sadece aşağıdaki şablona harfiyen uyarak düz metin yaz. Soruların arasına kesinlikle tek satır halinde === ekle!
        
        ŞABLON:
        KONU: [Konu Adı]
        SORU: [Soru Metni]
        A: [A seçeneği]
        B: [B seçeneği]
        C: [C seçeneği]
        D: [D seçeneği]
        CEVAP: [Sadece A, B, C veya D harfi]
        COZUM: [Maksimum 2 cümlelik emojili çözüm]
        ===
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        ham_metin = response.text.strip()
        
        # Yapay zekadan gelen veriyi parçalama işlemi
        bloklar = ham_metin.split("===")
        sorular_listesi = []
        
        for blok in bloklar:
            if "SORU:" in blok and "CEVAP:" in blok:
                satirlar = blok.strip().split("\n")
                s_dict = {"konu": "Genel Tekrar", "soru": "", "A": "", "B": "", "C": "", "D": "", "cevap": "A", "cozum": ""}
                for satir in satirlar:
                    satir = satir.strip()
                    if satir.startswith("KONU:"): s_dict["konu"] = satir.replace("KONU:", "").strip()
                    elif satir.startswith("SORU:"): s_dict["soru"] = satir.replace("SORU:", "").strip()
                    elif satir.startswith("A:"): s_dict["A"] = satir.replace("A:", "").strip()
                    elif satir.startswith("B:"): s_dict["B"] = satir.replace("B:", "").strip()
                    elif satir.startswith("C:"): s_dict["C"] = satir.replace("C:", "").strip()
                    elif satir.startswith("D:"): s_dict["D"] = satir.replace("D:", "").strip()
                    elif satir.startswith("CEVAP:"): s_dict["cevap"] = satir.replace("CEVAP:", "").strip()
                    elif satir.startswith("COZUM:"): s_dict["cozum"] = satir.replace("COZUM:", "").strip()
                sorular_listesi.append(s_dict)
                
        return sorular_listesi if len(sorular_listesi) > 0 else None
    except:
        return None

# ==========================================
# 🧠 STREAMLIT BELLEK (STATE) YÖNETİMİ
# ==========================================
if "soru_paketi" not in st.session_state: st.session_state.soru_paketi = {}
if "aktif_index" not in st.session_state: st.session_state.aktif_index = {}
if "kontrol_edildi" not in st.session_state: st.session_state.kontrol_edildi = {}
if "veli_secilen_ders" not in st.session_state: st.session_state.veli_secilen_ders = TUM_DERSLER[0]
if "show_popup_ders" not in st.session_state: st.session_state.show_popup_ders = None

# ==========================================
# 🎯 DİALOG / POP-UP SORU ÇÖZÜM MODÜLÜ
# ==========================================
@st.dialog("🎯 LGS Çözüm Karargâhı", width="large")
def pop_up_pencere(ders, bugun):
    havuz = st.session_state.soru_paketi.get(ders, [])
    idx = st.session_state.aktif_index.get(ders, 0)
    
    if idx < len(havuz):
        soru = havuz[idx]
        
        # Üst Soru Navigasyon Barı
        col_sol, col_orta, col_sag = st.columns([1, 4, 1])
        with col_sol:
            if idx > 0:
                if st.button("⬅️ Önceki Soru", key=f"nav_p_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] -= 1
                    st.rerun()
        with col_orta:
            st.info(f"📌 Soru {idx + 1} / {len(havuz)} | Ders: {ders} | Konu: {soru.get('konu', '')}")
        with col_sag:
            if idx < len(havuz) - 1:
                if st.button("Sonraki Soru ➡️", key=f"nav_n_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] += 1
                    st.rerun()

        st.divider()
        
        # Sol Taraf: Soru ve Şıklar | Sağ Taraf: Karalama Tahtası
        col_soru_alani, col_cizim_alani = st.columns([1, 1])
        with col_soru_alani:
            st.markdown(f"### {soru.get('soru', '')}")
            
            secenek = st.radio(
                "Cevabını Seç:", 
                [f"A) {soru.get('A', '')}", f"B) {soru.get('B', '')}", f"C) {soru.get('C', '')}", f"D) {soru.get('D', '')}"], 
                index=None, key=f"radio_choice_{ders}_{idx}"
            )
            
            is_checked = st.session_state.kontrol_edildi[ders][idx]
            if not is_checked:
                if st.button("Cevabı Kontrol Et 🚀", key=f"btn_check_{ders}_{idx}", type="primary", use_container_width=True):
                    if secenek is None:
                        st.warning("⚠️ Lütfen önce bir seçeneği işaretle!")
                    else:
                        st.session_state.kontrol_edildi[ders][idx] = True
                        secilen_harf = secenek[0]  # A, B, C veya D
                        dogru_harf = soru.get('cevap', 'A').strip().upper()
                        
                        if secilen_harf == dogru_harf:
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, ders, soru.get('konu', '')))
                        else:
                            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, ders, soru.get('konu', ''), f"{secilen_harf} işaretlendi, doğru {dogru_harf}"))
                        st.rerun()
            else:
                st.subheader("💡 Yapay Zeka Çözüm Analizi")
                secilen_harf = secenek[0] if secenek else ""
                dogru_harf = soru.get('cevap', 'A').strip().upper()
                
                if secilen_harf == dogru_harf:
                    st.success(f"🎉 Harika Doğru! {soru.get('cozum', '')}")
                else:
                    st.error(f"❌ Yanlış Cevap. Doğru Seçenek: {dogru_harf}")
                    st.warning(soru.get('cozum', ''))
                
                st.divider()
                if idx < len(havuz) - 1:
                    if st.button("Sıradaki Soruya Geç ➡️", key=f"btn_next_pass_{ders}_{idx}", use_container_width=True):
                        st.session_state.aktif_index[ders] += 1
                        st.rerun()
                else:
                    st.balloons()
                    st.success("🏆 Tebrikler! Bu dersin tüm sorularını başarıyla bitirdin!")
                    if st.button("🏁 Çalışmayı Bitir ve Paneli Kapat", key=f"btn_finish_close_{ders}", type="primary", use_container_width=True):
                        st.session_state.show_popup_ders = None
                        st.rerun()
        
        with col_cizim_alani:
            st.caption("✏️ Karalama ve İşlem Yapma Alanı:")
            firca = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"brush_slider_{ders}_{idx}")
            st_canvas(
                fill_color="rgba(255,165,0,0.3)", 
                stroke_width=firca, 
                stroke_color="#000000", 
                background_color="#eeeeee", 
                height=360, 
                drawing_mode="freedraw", 
                key=f"canvas_board_{ders}_{idx}"
            )

# ==========================================
# 🏠 ANA EKRAN LOGO VE BAŞLIK
# ==========================================
col_logo, col_baslik = st.columns([1, 7])
with col_logo:
    if os.path.exists("profil.jpg"): 
        st.image("profil.jpg", width=120)
    else: 
        st.info("📷 Profil")
with col_baslik:
    st.title("🏆 Şampiyonun LGS Karargâhı 🚀")
    st.caption("Poyraz Efe'nin LGS Yolculuğu - Hedeflerine Adım Adım!")
st.divider()

panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)
st.divider()

# ==========================================
# 👨‍🏫 VELİ / YÖNETİCİ PANELİ
# ==========================================
if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Analiz Raporları ve Kontrol Merkezi")
    if not st.session_state.get("veli_giris_yapildi"):
        girilen_sifre = st.text_input("Giriş Şifresi:", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if girilen_sifre == DOGRU_SIFRE: 
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else: 
                st.error("❌ Hatalı şifre!")
    else:
        if st.button("🔒 Paneli Kilitle", type="secondary"):
            st.session_state.veli_giris_yapildi = False
            st.rerun()
            
        tab1, tab2 = st.tabs(["📊 Performans ve Hedef Grafiği", "🎯 Günlük Soru Hedefi Koy"])
        with tab1:
            st.subheader("📈 Ders Bazlı Durum Grafiği")
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
                    go.Bar(name='Verilen Hedef', x=dersler_list, y=[grafik_haritasi[d]["hedef"] for d in dersler_list], marker_color='#1f77b4'),
                    go.Bar(name='Doğru Sayısı', x=dersler_list, y=[grafik_haritasi[d]["dogru"] for d in dersler_list], marker_color='rgb(34, 139, 34)'),
                    go.Bar(name='Yanlış Sayısı', x=dersler_list, y=[grafik_haritasi[d]["yanlis"] for d in dersler_list], marker_color='rgb(178, 34, 34)')
                ])
                fig.update_layout(barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            else: 
                st.info("Henüz analiz edilecek veri girilmedi.")
                
        with tab2:
            st.subheader("Günlük Soru Hedefi Belirle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            
            cols_veli = st.columns(3)
            for i, d in enumerate(TUM_DERSLER):
                type_style = "primary" if st.session_state.veli_secilen_ders == d else "secondary"
                if cols_veli[i % 3].button(d, key=f"veli_select_{d}", type=type_style, use_container_width=True):
                    st.session_state.veli_secilen_ders = d
                    st.rerun()
            
            hedef_soru = st.number_input(f"{st.session_state.veli_secilen_ders} İçin Hedef Soru Adeti", min_value=1, value=5)
            if st.button("Hedefi Veritabanına Kaydet", type="primary", use_container_width=True):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, st.session_state.veli_secilen_ders, hedef_soru))
                st.success(f"🎯 {st.session_state.veli_secilen_ders} dersi için {hedef_soru} adet soru hedefi başarıyla koyuldu!")

# ==========================================
# 📱 ÖĞRENCİ / TABLET PANELİ
# ==========================================
else:
    bugun = datetime.now().strftime('%Y-%m-%d')
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    hedef_adetler = {h[0]: h[1] for h in bugunun_hedefleri}
    
    st.markdown("### 📚 Bugünkü Ders Görevlerin (Çözmek İstediğin Kutuya Tıkla)")
    cols_ogr = st.columns(3)
    
    for i, d in enumerate(TUM_DERSLER):
        is_active = d in hedef_adetler
        button_style = "primary" if is_active else "secondary"
        
        if cols_ogr[i % 3].button(d, key=f"ogr_btn_{d}", disabled=not is_active, type=button_style, use_container_width=True):
            if d not in st.session_state.soru_paketi:
                with st.spinner("Sorular yapay zeka tarafından özenle hazırlanıyor... ⏳"):
                    sorular = ai_soru_metni_parcala(d, adet=hedef_adetler[d])
                    if sorular:
                        st.session_state.soru_paketi[d] = sorular
                        st.session_state.aktif_index[d] = 0
                        st.session_state.kontrol_edildi[d] = [False] * len(sorular)
                        st.session_state.show_popup_ders = d
                        st.rerun()
                    else:
                        st.error("⚠️ Sunucu bağlantısında anlık yoğunluk oldu. Lütfen ders kutusuna tekrar dokun.")
            else:
                st.session_state.show_popup_ders = d
                st.rerun()

    # Eğer tetiklenen aktif bir pop-up dersi varsa ekranda göster
    if st.session_state.show_popup_ders:
        pop_up_pencere(st.session_state.show_popup_ders, bugun)
        
    if not hedef_adetler:
        st.success("🎉 Harika! Bugün için atanmış bir görevin yok, bol bol dinlenebilirsin!")