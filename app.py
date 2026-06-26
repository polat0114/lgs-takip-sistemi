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

# Profil Resmi İçin Özel CSS (Yuvarlak Çerçeve ve Gölge)
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

# Yapay Zekadan Toplu Soru Paketi Üretme
def ai_toplu_soru_uret(ders, adet=5):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        Sen Türkiye MEB müfredat uzmanı bir LGS öğretmenisin.
        Sadece ve sadece Türkiye MEB 7. Sınıf {ders} müfredat ünitelerine, kazanımlarına ve sınırlarına bağlı kalarak {adet} adet karışık genel tekrar sorusu hazırla.
        KATI KURAL: 7. sınıf müfredat sınırlarının kesinlikle dışına çıkma. Sadece 7. sınıf kazanımları olsun ama LGS tarzı mantık muhakeme mantığında olsun.
        
        FORMAT KURALLARI:
        1. Soru metinleri net, anlaşılır olsun. Sıkıcı uzun paragraf duvarları oluşturma.
        2. 'cozum' kısmı maksimum 2-3 cümle ile, samimi, emojili ve direkt hatayı gösteren bir özet olsun.
        
        Çıktıyı sadece şu JSON liste formatında ver, başka hiçbir yazı ekleme:
        [
          {{"konu": "7. Sınıf Müfredat Konu Adı", "soru": "Soru Metni", "A": "A seçeneği", "B": "B seçeneği", "C": "C seçeneği", "D": "D seçeneği", "cevap": "Doğru Şık (A, B, C veya D)", "cozum": "Kısa, net ve emojili çözüm açıklaması."}}
        ]
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        temiz_metin = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(temiz_metin)
    except:
        return []

# ----------------- ÖZEL BAŞLIK TASARIMI -----------------
col_logo, col_baslik = st.columns([1, 7])
with col_logo:
    # GitHub'a yükleyeceğin fotoğrafı burada arayacak
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

# ----------------- 1. VELİ PANELİ -----------------
if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Analiz Raporları ve Dashboard")
    
    if "veli_giris_yapildi" not in st.session_state:
        st.session_state.veli_giris_yapildi = False
        
    if not st.session_state.veli_giris_yapildi:
        girilen_sifre = st.text_input("Lütfen Veli Giriş Şifresini Girin:", type="password")
        if st.button("Giriş Yap"):
            if girilen_sifre == DOGRU_SIFRE:
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else:
                st.error("❌ Hatalı şifre!")
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
            for h in hedefler_data:
                grafik_haritasi[h[0]] = {"hedef": h[1], "dogru": 0, "yanlis": 0}
            for c in cozumler_data:
                if c[0] not in grafik_haritasi:
                    grafik_haritasi[c[0]] = {"hedef": 0, "dogru": 0, "yanlis": 0}
                grafik_haritasi[c[0]]["dogru"] = c[1]
                grafik_haritasi[c[0]]["yanlis"] = c[2]
            
            if grafik_haritasi:
                dersler_list = list(grafik_haritasi.keys())
                hedefler_list = [grafik_haritasi[d]["hedef"] for d in dersler_list]
                dogrular_list = [grafik_haritasi[d]["dogru"] for d in dersler_list]
                cyanlislar_list = [grafik_haritasi[d]["yanlis"] for d in dersler_list]
                
                fig = go.Figure(data=[
                    go.Bar(name='Verilen Soru Hedefi', x=dersler_list, y=hedefler_list, marker_color='#1f77b4'),
                    go.Bar(name='Doğru Sayısı', x=dersler_list, y=dogrular_list, marker_color='rgb(34, 139, 34)'),
                    go.Bar(name='Yanlış Sayısı', x=dersler_list, y=cyanlislar_list, marker_color='rgb(178, 34, 34)')
                ])
                fig.update_layout(
                    barmode='group', 
                    title="Ders Bazında Karşılaştırmalı Durum Grafiği", 
                    xaxis_title="Dersler", 
                    yaxis_title="Soru Sayısı",
                    legend_title="Gösterge"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 Veri Dağılım Listesi")
                for d in dersler_list:
                    st.write(f"📖 **{d}**: Belirlenen Hedef: `{grafik_haritasi[d]['hedef']}` Soru | Çözülen Doğru: `{grafik_haritasi[d]['dogru']}` | Yanlış: `{grafik_haritasi[d]['yanlis']}`")
            else:
                st.info("Grafiklerin çizilmesi için bir hedef girilmesi veya soru çözülmesi gerekiyor.")
                
        with tab2:
            st.subheader("Günlük Soru Hedefi Belirle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            secilen_ders = st.selectbox("Ders Seçin", ["Türkçe", "Matematik", "Fen Bilimleri", "İngilizce", "Sosyal Bilgiler"])
            hedef_soru = st.number_input("Günlük Soru Hedefi", min_value=1, value=5, step=1)
            if st.button("Hedefi Kaydet"):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, secilen_ders, hedef_soru))
                st.success("Hedef başarıyla kaydedildi!")

