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

# Profil Resmi İçin Özel CSS
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

# Sabit Ders Listesi
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

# Yapay Zeka
def ai_toplu_soru_uret(ders, adet=5):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        Sen Türkiye MEB müfredat uzmanı bir LGS öğretmenisin.
        Sadece Türkiye MEB 7. Sınıf {ders} müfredatına bağlı kalarak {adet} adet LGS tarzı mantık muhakeme sorusu hazırla.
        
        KATI KURAL: Çıktıyı SADECE VE SADECE JSON formatında ver. Başına veya sonuna HİÇBİR metin ekleme! 
        Sadece köşeli parantezle başlayan şu formattaki temiz bir liste ver:
        [
          {{"konu": "Müfredat Konusu", "soru": "Soru Metni", "A": "A seçeneği", "B": "B seçeneği", "C": "C seçeneği", "D": "D seçeneği", "cevap": "Doğru Şık (A, B, C veya D)", "cozum": "Kısa, net ve emojili çözüm."}}
        ]
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        temiz_metin = response.text.strip()
        if temiz_metin.startswith("```json"): temiz_metin = temiz_metin[7:]
        if temiz_metin.endswith("```"): temiz_metin = temiz_metin[:-3]
        return json.loads(temiz_metin.strip())
    except Exception as e:
        return "hata" 

# Bellek (State) Yönetimi
if "soru_paketi" not in st.session_state:
    st.session_state.soru_paketi = {}
if "aktif_index" not in st.session_state:
    st.session_state.aktif_index = {}
if "kontrol_edildi" not in st.session_state:
    st.session_state.kontrol_edildi = {}
if "veli_secilen_ders" not in st.session_state:
    st.session_state.veli_secilen_ders = TUM_DERSLER[0]

# ==========================================
# 🎯 ÖZEL POP-UP ÇÖZÜM EKRANI MİMARİSİ
# ==========================================
@st.dialog("🎯 LGS Çözüm Karargâhı", width="large")
def ac_pop_up(ders, hedef_adet, bugun):
    if ders not in st.session_state.soru_paketi:
        with st.spinner(f"Senin için {ders} soruları hazırlanıyor... ⏳"):
            sorular = ai_toplu_soru_uret(ders, adet=hedef_adet)
            if sorular == "hata":
                st.error("⚠️ Yapay zeka yoğunluktan dolayı soruları oluşturamadı. Lütfen sağ üstteki (X) işaretinden kapatıp tekrar tıkla.")
                return
            elif sorular:
                st.session_state.soru_paketi[ders] = sorular
                st.session_state.aktif_index[ders] = 0
                st.session_state.kontrol_edildi[ders] = [False] * len(sorular)
                st.rerun()

    havuz = st.session_state.soru_paketi.get(ders, [])
    if not havuz: return
    
    idx = st.session_state.aktif_index.get(ders, 0)
    soru = havuz[idx]
    
    # Üst Navigasyon Okları
    col_sol, col_orta, col_sag = st.columns([1, 4, 1])
    with col_sol:
        if idx > 0:
            if st.button("⬅️ Önceki", key=f"prev_{ders}_{idx}", use_container_width=True):
                st.session_state.aktif_index[ders] -= 1
                st.rerun()
    with col_orta:
        st.info(f"📌 Soru {idx + 1} / {len(havuz)} | Konu: {soru.get('konu', '')}")
    with col_sag:
        if idx < len(havuz) - 1:
            if st.button("Sonraki ➡️", key=f"next_{ders}_{idx}", use_container_width=True):
                st.session_state.aktif_index[ders] += 1
                st.rerun()

    st.divider()
    
    # Soru ve Çizim Alanı
    col_soru_alani, col_karalama_alani = st.columns([1, 1])
    with col_soru_alani:
        st.markdown(f"### {soru.get('soru', '')}")
        secenek = st.radio(
            "Cevabını İşaretle:", 
            [f"A) {soru.get('A', '')}", f"B) {soru.get('B', '')}", f"C) {soru.get('C', '')}", f"D) {soru.get('D', '')}"], 
            index=None, 
            key=f"radio_{ders}_{idx}"
        )
        
        is_checked = st.session_state.kontrol_edildi[ders][idx]
        if not is_checked:
            if st.button("Cevabı Kontrol Et 🚀", key=f"btn_chk_{ders}_{idx}", type="primary"):
                if secenek is None:
                    st.warning("⚠️ Lütfen önce bir şık işaretle!")
                else:
                    st.session_state.kontrol_edildi[ders][idx] = True
                    secilen_harf = secenek[0]
                    if secilen_harf == soru.get('cevap', ''):
                        veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, ders, soru.get('konu', '')))
                    else:
                        veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, ders, soru.get('konu', ''), f"{soru.get('konu', '')} hatası."))
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
                if st.button("Sıradaki Soruya Geç ➡️", key=f"pass_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] += 1
                    st.rerun()
            else:
                st.balloons()
                st.success("🏆 Harika! Bu dersin bugünkü görevini başarıyla bitirdin ve raporunu babana gönderdin!")
                st.info("Sağ üstteki (X) işaretine basarak ana ekrana dönebilir, diğer derslerini çözebilirsin.")
    
    with col_karalama_alani:
        st.caption("✏️ Karalama ve İşlem Alanı:")
        firca_kalinligi = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"sl_{ders}_{idx}")
        st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=firca_kalinligi,
            stroke_color="#000000",
            background_color="#eeeeee",
            height=380,
            drawing_mode="freedraw",
            key=f"canvas_{ders}_{idx}"
        )


