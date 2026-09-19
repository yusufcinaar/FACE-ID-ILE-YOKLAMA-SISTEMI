import csv
from datetime import datetime
import importlib
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'FACE_ID'))
from veri import veritabani_olustur, yeni_ders_baslat, yoklama_ekle, dersi_bitir, ders_kayitlari, csv_aktar, yoklama_getir
from tanima import en_yakin_eslesme, DogrulamaTakibi, yuzleri_yukle
import uygulama


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'yoklama.db'
        self.conn = veritabani_olustur(self.path)
        self.lesson = yeni_ders_baslat(self.conn, 'Yazılım', ['Çağrı', 'Şule'])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_fast_sessions_have_distinct_ids(self):
        with patch('veri.datetime') as clock:
            clock.now.return_value=datetime(2026,9,19,10,0,0)
            first=yeni_ders_baslat(self.conn)
            second=yeni_ders_baslat(self.conn)
        self.assertNotEqual(first,second)

    def test_roster_starts_pending(self):
        self.assertEqual({r[1] for r in ders_kayitlari(self.conn, self.lesson)}, {'BEKLIYOR'})

    def test_duplicate_detection_preserves_first_time_and_row(self):
        yoklama_ekle(self.conn, self.lesson, 'Çağrı', 'KATILDI')
        before = self.conn.execute("SELECT id,kayit_saati FROM yoklamalar WHERE isim='Çağrı'").fetchone()
        yoklama_ekle(self.conn, self.lesson, 'Çağrı', 'KATILDI')
        after = self.conn.execute("SELECT id,kayit_saati FROM yoklamalar WHERE isim='Çağrı'").fetchone()
        self.assertEqual(before, after)
        self.assertEqual(len(ders_kayitlari(self.conn, self.lesson)), 2)

    def test_completed_session_marks_only_missing_students_absent(self):
        yoklama_ekle(self.conn, self.lesson, 'Çağrı', 'KATILDI')
        dersi_bitir(self.conn, self.lesson)
        self.assertEqual({r[0]:r[1] for r in ders_kayitlari(self.conn,self.lesson)}, {'Çağrı':'KATILDI','Şule':'KATILMADI'})

    def test_camera_failure_leaves_missing_students_pending(self):
        dersi_bitir(self.conn, self.lesson, False)
        self.assertEqual({r[1] for r in ders_kayitlari(self.conn,self.lesson)}, {'BEKLIYOR'})
        self.assertEqual(self.conn.execute('SELECT oturum_durumu FROM dersler WHERE id=?',(self.lesson,)).fetchone()[0],'YARIDA_KALDI')

    def test_attendance_cannot_be_overwritten_by_absence(self):
        yoklama_ekle(self.conn,self.lesson,'Çağrı','KATILDI')
        yoklama_ekle(self.conn,self.lesson,'Çağrı','KATILMADI')
        self.assertEqual(yoklama_getir(self.conn,'Çağrı')[0][2],'KATILDI')

    def test_missing_lesson_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            yoklama_ekle(self.conn,999,'Örnek','KATILDI')

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            yoklama_ekle(self.conn,self.lesson,'Örnek','INVALID')

    def test_csv_preserves_turkish_names(self):
        path=csv_aktar(self.conn,self.lesson,Path(self.tmp.name)/'rapor.csv')
        with path.open(encoding='utf-8-sig',newline='') as handle:
            rows=list(csv.reader(handle,delimiter=';'))
        self.assertEqual(rows[0][4],'Öğrenci')
        self.assertEqual({r[4] for r in rows[1:]},{'Çağrı','Şule'})

    def test_csv_formula_is_escaped(self):
        yoklama_ekle(self.conn,self.lesson,'=1+1','KATILDI')
        path=csv_aktar(self.conn,self.lesson,Path(self.tmp.name)/'formula.csv')
        self.assertIn("'=1+1",path.read_text(encoding='utf-8-sig'))

    def test_csv_cannot_overwrite_database(self):
        with self.assertRaises(ValueError):csv_aktar(self.conn,self.lesson,self.path)
        self.assertEqual(len(ders_kayitlari(self.conn,self.lesson)),2)

    def test_old_schema_is_upgraded_without_losing_records(self):
        path=Path(self.tmp.name)/'old.db'
        old=sqlite3.connect(path)
        old.execute('CREATE TABLE dersler (id INTEGER PRIMARY KEY, ders_tarihi DATE, ders_saati TIME)')
        old.execute("INSERT INTO dersler VALUES (7,'2024-12-01','09:00:00')")
        old.commit();old.close()
        conn=veritabani_olustur(path)
        try:self.assertEqual(conn.execute('SELECT id,oturum_durumu FROM dersler').fetchone(),(7,'TAMAMLANDI'))
        finally:conn.close()


