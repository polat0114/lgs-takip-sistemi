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

# API Anahtarı Yapılandırması
API_ANAHTARI = "AQ.Ab8RN6L3jbuS0MBwPk3gD7dPJFIwan507hx-LONL8E_4dDi_Aw"
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

# ==========================================
# 📦 SARSILMAZ VE GENİŞLETİLMİŞ YEREL LGS SORU BANKASI
# ==========================================
YENI_NESIL_SORU_BANKASI = {
    "Matematik": [
        {"konu": "Çarpanlar ve Katlar", "soru": "Kenar uzunlukları 12 cm ve 18 cm olan kartlar yan yana dizilerek bir kare oluşturulacaktır. Bu iş için en az kaç kart gerekir?", "A": "4", "B": "6", "C": "9", "D": "12", "cevap": "B", "cozum": "💡 12 ve 18'in en küçük ortak katı (EKOK) 36'dır. Kare kenarı 36 cm olmalıdır. (36/12) * (36/18) = 3 * 2 = 6 kart gerekir."},
        {"konu": "Üslü İfadeler", "soru": "2^5 ile 5^5 sayılarının çarpımı kaç basamaklı bir sayıdır?", "A": "5", "B": "6", "C": "7", "D": "8", "cevap": "B", "cozum": "💡 Üsler aynı olduğunda tabanlar çarpılır: 2^5 * 5^5 = 10^5 olur. Bu sayı 6 basamaklıdır."},
        {"konu": "Tam Sayılar", "soru": "(-5) + (+8) * (-2) işleminin sonucu kaçtır?", "A": "-21", "B": "-11", "C": "-6", "D": "11", "cevap": "A", "cozum": "💡 Önce çarpma yapılır: (+8) * (-2) = -16. Sonra toplama: (-5) + (-16) = -21."},
        {"konu": "Rasyonel Sayılar", "soru": "1/2 + 2/3 işleminin sonucu aşağıdakilerden hangisidir?", "A": "3/5", "B": "5/6", "C": "7/6", "D": "1", "cevap": "C", "cozum": "💡 Paydalar 6'da eşitlenir: (3/6) + (4/6) = 7/6 olur."},
        {"konu": "Cebirsel İfadeler", "soru": "3x + 5 = 20 denklemini sağlayan x değeri kaçtır?", "A": "3", "B": "4", "C": "5", "D": "6", "cevap": "C", "cozum": "💡 5 karşıya eksi geçer: 3x = 15. Her iki taraf 3'e bölünürse x = 5 bulunur."},
        {"konu": "Doğrusal Denklemler", "soru": "Bir taksinin açılış ücreti 10 TL ve gidilen her kilometre için 5 TL alınmaktadır. 40 TL ödeyen bir kişi kaç km gitmiştir?", "A": "5", "B": "6", "C": "7", "D": "8", "cevap": "B", "cozum": "💡 40 - 10 = 30 TL km ücretidir. 30 / 5 = 6 km yol gidilmiştir."}
    ],
    "Türkçe": [
        {"konu": "Sözcükte Anlam", "soru": "'Ağır' sözcüğü aşağıdaki cümlelerin hangisinde 'sorumluluğu çok olan, çetin' anlamında kullanılmıştır?", "A": "Bu çuval çok ağır, taşıyamadım.", "B": "Yeni dönemde bize çok ağır bir görev verdiler.", "C": "Yaşlı adam ağır adımlarla yürüyordu.", "D": "Koridorda çok ağır bir koku vardı.", "cevap": "B", "cozum": "💡 'Ağır görev' çetin, sorumluluğu yüksek işler için kullanılan mecaz bir anlamdır."},
        {"konu": "Cümlede Anlam", "soru": "Aşağıdaki cümlelerin hangisinde 'öznel' bir anlatım söz konusudur?", "A": "Yazarın son kitabı dün akşam piyasaya çıktı.", "B": "Türkiye'nin başkenti Ankara'dır.", "C": "Bu film, izlediğim en sürükleyici ve harika yapımdı.", "D": "Kitap toplamda 120 sayfadan oluşuyor.", "cevap": "C", "cozum": "💡 'Sürükleyici ve harika' ifadeleri kişisel beğeni içerdiği için özneldir."},
        {"konu": "Paragrafta Anlam", "soru": "Aşağıdakilerden hangisi bir paragrafın giriş cümle çizgisine uymaya en uygundur?", "A": "Bu yüzden kitap okumak çok önemlidir.", "B": "Kitaplar, insanlığın ortak hafızasıdır.", "C": "Oysa bu durum her zaman böyle gerçekleşmez.", "D": "Kısacası, başarıya giden yol çalışmaktan geçer.", "cevap": "B", "cozum": "💡 Giriş cümleleri kendinden önce bir düşünce olduğunu hissettiren bağlayıcı sözcükler içermez."},
        {"konu": "Yazım Kuralları", "soru": "Aşağıdaki cümlelerin hangisinde yazım hatası yapılmıştır?", "A": "Ankara'da havalar ısınmaya başladı.", "B": "Herşey yolunda gidiyor.", "C": "Bunu sen mi söyledin?", "D": "29 Ekim Cumhuriyet Bayramı kutlu olsun.", "cevap": "B", "cozum": "💡 'Her şey' sözcüğü her zaman ayrı yazılır. 'Herşey' yazımı hatalıdır."},
        {"konu": "Noktalama İşaretleri", "soru": "Pazardan elma ( ) armut ve muz aldım. Cümlesinde parantez içine hangi işaret gelmelidir?", "A": ", (Virgül)", "B": "; (Noktalı Virgül)", "C": ". (Nokta)", "D": ": (İki Nokta)", "cevap": "A", "cozum": "💡 Eş görevli sözcükleri ayırmak için virgül kullanılır."}
    ],
    "Fen Bilimleri": [
        {"konu": "Mevsimler ve İklim", "soru": "21 Haziran tarihinde Kuzey Yarım Küre'de hangi mevsimin başlangıcı yaşanır?", "A": "İlkbahar", "B": "Yaz", "C": "Sonbahar", "D": "Kış", "cevap": "B", "cozum": "💡 21 Haziran'da Kuzey Yarım Küre Güneş ışınlarını en dik açıyla alır ve Yaz başlar."},
        {"konu": "DNA ve Genetik Kod", "soru": "DNA'nın yapı birimi aşağıdakilerden hangisidir?", "A": "Gen", "B": "Kromozom", "C": "Nükleotid", "D": "Organel", "cevap": "C", "cozum": "💡 DNA'nın temel yapı birimi nükleotidlerdir. Görev birimi ise gendir."},
        {"konu": "Sıvı Basıncı", "soru": "Sıvı basıncı aşağıdakilerden hangisine bağlı değildir?", "A": "Sıvının yoğunluğuna", "B": "Sıvının derinliğine", "C": "Kabın şekline", "D": "Yer çekimi ivmesine", "cevap": "C", "cozum": "💡 Sıvı basıncı derinlik ve yoğunluğa bağlıdır, kabın şekline veya sıvı miktarına bağlı değildir."}
    ],
    "İnkılap Tarihi": [
        {"konu": "Bir Kahraman Doğuyor", "soru": "Mustafa Kemal'in fikir hayatının oluşmasında aşağıdaki şehirlerden hangisi doğrudan etkili olmamıştır?", "A": "Selanik", "B": "Manastır", "C": "İstanbul", "D": "Londra", "cevap": "D", "cozum": "💡 Mustafa Kemal Londra'da eğitim hayatı geçirmemiştir veya görev almamıştır."},
        {"konu": "Milli Uyanış", "soru": "I. Dünya Savaşı'nın çıkmasında etkili olan sömürgecilik yarışı hangi olayla hız kazanmıştır?", "A": "Fransız İhtilali", "B": "Sanayi İnkılabı", "C": "Coğrafi Keşifler", "D": "Rönesans", "cevap": "B", "cozum": "💡 Sanayi İnkılabı ile birlikte hammadde ve pazar arayışı (sömürgecilik) hızlanmıştır."}
    ],
    "İngilizce": [
        {"konu": "Friendship", "soru": "Choose the best option: 'A true friend always ______ you when you need help.'", "A": "argues", "B": "backs up", "C": "lies", "D": "refuses", "cevap": "B", "cozum": "💡 'Back up' desteklemek anlamına gelir."},
        {"konu": "Teen Life", "soru": "Selin loves nature. She prefers going ______ in her free time.", "A": "camping", "B": "shopping", "C": "skydiving", "D": "bowling", "cevap": "A", "cozum": "💡 Doğa sevgisiyle en uyumlu aktivite kamp yapmaktır (camping)."}
    ],
    "Din Kültürü": [
        {"konu": "Kader ve Kaza", "soru": "Aşağıdakilerden hangisi insanın cüzi iradesi (kendi özgür seçimi) kapsamındadır?", "A": "Doğum yeri", "B": "Meslek seçimi", "C": "Göz rengi", "D": "Ölüm tarihi", "cevap": "B", "cozum": "💡 Meslek seçimi insanın kendi iradesi ve seçimidir; fiziksel özellikler külli iradedir."},
        {"konu": "Zekat ve Sadaka", "soru": "İslam dinine göre nisap miktarı mala sahip olan zengin bir Müslümanın yılda bir kez vermesi farz olan ibadet hangisidir?", "A": "Sadaka", "B": "Zekat", "C": "Fitre", "D": "Fidye", "cevap": "B", "cozum": "💡 Nisap miktarı mala sahip olanların yılda bir kez vermesi farz olan mali ibadet zekattır."}
    ]
}

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

