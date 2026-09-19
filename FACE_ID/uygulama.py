"""Kamera oturumu, demo ve komut satırı seçenekleri."""

import argparse
from pathlib import Path
import sqlite3
import sys

from tanima import DogrulamaTakibi, en_yakin_eslesme, yuzleri_yukle
from veri import (DEFAULT_DB, veritabani_olustur, yeni_ders_baslat, yoklama_ekle,
                  dersi_bitir, ders_kayitlari, csv_aktar)


def argumanlar(argv=None):
    parser = argparse.ArgumentParser(description='Yüz tanıma ile yoklama sistemi')
    parser.add_argument('--demo', action='store_true', help='Kamerasız, örnek öğrencilerle dene')
    parser.add_argument('--history', action='store_true', help='Geçmiş yoklamaları aç')
    parser.add_argument('--no-gui', action='store_true', help='Sonuç penceresini açma')
    parser.add_argument('--camera', type=int, default=0, help='Kamera numarası (varsayılan: 0)')
    parser.add_argument('--faces-dir', type=Path, default=Path(__file__).resolve().parent/'faces')
    parser.add_argument('--db', type=Path, help='Veritabanı dosyası')
    parser.add_argument('--lesson', default='Ders', help='Ders adı')
    parser.add_argument('--tolerance', type=float, default=0.5, help='Eşleşme mesafesi eşiği (0-1)')
    parser.add_argument('--confirm-frames', type=int, default=3, help='Ardışık doğrulama sayısı')
    parser.add_argument('--export', type=Path, help='Sonuçları CSV dosyasına kaydet')
    args = parser.parse_args(argv)
    if not 0 < args.tolerance <= 1 or args.confirm_frames < 1 or args.camera < 0:
        parser.error('Eşik 0-1 arasında, doğrulama en az 1, kamera numarası en az 0 olmalı.')
    if args.history and (args.demo or args.no_gui or args.export):
        parser.error('--history, --demo/--no-gui/--export ile birlikte kullanılamaz.')
    default_db = DEFAULT_DB.with_name('demo_yoklama.db') if args.demo else DEFAULT_DB
    args.db = (args.db or default_db).expanduser().resolve()
    return args


def kamera_ac(cv2, index):
    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == 'win32' else [cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, frame = cap.read()
            if ok and frame is not None:
                return cap, frame
        cap.release()
    raise ValueError('Kamera açılamadı. Diğer kamera uygulamalarını kapat veya --camera 1 ile dene.')


def ekran_metni(value):
    return value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU'))


def canli_oturum(args, cv2, engine):
    encodings, names = yuzleri_yukle(args.faces_dir, engine)
    cap, frame = kamera_ac(cv2, args.camera)
    conn, lesson_id, completed = None, None, False
    tracker = DogrulamaTakibi(args.confirm_frames)
    frame_count, locations, labels, scroll = 0, [], [], [0]
    window = 'Yoklama - Q: bitir / ESC: iptal'
    try:
        # Kamera ilk kareyi vermeden ders oluşturulmaz.
        conn = veritabani_olustur(args.db)
        lesson_id = yeni_ders_baslat(conn, args.lesson, names)
        cv2.namedWindow(window)
        def wheel(event, x, y, flags, param):
            if event == cv2.EVENT_MOUSEWHEEL:
                scroll[0] = max(0, min(max(0, len(names)-12), scroll[0] + (-1 if flags > 0 else 1)))
        cv2.setMouseCallback(window, wheel)
        while True:
            frame = cv2.flip(frame, 1)
            if frame_count % 3 == 0:
                small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (0, 0), fx=.25, fy=.25)
                locations = engine.face_locations(small, model='hog')
                vectors = engine.face_encodings(small, locations)
                labels = [en_yakin_eslesme(names, engine.face_distance(encodings, vector), args.tolerance)
                          for vector in vectors]
                for name in tracker.update(labels):
                    yoklama_ekle(conn, lesson_id, name, 'KATILDI')
                    print(f'{name} derse katıldı.', flush=True)
            frame_count += 1
            for (top, right, bottom, left), name in zip(locations, labels):
                color = (90, 190, 100) if name in tracker.confirmed else (80, 150, 240)
                cv2.rectangle(frame, (left*4, top*4), (right*4, bottom*4), color, 2)
                cv2.putText(frame, ekran_metni(name or 'Taninmadi'), (left*4, max(20, top*4-8)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, color, 2)
            canvas = cv2.copyMakeBorder(frame, 0, 0, 0, 310, cv2.BORDER_CONSTANT, value=(28, 24, 20))
            x = frame.shape[1]+15
            cv2.putText(canvas, f'KATILIM: {len(tracker.confirmed)}/{len(names)}', (x, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (240, 240, 240), 2)
            for index, name in enumerate(names[scroll[0]:scroll[0]+12]):
                present = name in tracker.confirmed
                text = ('[+] ' if present else '[ ] ') + ekran_metni(name)[:27]
                cv2.putText(canvas, text, (x, 70+index*29), cv2.FONT_HERSHEY_SIMPLEX, .5,
                            (100, 220, 150) if present else (180, 180, 180), 1)
            cv2.imshow(window, canvas)
            key = cv2.waitKey(1) & 0xff
            if key in (ord('q'), ord('Q')):
                completed = True
                break
            if key == 27 or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
            ok, frame = cap.read()
            if not ok or frame is None:
                print('Kamera bağlantısı kesildi. Görülmeyen öğrenciler belirsiz bırakıldı.')
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if conn is not None:
            try:
                if lesson_id is not None:
                    dersi_bitir(conn, lesson_id, completed)
            finally:
                conn.close()
    return lesson_id


def demo_oturum(args):
    conn = veritabani_olustur(args.db)
    try:
        names = [f'Örnek Öğrenci {i:02}' for i in range(1, 9)]
        lesson_id = yeni_ders_baslat(conn, 'Demo — ' + args.lesson, names)
        for name in names[:5]:
            yoklama_ekle(conn, lesson_id, name, 'KATILDI')
        dersi_bitir(conn, lesson_id)
        return lesson_id
    finally:
        conn.close()


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = argumanlar(argv)
    try:
        if args.history:
            from yoklama_db import gecmis_yoklamalari_goster
            gecmis_yoklamalari_goster(args.db)
            return 0
        if args.demo:
            print('DEMO: Kamera kullanılmıyor; kayıtlar örnek öğrencilerden oluşuyor.')
            lesson_id = demo_oturum(args)
        else:
            try:
                import cv2
                import face_recognition
            except ImportError as exc:
                print(f'Kamera bağımlılığı eksik: {exc}. requirements.txt dosyasını kur veya --demo kullan.', file=sys.stderr)
                return 2
            lesson_id = canli_oturum(args, cv2, face_recognition)
        conn = veritabani_olustur(args.db)
        try:
            records = ders_kayitlari(conn, lesson_id)
            if args.export:
                print('CSV:', csv_aktar(conn, lesson_id, args.export))
            print(f'Ders {lesson_id}: {sum(row[1] == "KATILDI" for row in records)}/{len(records)} katılım. Veritabanı: {args.db}')
        finally:
            conn.close()
        if not args.no_gui:
            from yoklama_db import sonuc_tablosu_goster
            sonuc_tablosu_goster({name: status == 'KATILDI' for name, status, _ in records}, lesson_id, args.db)
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f'Hata: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Oturum iptal edildi.')
        return 130
