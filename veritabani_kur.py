import sqlite3

def veritabani_olustur():
    conn = sqlite3.connect('lgs_takip.db')
    cursor = conn.cursor()
    
    # 1. Konular Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS konular (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ders TEXT,
        konu_adi TEXT
    )
    ''')
    
    # 2. Veli Günlük Hedefler Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hedefler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        ders TEXT,
        hedef_soru INTEGER
    )
    ''')
    
    # 3. Öğrenci Çözüm ve Hata Analizi Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cozumler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        ders TEXT,
        konu_adi TEXT,
        toplam_cozulen INTEGER,
        dogru_sayisi INTEGER,
        yanlis_sayisi INTEGER,
        anlasilmayan_detay TEXT
    )
    ''')
    
    # Örnek birkaç Türkçe konusu ekleyelim
    ornek_konular = [
        ('Türkçe', 'Sözcükte Anlam'),
        ('Türkçe', 'Cümlede Anlam'),
        ('Türkçe', 'Paragrafta Anlam'),
        ('Türkçe', 'Dil Bilgisi')
    ]
    
    cursor.executemany('INSERT INTO konular (ders, konu_adi) VALUES (?, ?)', ornek_konular)
    
    conn.commit()
    conn.close()
    print("Veri tabanı ve örnek konular başarıyla oluşturuldu!")

if __name__ == "__main__":
    veritabani_olustur()