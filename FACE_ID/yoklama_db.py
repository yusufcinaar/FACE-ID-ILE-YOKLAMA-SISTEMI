"""
Yoklama Veritabanı Yönetim Modülü
Bu modül, yüz tanıma sistemi için SQLite veritabanı işlemlerini yönetir.
Dersler ve yoklamalar için tablo oluşturma, veri ekleme ve sorgulama işlemlerini içerir.
Ayrıca yoklama sonuçlarını görsel olarak gösteren GUI arayüzünü de sağlar.
"""

import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import random
from datetime import datetime, timedelta
import os

def veritabani_olustur():
    """
    SQLite veritabanını oluşturur ve bağlantıyı döndürür
    
    Returns:
        sqlite3.Connection: Veritabanı bağlantı objesi, hata durumunda None
        
    Not:
        İki ana tablo oluşturulur:
        1. dersler: Ders kayıtlarını tutar (id, tarih, saat)
        2. yoklamalar: Yoklama kayıtlarını tutar (id, ders_id, isim, durum, kayit_saati)
    """
    try:
        conn = sqlite3.connect('yoklama.db')
        cursor = conn.cursor()
        
        # Dersler tablosu oluştur
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dersler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_tarihi DATE NOT NULL,
                ders_saati TIME NOT NULL,
                UNIQUE(ders_tarihi, ders_saati)
            )
        ''')
        
        # Yoklamalar tablosu oluştur (dersler tablosuyla ilişkili)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS yoklamalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_id INTEGER NOT NULL,
                isim TEXT NOT NULL,
                durum TEXT NOT NULL,
                kayit_saati TIME NOT NULL,
                FOREIGN KEY (ders_id) REFERENCES dersler(id),
                UNIQUE(ders_id, isim)
            )
        ''')
        
        conn.commit()
        return conn
    except sqlite3.Error as e:
        print(f"Veritabani hatasi: {e}")
        return None

def yeni_ders_baslat(conn):
    """
    Yeni bir ders kaydı oluşturur
    
    Args:
        conn (sqlite3.Connection): Veritabanı bağlantısı
        
    Returns:
        int: Oluşturulan dersin ID'si, hata durumunda None
        
    Not:
        Mevcut tarih ve saat bilgisiyle yeni bir ders kaydı oluşturur
    """
    try:
        if conn is None:
            print("Veritabani baglantisi kurulamadi")
            return None
            
        cursor = conn.cursor()
        simdi = datetime.now()
        tarih = simdi.strftime('%Y-%m-%d')
        saat = simdi.strftime('%H:%M:%S')
        
        cursor.execute('''
            INSERT INTO dersler (ders_tarihi, ders_saati)
            VALUES (?, ?)
        ''', (tarih, saat))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ders başlatılırken hata olustu: {e}")
        return None

def yoklama_ekle(conn, ders_id, isim, durum):
    """
    Yoklama kaydı ekler veya günceller
    
    Args:
        conn (sqlite3.Connection): Veritabanı bağlantısı
        ders_id (int): Dersin ID'si
        isim (str): Öğrencinin ismi
        durum (str): Yoklama durumu (KATILDI/KATILMADI)
        
    Not:
        Aynı ders ve isim için tekrar kayıt yapılırsa, mevcut kayıt güncellenir
    """
    try:
        if conn is None:
            print("Veritabani baglantisi kurulamadi")
            return
            
        cursor = conn.cursor()
        simdi = datetime.now()
        saat = simdi.strftime('%H:%M:%S')
        
        cursor.execute('''
            INSERT OR REPLACE INTO yoklamalar (ders_id, isim, durum, kayit_saati)
            VALUES (?, ?, ?, ?)
        ''', (ders_id, isim, durum, saat))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Kayit eklenirken hata olustu: {e}")