# ==========================================
# 🏠 ANA EKRAN VE PANELLER
# ==========================================
col_logo, col_baslik = st.columns([1, 7])
with col_logo:
    if os.path.exists("profil.jpg"):
        st.image("profil.jpg", width=120)
    else:
        st.info("📷 Profil")
with col_baslik:
    st.title("🏆 Şampiyonun LGS Karargâhı 🚀")
    st.caption("Hedeflerine adım adım, pes etmeden!")
st.divider()

panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)
st.divider()

if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Analiz Raporları ve Dashboard")
    if not st.session_state.get("veli_giris_yapildi"):
        girilen_sifre = st.text_input("Lütfen Veli Giriş Şifresini Girin:", type="password")
        if st.button("Giriş Yap"):
            if girilen_sifre == DOGRU_SIFRE:
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else: st.error("❌ Hatalı şifre!")
    else:
        if st.button("🔒 Paneli Kilitle"):
            st.session_state.veli_giris_yapildi = False
            st.rerun()
            
        tab1, tab2 = st.tabs(["📊 Gelişmiş Hedef ve Performans Grafiği", "🎯 Günlük Hedef Belirle"])
        with tab1:
            st.subheader("📈 Derslere Göre Hedef / Doğru / Yanlış Dağılımı")
            hedefler_data = veri_getir("SELECT ders, SUM(hedef_soru) FROM hedefler GROUP BY ders")
            cozumler_data = veri_getir("SELECT ders, SUM(dogru_sayisi), SUM(yanlis_sayisi) FROM cozumler GROUP BY ders")
            
            grafik_haritasi = {}
            for h in hedefler_data: grafik_haritasi[h[0]] = {"hedef": h[1], "dogru": 0, "yanlis": 0}
            for c in cozumler_data:
                if c[0] not in grafik_haritasi: grafik_haritasi[c[0]] = {"hedef": 0, "dogru": 0, "yanlis": 0}
                grafik_haritasi[c[0]]["dogru"] = c[1]
                grafik_haritasi[c[0]]["yanlis"] = c[2]
            
            if grafik_haritasi:
                dersler_list = list(grafik_haritasi.keys())
                fig = go.Figure(data=[
                    go.Bar(name='Verilen Soru Hedefi', x=dersler_list, y=[grafik_haritasi[d]["hedef"] for d in dersler_list], marker_color='#1f77b4'),
                    go.Bar(name='Doğru Sayısı', x=dersler_list, y=[grafik_haritasi[d]["dogru"] for d in dersler_list], marker_color='rgb(34, 139, 34)'),
                    go.Bar(name='Yanlış Sayısı', x=dersler_list, y=[grafik_haritasi[d]["yanlis"] for d in dersler_list], marker_color='rgb(178, 34, 34)')
                ])
                fig.update_layout(barmode='group', title="Ders Bazında Karşılaştırmalı Durum", xaxis_title="Dersler", yaxis_title="Soru Sayısı")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Grafiklerin çizilmesi için bir hedef girilmesi veya soru çözülmesi gerekiyor.")
                
        with tab2:
            st.subheader("Günlük Soru Hedefi Belirle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            st.write("**Hedef Belirlenecek Dersi Seçin:**")
            
            cols_veli = st.columns(3)
            for i, d in enumerate(TUM_DERSLER):
                btn_type = "primary" if st.session_state.veli_secilen_ders == d else "secondary"
                if cols_veli[i % 3].button(d, key=f"v_btn_{d}", type=btn_type, use_container_width=True):
                    st.session_state.veli_secilen_ders = d
                    st.rerun()
            
            hedef_soru = st.number_input(f"{st.session_state.veli_secilen_ders} İçin Soru Hedefi", min_value=1, value=5, step=1)
            if st.button("Hedefi Kaydet", type="primary"):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, st.session_state.veli_secilen_ders, hedef_soru))
                st.success(f"{st.session_state.veli_secilen_ders} hedefi başarıyla kaydedildi!")

else:
    bugun = datetime.now().strftime('%Y-%m-%d')
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    hedef_adetler = {h[0]: h[1] for h in bugunun_hedefleri}
    
    st.markdown("### 📚 Bugünkü Görevlerin (Çözmek İstediğin Kutuya Tıkla)")
    
    cols_ogr = st.columns(3)
    for i, d in enumerate(TUM_DERSLER):
        is_active = d in hedef_adetler
        b_type = "primary" if is_active else "secondary"
        if cols_ogr[i % 3].button(d, key=f"o_btn_{d}", disabled=not is_active, type=b_type, use_container_width=True):
            ac_pop_up(d, hedef_adetler[d], bugun)
            
    if not hedef_adetler:
        st.success("🎉 Bugünlük tanımlanmış hedefin yok. Dinlenebilirsin!")