class RecognitionTests(unittest.TestCase):
    def test_unknown_face_rejected(self):
        self.assertIsNone(en_yakin_eslesme(['A'],[.7]))

    def test_closest_match_selected(self):
        self.assertEqual(en_yakin_eslesme(['A','B'],[.6,.35]),'B')

    def test_ambiguous_match_rejected(self):
        self.assertIsNone(en_yakin_eslesme(['A','B'],[.35,.36]))

    def test_nonfinite_distance_rejected(self):
        self.assertIsNone(en_yakin_eslesme(['A'],[float('nan')]))

    def test_confirmation_requires_consecutive_frames(self):
        t=DogrulamaTakibi(3)
        self.assertFalse(t.update(['A']))
        self.assertFalse(t.update(['A']))
        self.assertFalse(t.update([]))
        self.assertFalse(t.update(['A']))
        self.assertFalse(t.update(['A']))
        self.assertEqual(t.update(['A']),{'A'})
        self.assertFalse(t.update(['A']))

    def test_duplicate_faces_in_same_frame_count_once(self):
        t=DogrulamaTakibi(2)
        self.assertFalse(t.update(['A','A','A']))
        self.assertEqual(t.update(['A']),{'A'})

    def test_invalid_and_multiple_faces_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ['A.jpg','B.PNG','Şule.jpeg']:(Path(folder)/name).touch()
            engine=Mock()
            engine.load_image_file.side_effect=lambda path:Path(path).stem
            engine.face_encodings.side_effect=lambda name:{'A':[],'B':[1,2],'Şule':[42]}[name]
            messages=[]
            encodings,names=yuzleri_yukle(folder,engine,messages.append)
            self.assertEqual((encodings,names),([42],['Şule']))
            self.assertEqual(len(messages),2)

    def test_empty_folder_has_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Kullanılabilir yüz yok'):
                yuzleri_yukle(folder,Mock())


class ApplicationTests(unittest.TestCase):
    def test_import_does_not_start_camera_or_create_database(self):
        with tempfile.TemporaryDirectory() as folder:
            result=subprocess.run([sys.executable,'-c',f'import sys;sys.path.insert(0,{str(ROOT / "FACE_ID")!r});import deneme'],cwd=folder,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_demo_runs_from_another_directory_without_camera_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            result=subprocess.run([sys.executable,str(ROOT/'FACE_ID/deneme.py'),'--demo','--no-gui','--db',str(path/'demo.db'),'--export',str(path/'out.csv')],cwd=folder,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((path/'out.csv').exists())
            conn=sqlite3.connect(path/'demo.db')
            try:self.assertEqual(conn.execute("SELECT count(*) FROM yoklamalar WHERE durum='KATILDI'").fetchone()[0],5)
            finally:conn.close()

    def test_failed_camera_releases_all_attempts(self):
        cv2=Mock();cv2.CAP_DSHOW=1;cv2.CAP_ANY=0
        caps=[Mock(),Mock()]
        for cap in caps:cap.isOpened.return_value=False
        cv2.VideoCapture.side_effect=caps
        with patch.object(uygulama.sys,'platform','win32'):
            with self.assertRaisesRegex(ValueError,'Kamera açılamadı'):uygulama.kamera_ac(cv2,0)
        for cap in caps:cap.release.assert_called_once()

    def test_camera_failure_does_not_create_lesson(self):
        with tempfile.TemporaryDirectory() as folder:
            args=uygulama.argumanlar(['--db',str(Path(folder)/'camera.db')])
            with patch.object(uygulama,'yuzleri_yukle',return_value=([1],['Örnek'])),patch.object(uygulama,'kamera_ac',side_effect=ValueError('Kamera açılamadı')):
                with self.assertRaises(ValueError):uygulama.canli_oturum(args,Mock(),Mock())
            self.assertFalse(args.db.exists())

    def test_camera_disconnect_preserves_pending_and_releases_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            args=uygulama.argumanlar(['--db',str(Path(folder)/'camera.db')])
            cv2=MagicMock();cv2.waitKey.return_value=-1;cv2.getWindowProperty.return_value=1
            engine=Mock();engine.face_locations.return_value=[];engine.face_encodings.return_value=[]
            cap=Mock();cap.read.return_value=(False,None)
            with patch.object(uygulama,'yuzleri_yukle',return_value=([1],['Örnek'])),patch.object(uygulama,'kamera_ac',return_value=(cap,MagicMock())),patch('builtins.print'):
                lesson=uygulama.canli_oturum(args,cv2,engine)
            conn=veritabani_olustur(args.db)
            try:self.assertEqual(ders_kayitlari(conn,lesson)[0][1],'BEKLIYOR')
            finally:conn.close()
            cap.release.assert_called_once();cv2.destroyAllWindows.assert_called_once()

    def test_result_window_reads_actual_recording_time(self):
        import yoklama_db as gui
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ui.db';conn=veritabani_olustur(path)
            lesson=yeni_ders_baslat(conn,students=['Örnek'])
            conn.execute("UPDATE yoklamalar SET durum='KATILDI', kayit_saati='08:13:42'")
            conn.commit();conn.close()
            # Mock widgets, real database: the displayed time must come from the record.
            with patch.object(gui,'tk',MagicMock()),patch.object(gui,'ttk',MagicMock()) as widgets:
                gui.sonuc_tablosu_goster({'Örnek':True},lesson,path)
                widgets.Treeview.return_value.insert.assert_any_call('', 'end', values=('Örnek','08:13:42'))

    def test_history_window_handles_empty_lesson(self):
        import yoklama_db as gui
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ui.db';conn=veritabani_olustur(path)
            yeni_ders_baslat(conn,'Boş ders');conn.close()
            with patch.object(gui,'tk',MagicMock()),patch.object(gui,'ttk',MagicMock()) as widgets:
                gui.gecmis_yoklamalari_goster(path)
                values=widgets.Treeview.return_value.insert.call_args.kwargs['values']
                self.assertEqual(values[2:5],('Boş ders','Devam ediyor',0))


if __name__=='__main__':unittest.main()