def yoklama_getir(conn, isim):
    """
    Öğrencinin son 5 dersin yoklama kayıtlarını getirir
    
    Args:
        conn (sqlite3.Connection): Veritabanı bağlantısı
        isim (str): Öğrencinin ismi
        
    Returns:
        list: Yoklama kayıtları listesi, hata durumunda boş liste
        
    Not:
        - Son 5 dersin yoklama kayıtlarını getirir
        - Kayıtlar tarih ve saat bilgisine göre sıralanır
    """
    try:
        if conn is None:
            print("Veritabani baglantisi kurulamadi")
            return []
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.ders_tarihi, d.ders_saati, y.durum, y.kayit_saati
            FROM yoklamalar y
            JOIN dersler d ON y.ders_id = d.id
            WHERE y.isim = ?
            ORDER BY d.ders_tarihi DESC, d.ders_saati DESC
            LIMIT 5
        ''', (isim,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Kayitlar getirilirken hata olustu: {e}")
        return []

def detay_goster(event, tree):
    """
    Seçilen öğrencinin detaylı yoklama bilgilerini gösteren pencereyi açar
    
    Args:
        event: Treeview seçim olayı
        tree: Ana penceredeki Treeview widget'ı
        
    Not:
        - Son 5 dersin yoklama kayıtlarını gösterir
        - Modern ve koyu tema kullanır
        - Durum bilgisi emoji ile gösterilir (✅/❌)
    """
    try:
        item = tree.selection()[0]
        kisi = tree.item(item, "values")[0]
        
        # Detay penceresi oluştur ve yapılandır
        detay_pencere = tk.Toplevel()
        detay_pencere.title(f"Kisi Detayi - {kisi}")
        detay_pencere.geometry("500x300")
        detay_pencere.configure(bg='#0A0E17')  # Koyu tema arka planı
        
        style = ttk.Style()
        style.configure("Detay.TLabel",
                      font=('Arial', 10),
                      padding=5,
                      background='#0A0E17',
                      foreground='#E2E8F0')
        
        style.configure("Custom.TButton",
                       font=('Segoe UI', 11),
                       background='#3B82F6',
                       foreground='white',
                       padding=[15, 8])
        
        style.map("Custom.TButton",
                  background=[('active', '#60A5FA')],
                  foreground=[('active', '#FFFFFF')])
        
        # Treeview stili
        style.configure("Detay.Treeview",
                      background='#1A1F2C',
                      foreground='#E2E8F0',
                      fieldbackground='#1A1F2C',
                      font=('Segoe UI', 10),
                      rowheight=35,
                      borderwidth=0)  # Kenarlık kaldırıldı
        
        style.configure("Detay.Treeview.Heading",
                      background='#1A1F2C',
                      foreground='#60A5FA',
                      font=('Segoe UI', 11, 'bold'),
                      borderwidth=0)  # Kenarlık kaldırıldı
        
        style.map("Detay.Treeview",
                 background=[('selected', '#3B82F6'), ('!selected', '#1A1F2C')],
                 foreground=[('selected', '#FFFFFF'), ('!selected', '#E2E8F0')])
        
        # Üst kısım container
        top_container = ttk.Frame(detay_pencere, style="Dark.TFrame")
        top_container.pack(fill='x', padx=10, pady=5)
        
        # Frame stili
        style.configure("Dark.TFrame", background='#0A0E17')
        
        # Geri butonu
        geri_button = ttk.Button(
            top_container,
            text="← Geri",
            command=detay_pencere.destroy,
            style="Custom.TButton"
        )
        geri_button.pack(side='left')
        
        # Başlık
        baslik_label = tk.Label(
            top_container, 
            text=f"{kisi} - Son 5 Ders Yoklama Kaydi", 
            font=('Segoe UI', 12, 'bold'),
            bg='#0A0E17',
            fg='#E2E8F0'
        )
        baslik_label.pack(side='left', padx=20)
        
        columns = ('Tarih', 'Ders Saati', 'Durum', 'Kayit Saati')
        detay_tree = ttk.Treeview(detay_pencere, columns=columns, show='headings', style="Detay.Treeview")
        
        for col in columns:
            detay_tree.heading(col, text=col)
            detay_tree.column(col, width=120, anchor='center')
        
        conn = sqlite3.connect('yoklama.db')
        kayitlar = yoklama_getir(conn, kisi)
        conn.close()
        
        for kayit in kayitlar:
            tarih, ders_saati, durum, kayit_saati = kayit
            durum_simge = "✅" if durum == "KATILDI" else "❌"
            detay_tree.insert('', 'end', values=(tarih, ders_saati, durum_simge, kayit_saati))
        
        detay_tree.pack(pady=10, padx=10, fill='both', expand=True)
        
    except Exception as e:
        print(f"Detay gosterilirken hata olustu: {e}")

def sonuc_tablosu_goster(yoklama_durumu, ders_id):
    root = tk.Tk()
    root.title("Yoklama Sonuçları")
    root.geometry("1200x800")
    root.configure(bg='#0A0E17')
    
    # Stil ayarları
    style = ttk.Style()
    style.theme_use('clam')
    
    # Ana tema renkleri
    PRIMARY_BG = '#0A0E17'      # Koyu arka plan
    SECONDARY_BG = '#1A1F2C'    # Biraz daha açık arka plan
    ACCENT_COLOR = '#3B82F6'    # Mavi vurgu rengi
    TEXT_COLOR = '#E2E8F0'      # Ana metin rengi
    HIGHLIGHT_COLOR = '#60A5FA'  # Vurgulu metin rengi
    
    # Stil konfigürasyonları
    style.configure("Header.TLabel",
                   font=('Segoe UI', 24, 'bold'),
                   background=PRIMARY_BG,
                   foreground=TEXT_COLOR)
    
    style.configure("Stats.TLabel",
                   font=('Segoe UI', 12),
                   background=PRIMARY_BG,
                   foreground=TEXT_COLOR,
                   padding=5)
    
    style.configure("Custom.TNotebook",
                   background=PRIMARY_BG,
                   borderwidth=0)
    
    style.configure("Custom.TNotebook.Tab",
                   padding=[20, 10],
                   font=('Segoe UI', 11),
                   background=SECONDARY_BG,
                   foreground=TEXT_COLOR)
    
    style.map("Custom.TNotebook.Tab",
              background=[("selected", ACCENT_COLOR)],
              foreground=[("selected", "#FFFFFF")])
    
    style.configure("Custom.Treeview",
                   background=SECONDARY_BG,
                   foreground=TEXT_COLOR,
                   fieldbackground=SECONDARY_BG,
                   font=('Segoe UI', 10),
                   rowheight=35,
                   borderwidth=0)
    
    style.configure("Custom.Treeview.Heading",
                   background=SECONDARY_BG,
                   foreground=HIGHLIGHT_COLOR,
                   font=('Segoe UI', 11, 'bold'),
                   borderwidth=0)
    
    style.map("Custom.Treeview",
              background=[('selected', ACCENT_COLOR), ('!selected', SECONDARY_BG)],
              foreground=[('selected', '#FFFFFF'), ('!selected', TEXT_COLOR)])
    
    # Buton stili
    style.configure("Custom.TButton",
                   font=('Segoe UI', 11),
                   background=ACCENT_COLOR,
                   foreground='white',
                   padding=[15, 8])
    
    style.map("Custom.TButton",
              background=[('active', HIGHLIGHT_COLOR)],
              foreground=[('active', '#FFFFFF')])
    
    # Ana container frame
    main_container = ttk.Frame(root)
    main_container.pack(pady=20, padx=20, fill='both', expand=True)
    
    # Geçmiş Detay butonu
    gecmis_detay_button = ttk.Button(
        main_container,
        text="📋 Geçmiş Yoklamalar",
        command=lambda: gecmis_yoklamalari_goster(),
        style="Custom.TButton"
    )
    gecmis_detay_button.pack(anchor='nw', pady=(0, 20))
    
    # Üst bilgi frame'i
    header_frame = tk.Frame(main_container, bg=PRIMARY_BG)
    header_frame.pack(fill='x', pady=(0, 30))
    
    # Logo/İkon
    logo_label = tk.Label(header_frame,
                         text="📊",
                         font=('Segoe UI', 48),
                         bg=PRIMARY_BG,
                         fg=ACCENT_COLOR)
    logo_label.pack(pady=(0, 15))
    
    # Başlık
    baslik = tk.Label(header_frame,
                     text="YOKLAMA SONUÇLARI",
                     font=('Segoe UI', 28, 'bold'),
                     bg=PRIMARY_BG,
                     fg=TEXT_COLOR)
    baslik.pack()
    
    simdi = datetime.now()
    tarih_saat = tk.Label(header_frame,
                         text=f"{simdi.strftime('%d/%m/%Y %H:%M')}",
                         font=('Segoe UI', 13),
                         bg=PRIMARY_BG,
                         fg=HIGHLIGHT_COLOR)
    tarih_saat.pack(pady=8)
    
    # İstatistik kartları
    stats_frame = tk.Frame(main_container, bg=PRIMARY_BG)
    stats_frame.pack(fill='x', pady=(0, 30))
    
    # İstatistikleri getir
    conn = sqlite3.connect('yoklama.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT d.id) as ders_sayisi,
            SUM(CASE WHEN y.durum = 'KATILDI' THEN 1 ELSE 0 END) as toplam_katilim
        FROM dersler d
        LEFT JOIN yoklamalar y ON d.id = y.ders_id
    ''')
    
    ders_sayisi, toplam_katilim = cursor.fetchone()
    
    # Faces klasöründeki öğrenci sayısını al
    faces_dir = 'faces'
    toplam_ogrenci = len([f for f in os.listdir(faces_dir) if f.endswith(('.jpg', '.JPG', '.png', '.PNG'))])
    
    # İstatistik kartları
    stats = [
        {"title": "Toplam Ders", "value": ders_sayisi, "icon": "📚", "color": HIGHLIGHT_COLOR},
        {"title": "Toplam Öğrenci", "value": toplam_ogrenci, "icon": "👥", "color": "#10B981"},
        {"title": "Toplam Katılım", "value": toplam_katilim or 0, "icon": "✅", "color": "#8B5CF6"}
    ]
    
    for stat in stats:
        card = tk.Frame(stats_frame, bg=SECONDARY_BG)
        card.pack(side='left', fill='x', expand=True, padx=10)
        
        tk.Label(card, text=stat["icon"],
                font=('Segoe UI', 24),
                bg=SECONDARY_BG, fg=stat["color"]).pack()
        
        tk.Label(card, text=stat["title"],
                font=('Segoe UI', 11),
                bg=SECONDARY_BG, fg=TEXT_COLOR).pack(pady=(5,0))
        
        tk.Label(card, text=str(stat["value"]),
                font=('Segoe UI', 20, 'bold'),
                bg=SECONDARY_BG, fg=stat["color"]).pack(pady=(5,15))

    # Notebook (sekmeli görünüm)
    notebook = ttk.Notebook(main_container, style="Custom.TNotebook")
    notebook.pack(expand=True, fill='both', pady=(0, 20))
    
    # Katılanlar sekmesi
    katilan_frame = ttk.Frame(notebook)
    notebook.add(katilan_frame, text='✓ Katılanlar')
    
    katilan_tree = ttk.Treeview(katilan_frame,
                               columns=('Isim', 'Kayit Saati'),
                               show='headings',
                               style="Custom.Treeview")
    katilan_tree.heading('Isim', text='İsim')
    katilan_tree.heading('Kayit Saati', text='Kayıt Saati')
    katilan_tree.column('Isim', width=300, anchor='center')
    katilan_tree.column('Kayit Saati', width=300, anchor='center')
    
    # Katılmayanlar sekmesi
    katilmayan_frame = ttk.Frame(notebook)
    notebook.add(katilmayan_frame, text='✗ Katılmayanlar')
    
    katilmayan_tree = ttk.Treeview(katilmayan_frame,
                                  columns=('Isim', 'Durum'),
                                  show='headings',
                                  style="Custom.Treeview")
    katilmayan_tree.heading('Isim', text='İsim')
    katilmayan_tree.heading('Durum', text='Durum')
    katilmayan_tree.column('Isim', width=300, anchor='center')
    katilmayan_tree.column('Durum', width=300, anchor='center')
    
    # Scrollbar'lar
    katilan_scroll = ttk.Scrollbar(katilan_frame, orient='vertical', command=katilan_tree.yview)
    katilan_tree.configure(yscrollcommand=katilan_scroll.set)
    
    katilmayan_scroll = ttk.Scrollbar(katilmayan_frame, orient='vertical', command=katilmayan_tree.yview)
    katilmayan_tree.configure(yscrollcommand=katilmayan_scroll.set)
    
    # Verileri ağaçlara ekle
    for name, durum in yoklama_durumu.items():
        if durum:
            katilan_tree.insert('', 'end', values=(name, simdi.strftime('%H:%M:%S')))
        else:
            katilmayan_tree.insert('', 'end', values=(name, "Katılmadı"))
    
    # Ağaçları ve scrollbar'ları yerleştir
    katilan_tree.pack(side='left', fill='both', expand=True)
    katilan_scroll.pack(side='right', fill='y')
    
    katilmayan_tree.pack(side='left', fill='both', expand=True)
    katilmayan_scroll.pack(side='right', fill='y')
    
    # Detay görüntüleme için çift tıklama eventi
    katilan_tree.bind('<Double-1>', lambda e: detay_goster(e, katilan_tree))
    katilmayan_tree.bind('<Double-1>', lambda e: detay_goster(e, katilmayan_tree))
    
    # Alt bilgi
    footer_frame = ttk.Frame(main_container, style="Main.TFrame")
    footer_frame.pack(fill='x', pady=10)

    # Geçmiş yoklamaları görüntüleme butonu
    gecmis_button = ttk.Button(
        footer_frame,
        text="Geçmiş Yoklamaları Görüntüle",
        command=lambda: gecmis_yoklamalari_goster(),
        style="Custom.TButton"
    )
    gecmis_button.pack(side='left', padx=20)

    # Footer text
    footer_text = "Yoklama sistemi başarıyla tamamlandı."
    footer_label = tk.Label(footer_frame,
                          text=footer_text,
                          font=('Segoe UI', 10),
                          bg='#0A0E17',
                          fg='#E2E8F0')
    footer_label.pack(side='right', pady=5, padx=20)

    root.mainloop()

