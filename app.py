import streamlit as st
import sqlite3
from datetime import datetime
from google import genai
import plotly.graph_objects as go

# Sayfa Genişlik Ayarı
st.set_page_config(layout="wide", page_title="LGS Yapay Zeka Destekli Akademi")

DOGRU_SIFRE = "1234"

# 🔑 Google Gemini API Anahtarın Sisteme Entegre Edildi
GEMINI_API_KEY = "AQ.Ab8RN6ISfgTLZu44H--l4mSQMq_uxk-TJanYkpHn346OXLQEeg"

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

# Yapay Zeka Soru ve Çözüm Üretme Fonksiyonu
def ai_soru_uret(ders):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"Türkiye MEB 7. sınıf {ders} müfredatının tamamını kapsayan, LGS tarzında, yeni nesil zorlukta karışık bir genel tekrar sorusu hazırla. Çıktıyı sadece şu JSON formatında ver, başka hiçbir açıklama yazma: {{\"konu\": \"Konu Adı\", \"soru\": \"Soru Metni\", \"A\": \"A şıkkı metni\", \"B\": \"B şıkkı metni\", \"C\": \"C şıkkı metni\", \"D\": \"D şıkkı metni\", \"cevap\": \"Doğru Şık (Sadece A, B, C veya D)\", \"cozum\": \"Sorunun detaylı yapay zeka çözüm açıklaması ve ipuçları\"}}"
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        import json
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except:
        return None

# Üst Başlık
st.title("🤖 LGS Yapay Zeka Destekli Akıllı Takip ve Öğrenme Sistemi")
panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)
st.divider()

# ----------------- 1. VELİ PANELİ (GRAFİKLİ & ANALİZLİ) -----------------
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
            
        tab1, tab2 = st.tabs(["📊 Grafiksel Performans Raporu", "🎯 Günlük Hedef Belirle"])
        
        with tab1:
            st.subheader("📈 Oğlunun Güncel Gelişim Grafikleri")
            veriler = veri_getir("SELECT ders, konu_adi, SUM(dogru_sayisi), SUM(yanlis_sayisi) FROM cozumler GROUP BY ders, konu_adi")
            
            if veriler:
                konular_list = [f"{v[0]} - {v[1]}" for v in veriler]
                dogrular = [v[2] for v in veriler]
                yanlislar = [v[3] for v in veriler]
                
                # Plotly İle Grafik Oluşturma
                fig = go.Figure(data=[
                    go.Bar(name='Doğru Sayısı', x=konular_list, y=dogrular, marker_color='rgb(34, 139, 34)'),
                    go.Bar(name='Yanlış Sayısı', x=konular_list, y=yanlislar, marker_color='rgb(178, 34, 34)')
                ])
                fig.update_layout(barmode='group', title="Konulara Göre Doğru / Yanlış Dağılımı", xaxis_title="Konular", yaxis_title="Soru Sayısı")
                st.plotly_chart(fig, use_container_width=True)
                
                # Akıllı Durum Durakları
                st.subheader("💡 Yapay Zeka Veli Değerlendirme Özeti")
                col1, col2 = st.columns(2)
                with col1:
                    st.success("✅ Çok İyi Anladığı İçinin Rahat Olacağı Konular")
                    for v in veriler:
                        if v[2] > v[3]:
                            st.write(f"• **{v[0]}** - {v[1]}")
                with col2:
                    st.error("⚠️ Biraz Daha Soru Çözmesi ve Eksik Olduğu Konular")
                    for v in veriler:
                        if v[3] >= v[2]:
                            st.write(f"• **{v[0]}** - {v[1]} (Hata Oranı Yüksek!)")
            else:
                st.info("Grafiklerin çizilmesi için oğlunun en az 1 soru çözmesi gerekiyor.")
                
        with tab2:
            st.subheader("Günlük Soru Hedefi Belirle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            secilen_ders = st.selectbox("Ders Seçin", ["Türkçe", "Matematik", "Fen Bilimleri", "İngilizce", "Sosyal Bilgiler"])
            hedef_soru = st.number_input("Günlük Soru Hedefi", min_value=1, value=10)
            if st.button("Hedefi Kaydet"):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, secilen_ders, hedef_soru))
                st.success("Hedef başarıyla gönderildi!")

# ----------------- 2. ÖĞRENCİ PANELİ (TAM OTOMATİK YAPAY ZEKA) -----------------
else:
    st.header("📱 Yapay Zeka Destekli Akıllı Tablet Ekranı")
    bugun = datetime.now().strftime('%Y-%m-%d')
    
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    
    if bugunun_hedefleri:
        ders_listesi = [h[0] for h in bugunun_hedefleri]
        secilen_ders_ogrenci = st.selectbox("Çalışmak İstediğin Dersi Seç ve Yapay Zekayı Başlat:", ders_listesi)
        
        if "current_ai_soru" not in st.session_state:
            st.session_state.current_ai_soru = None
            st.session_state.cevap_kontrol_edildi = False
            
        if st.button("🤖 Yapay Zekadan Yeni Nesil Soru Getir"):
            with st.spinner("Yapay zeka 7. sınıf havuzundan sana özel soru üretiyor..."):
                st.session_state.current_ai_soru = ai_soru_uret(secilen_ders_ogrenci)
                st.session_state.cevap_kontrol_edildi = False
                st.rerun()
                
        soru = st.session_state.current_ai_soru
        if soru:
            st.info(f"📋 7. Sınıf Genel Tekrar | Konu: {soru['konu']}")
            st.markdown(f"### {soru['soru']}")
            
            secenek = st.radio("Cevabını İşaretle:", [f"A) {soru['A']}", f"B) {soru['B']}", f"C) {soru['C']}", f"D) {soru['D']}"])
            
            if not st.session_state.cevap_kontrol_edildi:
                if st.button("Cevabı Kontrol Et 🚀"):
                    st.session_state.cevap_kontrol_edildi = True
                    secilen_harf = secenek[0]
                    dogru_harf = soru['cevap']
                    
                    if secilen_harf == dogru_harf:
                        st.success("🎉 Harika! Doğru cevap verdin.")
                        veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", 
                                    (bugun, secilen_ders_ogrenci, soru['konu']))
                    else:
                        st.error(f"❌ Yanlış cevap verdiniz. Doğru seçenek: {dogru_harf}")
                        veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", 
                                    (bugun, secilen_ders_ogrenci, soru['konu'], f"{soru['konu']} konusunda hata yapıldı."))
                    st.rerun()
            else:
                st.subheader("💡 Yapay Zeka Çözüm ve Analiz Açıklaması")
                if secenek[0] == soru['cevap']:
                    st.success(soru['cozum'])
                else:
                    st.warning(soru['cozum'])
                st.caption("Yeni bir soruya geçmek için yukarıdaki 'Yapay Zekadan Yeni Nesil Soru Getir' butonuna tekrar basabilirsin.")
        else:
            st.write("Soru getirmek için lütfen yukarıdaki butona tıklayın.")
    else:
        st.success("🎉 Bugünlük hedefin tamamlanmış veya henüz hedef girilmemiş. Dinlenebilirsin!")