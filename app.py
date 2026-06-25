import streamlit as st
import sqlite3
from datetime import datetime

# Sayfa Genişlik Ayarı
st.set_page_config(layout="wide", page_title="LGS Dijital Çalışma ve Analiz")

# Sabit Veli Şifresi
DOGRU_SIFRE = "1905"

# Veri Tabanı Bağlantı Fonksiyonları
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

# Üst Başlık
st.title("🎯 LGS Kişiselleştirilmiş Takip ve Analiz Sistemi")

# Üst Menüden Panel Seçimi
panel = st.radio("Lütfen Giriş Türünü Seçin:", ["Veli / Yönetici Paneli", "Öğrenci / Tablet Paneli"], horizontal=True)

st.divider()

# ----------------- 1. VELİ PANELİ (ŞİFRELİ) -----------------
if panel == "Veli / Yönetici Paneli":
    st.header("👨‍🏫 Veli Hedef Belirleme ve Analiz Ekranı")
    
    # Şifre Kontrol Alanı
    if "veli_giris_yapildi" not in st.session_state:
        st.session_state.veli_giris_yapildi = False
        
    if not st.session_state.veli_giris_yapildi:
        girilen_sifre = st.text_input("Lütfen Veli Giriş Şifresini Girin:", type="password", placeholder="PIN Kodu")
        if st.button("Giriş Yap"):
            if girilen_sifre == DOGRU_SIFRE:
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else:
                st.error("❌ Hatalı şifre girdiniz! Lütfen tekrar deneyin.")
    else:
        # Şifre doğruysa içerik gösterilir
        if st.button("🔒 Çıkış Yap (Paneli Kilitle)"):
            st.session_state.veli_giris_yapildi = False
            st.rerun()
            
        tab1, tab2 = st.tabs(["🎯 Günlük Hedef Tanımla", "📊 Hata ve Analiz Raporları"])
        
        with tab1:
            st.subheader("Yeni Günlük Soru Hedefi Ekle")
            tarih = st.date_input("Hedef Tarihi", datetime.now()).strftime('%Y-%m-%d')
            dersler = ["Türkçe", "Matematik", "Fen Bilimleri", "T.C. İnkılap Tarihi", "Din Kültürü", "İngilizce"]
            secilen_ders = st.selectbox("Ders Seçin", dersler)
            hedef_soru = st.number_input("Günlük Çözmesi Gereken Soru Adedi", min_value=5, max_value=200, value=30, step=5)
            
            if st.button("Hedefi Kaydet ve Gönder"):
                veri_kaydet("INSERT INTO hedefler (tarih, ders, hedef_soru) VALUES (?, ?, ?)", (tarih, secilen_ders, hedef_soru))
                st.success(f"{tarih} tarihi için {secilen_ders} dersine {hedef_soru} soru hedefi başarıyla eklendi!")
                
        with tab2:
            st.subheader("📝 Konu Bazlı Hata ve Anlaşılmayan Noktalar")
            raporlar = veri_getir("SELECT tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay FROM cozumler ORDER BY id DESC")
            
            if raporlar:
                for r in raporlar:
                    with st.expander(f"📅 {r[0]} | {r[1]} - {r[2]} ({r[5]} Yanlış)"):
                        st.write(f"**Toplam Çözülen:** {r[3]} | **Doğru:** {r[4]} | **Yanlış:** {r[5]}")
                        st.warning(f"💡 **Oğlunun Notu / Anlamadığı Yer:** {r[6]}")
            else:
                st.info("Henüz girilmiş bir soru çözüm analizi bulunmuyor.")

# ----------------- 2. ÖĞRENCİ PANELİ -----------------
else:
    st.header("📱 LGS Dijital Soru Çözüm ve Analiz Paneli")
    bugun = datetime.now().strftime('%Y-%m-%d')
    
    # Bugünün hedeflerini çek
    bugunun_hedefleri = veri_getir("SELECT ders, hedef_soru FROM hedefler WHERE tarih = ?", (bugun,))
    
    st.subheader(f"📅 Bugünün Hedefleri ({bugun})")
    if bugunun_hedefleri:
        for h in bugunun_hedefleri:
            st.info(f"📚 **{h[0]}:** Bugün en az **{h[1]}** soru çözmelisin.")
            
        st.divider()
        st.subheader("✏️ Çözdüğün Soruları ve Yanlışlarını Gir")
        
        ders_listesi = [h[0] for h in bugunun_hedefleri]
        secilen_ders_ogrenci = st.selectbox("Hangi Dersin Analizini Gireceksin?", ders_listesi)
        
        konular = veri_getir("SELECT konu_adi FROM konular WHERE ders = ?", (secilen_ders_ogrenci,))
        konu_listesi = [k[0] for k in konular] if konular else ["Genel Tekrar"]
        secilen_konu = st.selectbox("Hangi Konuyu Çözdün?", konu_listesi)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            toplam = st.number_input("Toplam Çözülen Soru", min_value=1, value=30)
        with col2:
            dogru = st.number_input("Doğru Sayısı", min_value=0, value=25)
        with col3:
            yanlis = st.number_input("Yanlış Sayısı", min_value=0, value=5)
            
        anlasilmayan = st.text_area("Bu konuda tam olarak nerede zorlandın? Hata yaptığın sorular neyle ilgiliydi?", 
                                     placeholder="Örn: Paragrafta ana düşünceyi bulurken iki şık arasında kalıyorum.")
        
        if st.button("Çalışmayı Tamamla ve Babama Gönder 🚀"):
            veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (bugun, secilen_ders_ogrenci, secilen_konu, toplam, dogru, yanlis, anlasilmayan))
            st.success("Harika iş çıkardın! Analizlerin başarıyla kaydedildi ve babana iletildi. 👍")
            
    else:
        st.success("🎉 Bugün için tanımlanmış bir hedefin yok! Dinlenebilir veya geçmiş eksiklerine göz atabilirsin.")