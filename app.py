import streamlit as st
import sqlite3
from datetime import datetime
import google.generativeai as genai
import plotly.graph_objects as go
import os
import random
from streamlit_drawable_canvas import st_canvas

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Şampiyonun LGS Karargâhı")

DOGRU_SIFRE = "1234"

# 🔑 GERÇEK APİ ANAHTARI "AIzaSy" İLE BAŞLAMALIDIR. 
# Eğer aşağıya gerçek anahtarı yazarsan sistem CANLI moda geçer, yazmazsan GÜVENLİ OFFLINE havuzu kullanır.
API_ANAHTARI = "AQ.Ab8RN6LDAlrgDC_ME8tmHaHL-vAIaTT88xhhR8MekLo7Cw7tjQ"

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

# ==========================================
# 📦 ZENGİN VE GARANTİLİ LGS SORU HAVUZU (Offline Mod)
# ==========================================
OFFLINE_HAVUZ = {
    "Matematik": [
        {"konu": "Çarpanlar ve Katlar", "soru": "Kenar uzunlukları 12 cm ve 18 cm olan kartlar yan yana dizilerek bir kare oluşturulacaktır. Bu iş için en az kaç kart gerekir?", "A": "4", "B": "6", "C": "9", "D": "12", "cevap": "B", "cozum": "💡 12 ve 18'in en küçük ortak katı (EKOK) 36'dır. Kare kenarı 36 cm olmalıdır. (36/12) * (36/18) = 3 * 2 = 6 kart gerekir."},
        {"konu": "Üslü İfadeler", "soru": "2^5 ile 5^5 sayılarının çarpımı kaç basamaklı bir sayıdır?", "A": "5", "B": "6", "C": "7", "D": "8", "cevap": "B", "cozum": "💡 Üsler aynı olduğunda tabanlar çarpılır: 2^5 * 5^5 = 10^5 olur. Bu sayı 1'in yanına 5 sıfır eklenmesiyle oluşur, yani 6 basamaklıdır."}
    ],
    "Türkçe": [
        {"konu": "Sözcükte Anlam", "soru": "'Ağır' sözcüğü aşağıdaki cümlelerin hangisinde 'sorumluluğu çok olan, çetin' anlamında kullanılmıştır?", "A": "Bu çuval çok ağır, taşıyamadım.", "B": "Yeni dönemde bize çok ağır bir görev verdiler.", "C": "Yaşlı adam ağır adımlarla yürüyordu.", "D": "Koridorda çok ağır bir koku vardı.", "cevap": "B", "cozum": "💡 'Ağır görev' çetin, sorumluluğu yüksek ve zorlu işler için kullanılan mecaz bir anlamdır."},
        {"konu": "Cümlede Anlam", "soru": "Aşağıdaki cümlelerin hangisinde 'öznel' bir anlatım söz konusudur?", "A": "Yazarın son kitabı dün akşam piyasaya çıktı.", "B": "Türkiye'nin başkenti Ankara'dır.", "C": "Bu film, izlediğim en sürükleyici ve harika yapımdı.", "D": "Kitap toplamda 120 sayfadan oluşuyor.", "cevap": "C", "cozum": "💡 'Sürükleyici ve harika' ifadeleri kişisel beğeni içerdiği için özneldir; diğer şıklar ise kanıtlanabilir nesnel yargılardır."}
    ],
    "Fen Bilimleri": [
        {"konu": "Mevsimler ve İklim", "soru": "21 Haziran tarihinde Kuzey Yarım Küre'de hangi mevsimin başlangıcı yaşanır?", "A": "İlkbahar", "B": "Yaz", "C": "Sonbahar", "D": "Kış", "cevap": "B", "cozum": "💡 21 Haziran'da Kuzey Yarım Küre Güneş ışınlarını en dik açıyla alır ve en uzun gündüzü yaşayarak Yaz mevsimine başlar."}
    ],
    "İnkılap Tarihi": [
        {"konu": "Bir Kahraman Doğuyor", "soru": "Mustafa Kemal'in fikir hayatının oluşmasında aşağıdaki şehirlerden hangisi doğrudan etkili olmamıştır?", "A": "Selanik", "B": "Manastır", "C": "İstanbul", "D": "Londra", "cevap": "D", "cozum": "💡 Mustafa Kemal Selanik, Manastır, Sofya ve İstanbul'da eğitim görüp görev yapmıştır. Londra'nın fikir hayatı üzerinde doğrudan bir etkisi yoktur."}
    ],
    "İngilizce": [
        {"konu": "Friendship", "soru": "Choose the best option: 'A true friend always ______ you when you need help.'", "A": "argues", "B": "backs up", "C": "lies", "D": "refuses", "cevap": "B", "cozum": "💡 'Back up' arkasında durmak, desteklemek anlamına gelir. Gerçek bir dost yardım gerektiğinde destek olur."}
    ],
    "Din Kültürü": [
        {"konu": "Kader ve Kaza", "soru": "Aşağıdakilerden hangisi insanın cüzi iradesi (kendi özgür seçimi) kapsamında değerlendirilir?", "A": "Doğum yeri", "B": "Meslek seçimi", "C": "Göz rengi", "D": "Ölüm tarihi", "cevap": "B", "cozum": "💡 İnsanın kendi kararlarıyla seçebildiği eylemler (meslek, iyilik/kötülük) cüzi iradedir; doğum veya ölüm gibi müdahale edemediği alanlar ise külli iradedir."}
    ]
}