def gecmis_yoklamalari_goster():
    root = tk.Tk()
    root.title("Geçmiş Yoklamalar")
    root.geometry("1200x800")
    root.configure(bg='#0A0E17')
    
    # Stil ayarları
    style = ttk.Style()
    style.theme_use('clam')
    
    # Ana tema renkleri
    PRIMARY_BG = '#0A0E17'      # Koyu arka plan
    SECONDARY_BG = '#1A1F2C'    # Biraz daha açık arka plan
    ACCENT_COLOR = '#3B82F6'    # Mavi vurgu rengi
    TEXT_COLOR = '#E2E8F0'      # Ana metin rengi
    HIGHLIGHT_COLOR = '#60A5FA'  # Vurgulu metin rengi
    
    # Treeview stili
    style.configure("Custom.Treeview",
                   background=SECONDARY_BG,
                   foreground=TEXT_COLOR,
                   fieldbackground=SECONDARY_BG,
                   font=('Segoe UI', 11),
                   rowheight=40,
                   borderwidth=0)
    
    style.configure("Custom.Treeview.Heading",
                   background=SECONDARY_BG,
                   foreground=HIGHLIGHT_COLOR,
                   font=('Segoe UI', 12, 'bold'),
                   borderwidth=0)
    
    style.map("Custom.Treeview",
              background=[('selected', ACCENT_COLOR), ('!selected', SECONDARY_BG)],
              foreground=[('selected', '#FFFFFF'), ('!selected', TEXT_COLOR)])
    
    # Buton stili
    style.configure("Custom.TButton",
                   font=('Segoe UI', 11),
                   background=ACCENT_COLOR,
                   foreground='white',
                   padding=[15, 8])
    
    style.map("Custom.TButton",
              background=[('active', HIGHLIGHT_COLOR)],
              foreground=[('active', '#FFFFFF')])
    
    # Ana container frame
    main_container = ttk.Frame(root)
    main_container.pack(fill='both', expand=True, padx=30, pady=20)
    
    # Üst kısım container
    top_container = ttk.Frame(main_container)
    top_container.pack(fill='x', pady=(0, 30))
    
    # Başlık ve tarih container
    header_container = ttk.Frame(top_container)
    header_container.pack(fill='x')
    
    # Logo
    logo_label = tk.Label(header_container,
                         text="📅",
                         font=('Segoe UI', 48),
                         bg=PRIMARY_BG,
                         fg=ACCENT_COLOR)
    logo_label.pack(pady=(0, 15))
    
    # Başlık
    baslik = tk.Label(header_container,
                     text="Geçmiş Yoklamalar",
                     font=('Segoe UI', 28, 'bold'),
                     bg=PRIMARY_BG,
                     fg=TEXT_COLOR)
    baslik.pack()
    
    simdi = datetime.now()
    tarih_saat = tk.Label(header_container,
                         text=f"{simdi.strftime('%d/%m/%Y %H:%M')}",
                         font=('Segoe UI', 13),
                         bg=PRIMARY_BG,
                         fg=HIGHLIGHT_COLOR)
    tarih_saat.pack(pady=8)
    
    # İstatistik kartları için frame
    stats_frame = ttk.Frame(top_container)
    stats_frame.pack(fill='x', pady=20)
    
    # Veritabanı bağlantısı ve istatistikler
    conn = sqlite3.connect('yoklama.db')
    cursor = conn.cursor()
    
    # İstatistikleri getir
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT d.id) as ders_sayisi,
            COUNT(DISTINCT y.isim) as toplam_ogrenci,
            SUM(CASE WHEN y.durum = 'KATILDI' THEN 1 ELSE 0 END) as toplam_katilim
        FROM dersler d
        LEFT JOIN yoklamalar y ON d.id = y.ders_id
    ''')
    
    ders_sayisi, toplam_ogrenci, toplam_katilim = cursor.fetchone()
    
    # İstatistik kartları
    stats = [
        {"title": "Toplam Ders", "value": ders_sayisi, "icon": "📚", "color": HIGHLIGHT_COLOR},
        {"title": "Toplam Öğrenci", "value": toplam_ogrenci or 0, "icon": "👥", "color": "#10B981"},
        {"title": "Toplam Katılım", "value": toplam_katilim or 0, "icon": "✅", "color": "#8B5CF6"}
    ]
    
    for stat in stats:
        card = tk.Frame(stats_frame, bg=SECONDARY_BG)
        card.pack(side='left', fill='x', expand=True, padx=10)
        
        tk.Label(card, text=stat["icon"],
                font=('Segoe UI', 24),
                bg=SECONDARY_BG, fg=stat["color"]).pack()
        
        tk.Label(card, text=stat["title"],
                font=('Segoe UI', 12),
                bg=SECONDARY_BG, fg=TEXT_COLOR).pack(pady=(5,0))
        
        tk.Label(card, text=str(stat["value"]),
                font=('Segoe UI', 20, 'bold'),
                bg=SECONDARY_BG, fg=stat["color"]).pack(pady=(5,15))

    # Treeview container
    tree_container = ttk.Frame(main_container)
    tree_container.pack(fill='both', expand=True)
    
    # Treeview
    tree = ttk.Treeview(tree_container, style="Custom.Treeview")
    
    # Scrollbar
    scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Sütunlar
    tree["columns"] = ("Tarih", "Saat", "Toplam", "Katılan", "Katılmayan", "Katılım Oranı")
    tree["show"] = "headings"
    
    # Sütun genişlikleri ve başlıkları
    column_widths = {
        "Tarih": 180,
        "Saat": 140,
        "Toplam": 140,
        "Katılan": 140,
        "Katılmayan": 140,
        "Katılım Oranı": 140
    }
    
    for col, width in column_widths.items():
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="center")
    
    # Dersleri getir
    cursor.execute('''
        SELECT 
            d.ders_tarihi,
            d.ders_saati,
            COUNT(DISTINCT y.isim) as toplam,
            SUM(CASE WHEN y.durum = 'KATILDI' THEN 1 ELSE 0 END) as katilan,
            SUM(CASE WHEN y.durum = 'KATILMADI' THEN 1 ELSE 0 END) as katilmayan
        FROM dersler d
        LEFT JOIN yoklamalar y ON d.id = y.ders_id
        GROUP BY d.id
        ORDER BY d.ders_tarihi DESC, d.ders_saati DESC
    ''')
    
    for row in cursor.fetchall():
        tarih, saat, toplam, katilan, katilmayan = row
        if toplam > 0:
            oran = f"%{(katilan/toplam*100):.1f}"
        else:
            oran = "%0.0"
        tree.insert("", "end", values=(tarih, saat, toplam, katilan, katilmayan, oran))
    
    tree.pack(fill='both', expand=True)
    
    # Alt bilgi
    footer_frame = ttk.Frame(main_container, style="Main.TFrame")
    footer_frame.pack(fill='x', pady=15)
    
    # Info ikonu ve metin
    info_text = "Detaylı bilgi için tablodaki derslere çift tıklayın"
    info_label = tk.Label(footer_frame,
                         text="ℹ️ " + info_text,
                         font=('Segoe UI', 11),
                         bg='#0A0E17',
                         fg='#E2E8F0')
    info_label.pack(side='left')
    
    # Detay penceresi
    def detay_goster(event):
        item = tree.selection()[0]
        tarih, saat = tree.item(item)["values"][:2]
        
        detay = tk.Toplevel(root)
        detay.title(f"Ders Detayı - {tarih} {saat}")
        detay.geometry("900x700")
        detay.configure(bg='#0A0E17')
        
        # Üst kısım
        header_frame = ttk.Frame(detay, style="Main.TFrame")
        header_frame.pack(fill='x', padx=30, pady=20)
        
        # Başlık
        tk.Label(header_frame,
                text=f"{tarih} {saat}",
                font=('Segoe UI', 24, 'bold'),
                bg='#0A0E17',
                fg='#E2E8F0').pack(side='left')
        
        # Kapat butonu
        ttk.Button(header_frame,
                  text="✕ Kapat",
                  command=detay.destroy,
                  style="Custom.TButton").pack(side='right')
        
        # Detay tablosu
        detay_tree = ttk.Treeview(detay, style="Custom.Treeview")
        detay_tree["columns"] = ("İsim", "Durum", "Kayıt Saati")
        detay_tree["show"] = "headings"
        
        # Sütun ayarları
        column_widths = {
            "İsim": 300,
            "Durum": 200,
            "Kayıt Saati": 200
        }
        
        for col, width in column_widths.items():
            detay_tree.heading(col, text=col)
            detay_tree.column(col, width=width, anchor="center")
        
        # Scrollbar
        detay_scroll = ttk.Scrollbar(detay, orient="vertical", command=detay_tree.yview)
        detay_scroll.pack(side='right', fill='y', padx=(0, 30))
        
        detay_tree.configure(yscrollcommand=detay_scroll.set)
        
        # Verileri getir
        cursor.execute('''
            SELECT y.isim, y.durum, y.kayit_saati
            FROM yoklamalar y
            JOIN dersler d ON y.ders_id = d.id
            WHERE d.ders_tarihi = ? AND d.ders_saati = ?
            ORDER BY y.isim
        ''', (tarih, saat))
        
        for kayit in cursor.fetchall():
            detay_tree.insert("", "end", values=kayit)
        
        detay_tree.pack(fill='both', expand=True, padx=30)
    
    # Çift tıklama eventi
    tree.bind('<Double-1>', detay_goster)
    
    root.mainloop()
    
    if conn:
        conn.close()

def rastgele_yoklama_ekle(conn, kayit_sayisi=200):
    """
    Rastgele yoklama kayıtları ekler
    
    Args:
        conn (sqlite3.Connection): Veritabanı bağlantısı
        kayit_sayisi (int): Eklenmek istenen kayıt sayısı
        
    Not:
        - Son 30 gün için rastgele tarihler oluşturur
        - Her öğrenci için rastgele katılım durumu ekler
    """
    try:
        if conn is None:
            print("Veritabani baglantisi kurulamadi")
            return
            
        cursor = conn.cursor()
        
        # Faces klasöründeki isimleri al
        faces_dir = 'faces'
        ogrenciler = []
        for filename in os.listdir(faces_dir):
            if filename.endswith(('.jpg', '.JPG', '.png', '.PNG')):
                name = os.path.splitext(filename)[0]
                # Türkçe karakterleri düzelt
                name = name.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
                name = name.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
                ogrenciler.append(name)
        
        if not ogrenciler:
            print("Faces klasöründe fotoğraf bulunamadı")
            return
            
        # Son 30 gün için rastgele tarihler oluştur
        bugun = datetime.now()
        for _ in range(kayit_sayisi):
            # Rastgele bir tarih seç (son 30 gün içinde)
            rastgele_gun = random.randint(1, 30)
            ders_tarihi = (bugun - timedelta(days=rastgele_gun)).strftime('%Y-%m-%d')
            ders_saati = f"{random.randint(9,16):02d}:00:00"
            
            # Yeni ders kaydı oluştur
            cursor.execute('''
                INSERT INTO dersler (ders_tarihi, ders_saati)
                VALUES (?, ?)
            ''', (ders_tarihi, ders_saati))
            
            ders_id = cursor.lastrowid
            
            # Her öğrenci için rastgele katılım durumu ekle
            for ogrenci in ogrenciler:
                durum = random.choice(['KATILDI', 'KATILMADI'])
                kayit_saati = f"{random.randint(9,16):02d}:{random.randint(0,59):02d}:00"
                
                cursor.execute('''
                    INSERT OR REPLACE INTO yoklamalar (ders_id, isim, durum, kayit_saati)
                    VALUES (?, ?, ?, ?)
                ''', (ders_id, ogrenci, durum, kayit_saati))
        
        conn.commit()
        print(f"{kayit_sayisi} adet rastgele yoklama kaydı başarıyla eklendi.")
        
    except sqlite3.Error as e:
        print(f"Rastgele kayıt eklenirken hata oluştu: {e}")
