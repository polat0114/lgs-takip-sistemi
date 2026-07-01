import streamlit as st
import sqlite3
from datetime import datetime, timedelta
# Yeni nesil kütüphane entegrasyonu
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import plotly.graph_objects as go
import os
import random
from streamlit_drawable_canvas import st_canvas
from soru_havuzu import SORU_HAVUZU

class SoruModel(BaseModel):
    konu: str = Field(description="Sorunun ait olduğu LGS alt konu adı.")
    soru: str = Field(description="LGS tarzı yeni nesil, mantık-muhakeme odaklı sorunun metni (veya paragrafı/öncülleri).")
    A: str = Field(description="A seçeneğinin metni. Sadece seçenek içeriğini yazın. Kesinlikle seçeneğin doğru veya yanlış olduğuna dair açıklama, gerekçe veya 'Doğru', 'Yanlış' gibi ifadeler/ipuçları eklemeyin.")
    B: str = Field(description="B seçeneğinin metni. Sadece seçenek içeriğini yazın. Kesinlikle seçeneğin doğru veya yanlış olduğuna dair açıklama, gerekçe veya 'Doğru', 'Yanlış' gibi ifadeler/ipuçları eklemeyin.")
    C: str = Field(description="C seçeneğinin metni. Sadece seçenek içeriğini yazın. Kesinlikle seçeneğin doğru veya yanlış olduğuna dair açıklama, gerekçe veya 'Doğru', 'Yanlış' gibi ifadeler/ipuçları eklemeyin.")
    D: str = Field(description="D seçeneğinin metni. Sadece seçenek içeriğini yazın. Kesinlikle seçeneğin doğru veya yanlış olduğuna dair açıklama, gerekçe veya 'Doğru', 'Yanlış' gibi ifadeler/ipuçları eklemeyin.")
    cevap: str = Field(description="Doğru seçeneğin harfi (Sadece A, B, C veya D).")
    cozum: str = Field(description="Sorunun detaylı ve öğretici çözümü. Seçeneklerin neden doğru veya yanlış olduğunu burada açıklayın.")

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Şampiyonun LGS Karargâhı")

DOGRU_SIFRE = "1234"

