"""Yoklama kayıtları ve Excel'de açılabilen CSV raporları."""

import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / 'yoklama.db'
STATUSES = {'KATILDI', 'KATILMADI', 'BEKLIYOR'}


def veritabani_olustur(path=DEFAULT_DB):
    if str(path) != ':memory:':
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS dersler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_tarihi DATE NOT NULL, ders_saati TIME NOT NULL,
                UNIQUE(ders_tarihi, ders_saati));
            CREATE TABLE IF NOT EXISTS yoklamalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_id INTEGER NOT NULL REFERENCES dersler(id),
                isim TEXT NOT NULL, durum TEXT NOT NULL, kayit_saati TIME NOT NULL,
                UNIQUE(ders_id, isim));
        ''')
        columns = {row[1] for row in conn.execute('PRAGMA table_info(dersler)')}
        if 'ders_adi' not in columns:
            conn.execute("ALTER TABLE dersler ADD COLUMN ders_adi TEXT NOT NULL DEFAULT 'Ders'")
        if 'oturum_durumu' not in columns:
            conn.execute("ALTER TABLE dersler ADD COLUMN oturum_durumu TEXT NOT NULL DEFAULT 'TAMAMLANDI'")
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def yeni_ders_baslat(conn, ders_adi='Ders', students=()):
    now = datetime.now()
    with conn:
        # Eski şemadaki tarih/saat benzersizliğini koru. Windows saati iki
        # hızlı başlangıçta aynı değeri döndürebilir; uyumlu bir alt zaman seç.
        for attempt in range(1000):
            try:
                result = conn.execute('''INSERT INTO dersler
                    (ders_tarihi, ders_saati, ders_adi, oturum_durumu) VALUES (?, ?, ?, 'DEVAM')''',
                    (now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S.%f'), ders_adi.strip() or 'Ders'))
                break
            except sqlite3.IntegrityError as exc:
                if 'dersler.ders_tarihi, dersler.ders_saati' not in str(exc):
                    raise
                now += timedelta(microseconds=1)
        else:
            raise ValueError('Aynı anda çok fazla ders başlatıldı. Tekrar dene.')
        lesson_id = result.lastrowid
        conn.executemany('INSERT INTO yoklamalar (ders_id, isim, durum, kayit_saati) VALUES (?, ?, ?, ?)',
                         [(lesson_id, name, 'BEKLIYOR', '') for name in sorted(set(students))])
    return lesson_id


def yoklama_ekle(conn, ders_id, isim, durum):
    if not isim.strip() or durum not in STATUSES:
        raise ValueError('Geçerli öğrenci adı ve yoklama durumu gerekli.')
    # İlk katılım saati korunur; tekrar algılama mevcut kaydı değiştirmez.
    with conn:
        conn.execute('''INSERT INTO yoklamalar (ders_id, isim, durum, kayit_saati)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ders_id, isim) DO UPDATE SET
                durum=excluded.durum, kayit_saati=excluded.kayit_saati
            WHERE yoklamalar.durum != 'KATILDI' ''',
            (ders_id, isim, durum, datetime.now().strftime('%H:%M:%S') if durum != 'BEKLIYOR' else ''))


def dersi_bitir(conn, ders_id, completed=True):
    with conn:
        if completed:
            conn.execute("UPDATE yoklamalar SET durum='KATILMADI', kayit_saati=? WHERE ders_id=? AND durum='BEKLIYOR'",
                         (datetime.now().strftime('%H:%M:%S'), ders_id))
        conn.execute('UPDATE dersler SET oturum_durumu=? WHERE id=?',
                     ('TAMAMLANDI' if completed else 'YARIDA_KALDI', ders_id))


def ders_kayitlari(conn, ders_id):
    return conn.execute('SELECT isim, durum, kayit_saati FROM yoklamalar WHERE ders_id=? ORDER BY isim',
                        (ders_id,)).fetchall()


def yoklama_getir(conn, isim):
    return conn.execute('''SELECT d.ders_tarihi, d.ders_saati, y.durum, y.kayit_saati
        FROM yoklamalar y JOIN dersler d ON y.ders_id=d.id WHERE y.isim=?
        ORDER BY d.ders_tarihi DESC, d.ders_saati DESC, d.id DESC LIMIT 5''', (isim,)).fetchall()


def csv_hucresi(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text


def csv_aktar(conn, ders_id, destination):
    lesson = conn.execute('SELECT ders_adi, ders_tarihi, ders_saati, oturum_durumu FROM dersler WHERE id=?',
                          (ders_id,)).fetchone()
    if lesson is None:
        raise ValueError('Ders bulunamadı.')
    destination = Path(destination).expanduser().resolve()
    # Rapor yolu mevcut veritabanının üzerine yazamaz.
    for _, _, database in conn.execute('PRAGMA database_list'):
        if database and Path(database).resolve() == destination:
            raise ValueError('CSV yolu veritabanıyla aynı olamaz.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['Ders', 'Tarih', 'Başlangıç', 'Oturum', 'Öğrenci', 'Durum', 'Kayıt saati'])
        for row in ders_kayitlari(conn, ders_id):
            writer.writerow([csv_hucresi(cell) for cell in (*lesson, *row)])
    return destination