# ----------------- 2. ÖĞRENCİ PANELİ -----------------
else:
    bugun = datetime.now().strftime('%Y-%m-%d')
    
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    
    if "test_tamamen_bittimi" not in st.session_state:
        st.session_state.test_tamamen_bittimi = False
        
    if st.session_state.test_tamamen_bittimi:
        st.balloons()
        st.success("🏆 Harika! Bugünkü çalışmanı başarıyla bitirdin ve bitirme raporunu gönderdin. Şimdi dinlenme zamanı! 🎉")
        if st.button("🔄 Yeni Test Başlat"):
            st.session_state.test_tamamen_bittimi = False
            if "soru_paketi" in st.session_state: del st.session_state.soru_paketi
            st.rerun()
            
    elif bugunun_hedefleri:
        ders_listesi = [h[0] for h in bugunun_hedefleri]
        hedef_adetler = {h[0]: h[1] for h in bugunun_hedefleri}
        secilen_ders_ogrenci = st.selectbox("Çalışmak İstediğin Dersi Seç:", ders_listesi)
        
        if "soru_paketi" not in st.session_state:
            st.session_state.soru_paketi = {}
        if "aktif_index" not in st.session_state:
            st.session_state.aktif_index = 0
        if "kontrol_edildi_list" not in st.session_state:
            st.session_state.kontrol_edildi_list = {}

        if secilen_ders_ogrenci not in st.session_state.soru_paketi:
            if st.button(f"🚀 {secilen_ders_ogrenci} Test Paketini Hazırla"):
                # SENİN İSTEDİĞİN YENİ YÜKLEME MESAJI BURADA
                with st.spinner("Senin için sorular hazırlanıyor... ⏳"):
                    sorular = ai_toplu_soru_uret(secilen_ders_ogrenci, adet=hedef_adetler[secilen_ders_ogrenci])
                    if sorular:
                        st.session_state.soru_paketi[secilen_ders_ogrenci] = sorular
                        st.session_state.aktif_index = 0
                        st.session_state.kontrol_edildi_list[secilen_ders_ogrenci] = [False] * len(sorular)
                        st.rerun()

        if secilen_ders_ogrenci in st.session_state.soru_paketi and st.session_state.soru_paketi[secilen_ders_ogrenci]:
            havuz = st.session_state.soru_paketi[secilen_ders_ogrenci]
            idx = st.session_state.aktif_index
            
            if idx < len(havuz):
                soru = havuz[idx]
                
                col_sol, col_orta, col_sag = st.columns([1, 4, 1])
                with col_sol:
                    if idx > 0:
                        if st.button("⬅️ Önceki Soru"):
                            st.session_state.aktif_index -= 1
                            st.rerun()
                with col_orta:
                    st.info(f"📋 7. Sınıf {secilen_ders_ogrenci} | Konu: {soru['konu']} | 📌 Soru {idx + 1} / {len(havuz)}")
                with col_sag:
                    if idx < len(havuz) - 1:
                        if st.button("Sonraki Soru ➡️"):
                            st.session_state.aktif_index += 1
                            st.rerun()
                
                col_soru_alani, col_karalama_alani = st.columns([1, 1])
                
                with col_soru_alani:
                    st.markdown(f"### {soru['soru']}")
                    
                    secenek = st.radio(
                        "Cevabını İşaretle:", 
                        [f"A) {soru['A']}", f"B) {soru['B']}", f"C) {soru['C']}", f"D) {soru['D']}"], 
                        index=None, 
                        key=f"radio_{secilen_ders_ogrenci}_{idx}"
                    )
                    
                    is_checked = st.session_state.kontrol_edildi_list[secilen_ders_ogrenci][idx]
                    
                    if not is_checked:
                        if st.button("Cevabı Kontrol Et 🚀", key=f"btn_{idx}"):
                            if secenek is None:
                                st.warning("⚠️ Lütfen önce bir şık işaretle!")
                            else:
                                st.session_state.kontrol_edildi_list[secilen_ders_ogrenci][idx] = True
                                secilen_harf = secenek[0]
                                if secilen_harf == soru['cevap']:
                                    veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, secilen_ders_ogrenci, soru['konu']))
                                else:
                                    veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, secilen_ders_ogrenci, soru['konu'], f"{soru['konu']} hatası."))
                                st.rerun()
                    else:
                        st.subheader("💡 Yapay Zeka Çözüm Özeti")
                        if secenek and secenek[0] == soru['cevap']:
                            st.success(f"🎉 Doğru! {soru['cozum']}")
                        else:
                            st.error(f"❌ Yanlış. Doğru Seçenek: {soru['cevap']}")
                            st.warning(soru['cozum'])
                        
                        st.divider()
                        if idx < len(havuz) - 1:
                            if st.button("Sıradaki Soruya Geç ➡️", key=f"next_btn_{idx}"):
                                st.session_state.aktif_index += 1
                                st.rerun()
                        else:
                            if st.button("🏁 Bugünkü Çalışmayı Bitir ve Babama Raporla 🏆", key="bitir_btn"):
                                st.session_state.test_tamamen_bittimi = True
                                st.rerun()
                
                with col_karalama_alani:
                    st.caption("✏️ Tablet kalemiyle veya parmağınla işlemini burada yapabilirsin:")
                    firca_kalinligi = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"slider_{idx}")
                    canvas_result = st_canvas(
                        fill_color="rgba(255, 165, 0, 0.3)",
                        stroke_width=firca_kalinligi,
                        stroke_color="#000000",
                        background_color="#eeeeee",
                        height=380,
                        drawing_mode="freedraw",
                        key=f"canvas_{secilen_ders_ogrenci}_{idx}",
                    )
            else:
                st.success("🏆 Bu dersin paketindeki tüm sorular tamamlandı!")
    else:
        st.success("🎉 Bugünlük hedefin tamamlanmış veya henüz hedef girilmemiş. Dinlenebilirsin!")