# Kurşun Geçirmez Akıllı Soru Seçim Motoru (Asla Çökmez)
def ai_soru_uret_ve_temizle(ders, adet=5):
    # Veritabanından Poyraz Efe'nin yanlış yaptığı konuları çekip inceliyoruz
    yanlislar = veri_getir("SELECT DISTINCT konu_adi FROM cozumler WHERE ders = ? AND yanlis_sayisi > 0", (ders,))
    yanlis_konular = [y[0] for y in yanlislar if y[0]]
    
    konu_puanlama_ve_stresi = ""
    if yanlis_konular:
        konu_puanlama_ve_stresi = f"\nÖNEMLİ: Öğrenci daha önce şu konularda yanlış yapmıştır: {', '.join(yanlis_konular)}. Bu konuları pekiştirecek benzer tarzda mantık muhakeme sorularına ağırlık ver."

    # Önce canlı yapay zekayı güvenli bir şekilde dener
    if API_ANAHTARI and API_ANAHTARI.startswith("AIzaSy"):
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
            if sonuclar:
                return sonuclar
        except:
            pass # Canlı modda bir yetkilendirme veya bağlantı hatası olursa sessizce yerel bankaya geçer

    # 🎯 YEREL HAVUZ SİSTEMİ: API çalışmazsa ekrana hata basmak yerine doğrudan buradaki geniş bankayı süzüp adet kadar teslim eder
    havuz = YENI_NESIL_SORU_BANKASI.get(ders, YENI_NESIL_SORU_BANKASI["Matematik"])
    
    # Poyraz Efe'nin yanlış yaptığı konular varsa, o soruları listenin başına çekerek pekiştirme sağlar
    oncelikli_havuz = [s for s in havuz if s["konu"] in yanlis_konular]
    normal_havuz = [s for s in havuz if s["konu"] not in yanlis_konular]
    
    sirali_havuz = oncelikli_havuz + normal_havuz
    if len(sirali_havuz) < adet:
        return sirali_havuz
    return random.sample(sirali_havuz, adet)

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
                if st.button("⬅️ Önceki", key=f"p_pop_{ders}_{idx}", use_container_width=True):
                    st.session_state.aktif_index[ders] -= 1
                    st.rerun()
        with col_orta:
            st.info(f"📌 Soru {idx + 1} / {len(havuz)} | Ders: {ders} | Konu: {soru.get('konu')}")
        with col_sag:
            if idx < len(havuz) - 1:
                if st.button("Sonraki ➡️", key=f"n_pop_{ders}_{idx}", use_container_width=True):
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

# --- ANA BAŞLIK ---
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
                with st.spinner("Sorular güvenli karargâh havuzundan hazırlanıyor... ⏳"):
                    cevap = ai_soru_uret_ve_temizle(d, adet=hedef_adetler[d])
                    if cevap:
                        st.session_state.soru_paketi[d] = cevap
                        st.session_state.aktif_index[d] = 0
                        st.session_state.kontrol_edildi[d] = [False] * len(cevap)
            st.rerun()

    # Pop-up Tetikleme Alanı
    if st.session_state.show_popup_ders and st.session_state.show_popup_ders in st.session_state.soru_paketi:
        pop_up_pencere(st.session_state.show_popup_ders, bugun)
                
    if not hedef_adetler:
        st.success("🎉 Bugünlük atanmış bir görevin yok, harika!")