# Veritabanı Modülleri
def veri_getir(query, params=()):
    conn = sqlite3.connect('lgs_takip.db')
    cursor = conn.columns if False else conn.cursor()
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

# Akıllı Soru Üretim Motoru (Çökmeyen Hibrit Sistem)
def ai_soru_uret_ve_temizle(ders, adet=5):
    # Eğer geçerli bir API anahtarı girilmediyse doğrudan offline zengin havuzu kullanır
    if not API_ANAHTARI.startswith("AIzaSy"):
        havuz = OFFLINE_HAVUZ.get(ders, OFFLINE_HAVUZ["Matematik"])
        if len(havuz) < adet:
            return havuz
        return random.sample(havuz, adet)
        
    try:
        genai.configure(api_key=API_ANAHTARI)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Sen Türkiye MEB müfredat uzmanı bir LGS öğretmenisin.
        Sadece Türkiye MEB 7. Sınıf {ders} müfredatına bağlı kalarak {adet} adet LGS tarzı yeni nesil soru hazırla.
        Her sorunun başına tam olarak 'SORU_BASLA' ifadesini koy.
        Aşağıdaki formata harfiyen uy:
        
        SORU_BASLA
        KONU: [Konu Adı]
        SORU: [Soru Metni]
        A: [A Şıkkı]
        B: [B Şıkkı]
        C: [C Şıkkı]
        D: [D Şıkkı]
        CEVAP: [Sadece A, B, C veya D harfi]
        COZUM: [Çözüm açıklaması]
        """
        response = model.generate_content(prompt)
        metin = response.text
        
        bloklar = metin.split("SORU_BASLA")
        sonuclar = []
        
        for blok in bloklar:
            if "SORU:" in blok and "CEVAP:" in blok:
                satirlar = [s.strip() for s in blok.strip().split("\n") if s.strip()]
                obj = {"konu": "Genel Tekrar", "soru": "Soru yüklenemedi.", "A": "", "B": "", "C": "", "D": "", "cevap": "A", "cozum": "Çözüm mevcut değil."}
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
                    
        if len(sonuclar) == 0:
            return OFFLINE_HAVUZ.get(ders, OFFLINE_HAVUZ["Matematik"])
        return sonuclar
    except:
        # En ufak bir hatada bile sistem donmaz, offline havuzdan soruları getirir
        return OFFLINE_HAVUZ.get(ders, OFFLINE_HAVUZ["Matematik"])

# State Yönetimi
if "soru_paketi" not in st.session_state: st.session_state.soru_paketi = {}
if "aktif_index" not in st.session_state: st.session_state.aktif_index = {}
if "kontrol_edildi" not in st.session_state: st.session_state.kontrol_edildi = {}
if "veli_secilen_ders" not in st.session_state: st.session_state.veli_secilen_ders = TUM_DERSLER[0]
if "aktif_calisilan_ders" not in st.session_state: st.session_state.aktif_calisilan_ders = None

# Başlık Alanı
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
    if not st.session_state.get("veli_giris_yapildi"):
        girilen_sifre = st.text_input("Giriş Şifresi:", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if girilen_sifre == DOGRU_SIFRE: 
                st.session_state.veli_giris_yapildi = True
                st.rerun()
            else: 
                st.error("❌ Hatalı şifre!")
    else:
        if st.button("🔒 Paneli Kilitle"):
            st.session_state.veli_giris_yapildi = False
            st.rerun()
            
        tab1, tab2 = st.tabs(["📊 Durum Grafiği", "🎯 Hedef Belirle"])
        with tab1:
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
                    go.Bar(name='Hedef', x=dersler_list, y=[grafik_haritasi[d]["hedef"] for d in dersler_list], marker_color='#1f77b4'),
                    go.Bar(name='Doğru', x=dersler_list, y=[grafik_haritasi[d]["dogru"] for d in dersler_list], marker_color='green'),
                    go.Bar(name='Yanlış', x=dersler_list, y=[grafik_haritasi[d]["yanlis"] for d in dersler_list], marker_color='red')
                ])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Henüz veri yok.")
        with tab2:
            tarih = st.date_input("Tarih", datetime.now()).strftime('%Y-%m-%d')
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
            st.session_state.aktif_calisilan_ders = d
            if d not in st.session_state.soru_paketi:
                with st.spinner("Sorular güvenli modda hazırlanıyor... ⏳"):
                    cevap = ai_soru_uret_ve_temizle(d, adet=hedef_adetler[d])
                    if cevap:
                        st.session_state.soru_paketi[d] = cevap
                        st.session_state.aktif_index[d] = 0
                        st.session_state.kontrol_edildi[d] = [False] * len(cevap)
                        st.rerun()

    if st.session_state.aktif_calisilan_ders and st.session_state.aktif_calisilan_ders in st.session_state.soru_paketi:
        ders = st.session_state.aktif_calisilan_ders
        havuz = st.session_state.soru_paketi.get(ders, [])
        idx = st.session_state.aktif_index.get(ders, 0)
        
        if idx < len(havuz):
            soru = havuz[idx]
            st.write("")
            st.info(f"📖 Şu an Çalışılan Ders: {ders} | Soru {idx + 1} / {len(havuz)} | Konu: {soru.get('konu')}")
            
            col_s, col_c = st.columns([1, 1])
            with col_s:
                st.markdown(f"#### {soru.get('soru')}")
                secenek = st.radio(
                    "Cevabını Seç:",
                    [f"A) {soru.get('A')}", f"B) {soru.get('B')}", f"C) {soru.get('C')}", f"D) {soru.get('D')}"],
                    index=None, key=f"r_inline_{ders}_{idx}"
                )
                
                is_checked = st.session_state.kontrol_edildi[ders][idx]
                if not is_checked:
                    if st.button("Cevabı Kontrol Et 🚀", key=f"chk_inline_{ders}_{idx}", type="primary", use_container_width=True):
                        if secenek is None:
                            st.warning("Lütfen bir şık seçin!")
                        else:
                            st.session_state.kontrol_edildi[ders][idx] = True
                            s_harf = secenek[0]
                            d_harf = soru.get('cevap', 'A').strip().upper()
                            
                            if s_harf == d_harf:
                                veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 1, 0, '')", (bugun, ders, soru.get('konu')))
                            else:
                                veri_kaydet("INSERT INTO cozumler (tarih, ders, konu_adi, toplam_cozulen, dogru_sayisi, yanlis_sayisi, anlasilmayan_detay) VALUES (?, ?, ?, 1, 0, 1, ?)", (bugun, ders, soru.get('konu'), f"Hata: {s_harf} seçildi"))
                            st.rerun()
                else:
                    st.markdown("---")
                    s_harf = secenek[0] if secenek else ""
                    d_harf = soru.get('cevap', 'A').strip().upper()
                    if s_harf == d_harf:
                        st.success(f"🎉 Doğru! {soru.get('cozum')}")
                    else:
                        st.error(f"❌ Yanlış! Doğru Cevap: {d_harf}")
                        st.warning(soru.get('cozum', 'Çözüm açıklaması mevcut değil.'))
                    
                    st.write("")
                    if idx < len(havuz) - 1:
                        if st.button("Sıradaki Soruya Geç ➡️", key=f"next_inline_{ders}_{idx}", use_container_width=True):
                            st.session_state.aktif_index[ders] += 1
                            st.rerun()
                    else:
                        st.balloons()
                        st.success("🏆 Harika! Bu dersin tüm sorularını başarıyla bitirdin!")
                        if st.button("🏁 Dersi Bitir ve Kapat", key=f"close_inline_{ders}", type="primary", use_container_width=True):
                            st.session_state.aktif_calisilan_ders = None
                            st.rerun()
            with col_c:
                st.caption("✏️ Karalama Tahtası:")
                firca = st.slider("Kalem Kalınlığı", 1, 10, 3, key=f"br_inline_{ders}_{idx}")
                st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=firca, stroke_color="#000000", background_color="#eeeeee", height=380, drawing_mode="freedraw", key=f"can_inline_{ders}_{idx}")
                
    if not hedef_adetler:
        st.success("🎉 Bugünlük atanmış bir görevin yok, harika!")