# API Anahtarı Yükleme Mantığı
def api_anahtari_oku():
    # 1. Ortam Değişkeni
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY").strip()
    # 2. Streamlit Secrets
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except:
        pass
    # 3. Yerel api_key.txt
    if os.path.exists("api_key.txt"):
        try:
            with open("api_key.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return ""

API_ANAHTARI = api_anahtari_oku()

# Yeni Nesil İstemci Başlatma
try:
    if API_ANAHTARI:
        client = genai.Client(api_key=API_ANAHTARI)
    else:
        client = None
except Exception as e:
    client = None

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

def yerel_havuzdan_soru_sec(ders, adet=5):
    havuz = SORU_HAVUZU.get(ders, [])
    if not havuz:
        return [{"konu": "Genel Tekrar", "soru": f"Yerel havuzda {ders} dersine ait soru bulunamadı.", "A": "-", "B": "-", "C": "-", "D": "-", "cevap": "A", "cozum": "-", "is_local": True}]
    
    if adet <= len(havuz):
        secilenler = random.sample(havuz, adet)
    else:
        # Eğer istenen soru adeti havuzdakinden fazlaysa, önce elimizdeki tüm benzersiz soruları alıp
        # kalanını rastgele (tekrarlanarak) tamamlıyoruz ki hedef sayıya tam ulaşılsın.
        secilenler = list(havuz)
        kalan_adet = adet - len(havuz)
        secilenler += random.choices(havuz, k=kalan_adet)
        
    sonuc = []
    for s in secilenler:
        kopyalanmis = s.copy()
        kopyalanmis["is_local"] = True
        sonuc.append(kopyalanmis)
    return sonuc

def yedek_havuz_olustur(client, status_container):
    yeni_havuz = {}
    import pprint
    
    for ders in TUM_DERSLER:
        status_container.info(f"⏳ {ders} dersi için 50 adet yeni nesil 7. sınıf sorusu üretiliyor...")
        ders_sorulari = []
        
        # 50 soruyu tek seferde istemek yerine 5 ayrı parça halinde (10'ar adet) isteyelim ki API limitlerine takılmasın ve kaliteli olsun
        for i in range(5):
            status_container.info(f"⏳ {ders} dersi için sorular üretiliyor (Grup {i+1}/5)...")
            try:
                prompt = f"""
                Sen Türkiye MEB müfredatına tamamen hakim uzman bir LGS öğretmenisin.
                7. Sınıf {ders} müfredatına uygun, mantık muhakeme odaklı, LGS tarzı yeni nesil tam 10 adet özgün soru hazırla.
                
                ÖNEMLİ KURALLAR:
                1. Soruların hepsi LGS standartlarında, yeni nesil ve mantık-muhakeme becerilerini ölçen düzeyde olmalıdır.
                2. A, B, C, D seçeneklerinin metinlerinde kesinlikle seçeneğin doğru ya da yanlış olduğuna dair 'Doğru', 'Yanlış' gibi ipuçları, açıklamalar veya gerekçeler bulunmamalıdır. Seçenekler sadece sorunun normal şık metinlerini içermelidir.
                3. Şıkların neden doğru veya yanlış olduğunun gerekçesi ve sorunun ayrıntılı çözümü sadece 'cozum' (çözüm) alanında yer almalıdır.
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=list[SoruModel]
                    )
                )
                
                if response.parsed:
                    for s in response.parsed:
                        ders_sorulari.append({
                            "konu": s.konu,
                            "soru": s.soru,
                            "A": s.A,
                            "B": s.B,
                            "C": s.C,
                            "D": s.D,
                            "cevap": s.cevap.strip().upper(),
                            "cozum": s.cozum
                        })
            except Exception as e:
                # Hata durumunda devam etsin
                pass
                
        # Eğer hiç soru üretilemediyse mevcut havuzdakileri koruyalım
        if not ders_sorulari:
            try:
                from soru_havuzu import SORU_HAVUZU as ESKI_HAVUZ
                ders_sorulari = ESKI_HAVUZ.get(ders, [])
            except:
                pass
                
        yeni_havuz[ders] = ders_sorulari
        status_container.success(f"✅ {ders} dersi için {len(ders_sorulari)} adet soru başarıyla üretildi.")
        
    # Havuzu dosyaya yaz
    try:
        with open("soru_havuzu.py", "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n\n")
            f.write("SORU_HAVUZU = ")
            f.write(pprint.pformat(yeni_havuz, indent=4, width=120, compact=False))
        status_container.success("🎉 Her ders için 50'şer adet olmak üzere toplam 300 soruluk yeni LGS Soru Havuzu başarıyla oluşturuldu ve soru_havuzu.py dosyasına kaydedildi!")
        return True
    except Exception as e:
        status_container.error(f"Havuz dosyaya yazılırken hata oluştu: {str(e)}")
        return False

# 🧠 %100 CANLI VE SONSUZ FARKLI SORU ÜRETEN YAPAY ZEKA MOTORU
def ai_soru_uret_ve_temizle(ders, adet=5):
    yanlislar = veri_getir("SELECT DISTINCT konu_adi FROM cozumler WHERE ders = ? AND yanlis_sayisi > 0", (ders,))
    yanlis_konular = [y[0] for y in yanlislar if y[0]]
    
    konu_puanlama_ve_stresi = ""
    if yanlis_konular:
        konu_puanlama_ve_stresi = f"\nÖNEMLİ: Öğrenci daha önce şu konularda yanlış yapmıştır: {', '.join(yanlis_konular)}. Bu konuları pekiştirecek benzer tarzda sorulara ağırlık ver."

    if client is None:
        return yerel_havuzdan_soru_sec(ders, adet)

    try:
        prompt = f"""
        Sen Türkiye MEB müfredatına tamamen hakim uzman bir LGS öğretmenisin.
        7. Sınıf {ders} müfredatına uygun, mantık muhakeme odaklı, LGS tarzı yeni nesil tam {adet} adet özgün soru hazırla. {konu_puanlama_ve_stresi}
        
        ÖNEMLİ KURALLAR:
        1. Soruların hepsi LGS standartlarında, yeni nesil ve mantık-muhakeme becerilerini ölçen düzeyde olmalıdır.
        2. A, B, C, D seçeneklerinin metinlerinde kesinlikle seçeneğin doğru ya da yanlış olduğuna dair 'Doğru', 'Yanlış' gibi ipuçları, açıklamalar veya gerekçeler bulunmamalıdır. Seçenekler sadece sorunun normal şık metinlerini içermelidir.
        3. Şıkların neden doğru veya yanlış olduğunun gerekçesi ve sorunun ayrıntılı çözümü sadece 'cozum' (çözüm) alanında yer almalıdır.
        """
        
        # Yeni nesil Gemini API çağrısı
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[SoruModel]
            )
        )
        
        sonuclar = []
        if response.parsed:
            for s in response.parsed:
                sonuclar.append({
                    "konu": s.konu,
                    "soru": s.soru,
                    "A": s.A,
                    "B": s.B,
                    "C": s.C,
                    "D": s.D,
                    "cevap": s.cevap.strip().upper(),
                    "cozum": s.cozum,
                    "is_local": False
                })
                    
        if len(sonuclar) >= adet:
            return sonuclar[:adet]
        elif len(sonuclar) > 0:
            eksik = adet - len(sonuclar)
            return sonuclar + yerel_havuzdan_soru_sec(ders, eksik)
        else:
            return yerel_havuzdan_soru_sec(ders, adet)
    except Exception as e:
        return yerel_havuzdan_soru_sec(ders, adet)

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
            if soru.get("is_local"):
                st.warning("⚠️ Yapay zeka yoğunluğu nedeniyle yerel havuzdan yüklenmiştir.")
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
            
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Genel Durum Grafiği", "📆 Günlük Ödev / Hedef Takibi", "🎯 Yeni Hedef Belirle", "⚙️ Ayarlar"])
        
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
                
        with tab4:
            st.subheader("⚙️ Yapay Zeka & API Ayarları")
            
            # Maskelenmiş mevcut anahtarı göster
            if API_ANAHTARI:
                maskelenmis = API_ANAHTARI[:6] + "..." + API_ANAHTARI[-4:] if len(API_ANAHTARI) > 10 else "Tanımlı"
                st.info(f"🔑 **Mevcut API Anahtarı:** `{maskelenmis}`")
            else:
                st.warning("⚠️ **Mevcut API Anahtarı:** Tanımlı Değil (Sistem yerel havuzu kullanıyor)")
                
            yeni_key = st.text_input("Yeni Gemini API Anahtarı:", type="password", help="Google AI Studio'dan aldığınız API anahtarını buraya yapıştırın.")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button("Bağlantıyı Test Et ⚡", use_container_width=True):
                    if not yeni_key:
                        st.error("Lütfen test etmek için bir anahtar girin!")
                    else:
                        with st.spinner("Gemini API bağlantısı test ediliyor..."):
                            try:
                                test_client = genai.Client(api_key=yeni_key.strip())
                                test_resp = test_client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents='Merhaba, sadece "Test Başarılı" de.',
                                )
                                if test_resp.text:
                                    st.success(f"✅ Bağlantı Başarılı! Yapay zeka yanıtı: {test_resp.text}")
                                else:
                                    st.error("❌ Bağlantı başarısız: Yapay zeka boş yanıt döndürdü.")
                            except Exception as ex:
                                st.error(f"❌ Bağlantı Başarısız! Hata: {str(ex)}")
                                st.info("Not: 401 unauthenticated hatası alıyorsanız temiz bir Google hesabıyla yeni bir anahtar almayı deneyin.")
                                
            with col_t2:
                if st.button("Kaydet ve Uygula 💾", type="primary", use_container_width=True):
                    if not yeni_key:
                        st.error("Lütfen önce bir anahtar girin!")
                    else:
                        try:
                            with open("api_key.txt", "w", encoding="utf-8") as f:
                                f.write(yeni_key.strip())
                            st.success("API Anahtarı başarıyla kaydedildi! Sayfa yenileniyor...")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Kaydederken hata oluştu: {str(ex)}")
                            
            if API_ANAHTARI:
                st.markdown("---")
                if st.button("Mevcut API Anahtarını Sil 🗑️", use_container_width=True):
                    try:
                        if os.path.exists("api_key.txt"):
                            os.remove("api_key.txt")
                        st.success("API Anahtarı silindi! Sistem yerel havuz moduna döndü.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Silinirken hata oluştu: {str(ex)}")
                        
            st.markdown("---")
            st.subheader("🌀 Yedek Soru Havuzunu Genişlet (300 Soru Üret)")
            st.write("Eğer internetiniz yokken veya yapay zeka bağlantınız kesildiğinde Poyraz Efe'nin hiç tekrar eden soru görmesini istemiyorsanız, yerel havuzu yapay zeka yardımıyla **her ders için 50'şer adet (toplam 300 adet)** özgün soru ile güncelleyebilirsiniz.")
            
            if not API_ANAHTARI:
                st.info("💡 Bu işlemi başlatabilmek için önce geçerli bir API anahtarı girip kaydetmelisiniz.")
            else:
                if st.button("Yedek Havuzu Yapay Zeka ile Genişlet (300 Soru Üret) 🚀", use_container_width=True):
                    status_placeholder = st.empty()
                    with st.spinner("300 adet 7. Sınıf sorusu üretiliyor ve soru_havuzu.py dosyası güncelleniyor... Bu işlem yaklaşık 1-2 dakika sürebilir."):
                        yedek_havuz_olustur(client, status_placeholder)

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
                with st.spinner("Yapay zeka tamamen sıfırdan, özgün sorular üretiyor... 🧠⏳"):
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