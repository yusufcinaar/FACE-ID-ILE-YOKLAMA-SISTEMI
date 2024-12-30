"""
Yüz Tanıma Tabanlı Yoklama Sistemi
Bu program, kamera kullanarak gerçek zamanlı yüz tanıma yaparak yoklama alan bir sistemdir.
Öğrencilerin yüzlerini tanıyarak otomatik yoklama kaydı oluşturur.
"""

# Gerekli kütüphanelerin içe aktarılması
import face_recognition  # Yüz tanıma işlemleri için temel kütüphane
import cv2              # Görüntü işleme ve kamera kontrolü için OpenCV kütüphanesi
import os              # Dosya ve klasör işlemleri için işletim sistemi modülü
import numpy as np     # Matematiksel işlemler ve dizi manipülasyonu için
from datetime import datetime  # Tarih ve saat işlemleri için
from yoklama_db import *      # Veritabanı işlemleri için özel modül
import time                   # Zaman gecikmesi ve bekletme işlemleri için

# Veritabanı bağlantısını oluştur ve yeni ders başlat
conn = veritabani_olustur()  # Veritabanı bağlantısı oluşturulur
ders_id = yeni_ders_baslat(conn)  # Yeni bir ders kaydı başlatılır ve ID'si alınır

print("\nKatılımcılar yükleniyor...") # Kullanıcıya bilgi mesajı gösterilir

# Kaydırma işlemleri için global değişkenler tanımlanır
scroll_position = 0  # Kaydırma çubuğunun başlangıç pozisyonu
max_visible_items = 8  # Ekranda aynı anda gösterilecek maksimum kişi sayısı

def mouse_wheel(event, x, y, flags, param):
    """
    Fare tekerleği olaylarını yöneten fonksiyon
    """
    global scroll_position # Global değişkeni kullanmak için tanımlama
    if event == cv2.EVENT_MOUSEWHEEL: # Fare tekerleği olayı kontrol edilir
        if flags > 0:  # Yukarı kaydırma yapılıyorsa
            scroll_position = max(0, scroll_position - 1) # Pozisyonu yukarı kaydır
        else:  # Aşağı kaydırma yapılıyorsa
            scroll_position = min(max(0, len(known_face_names) - max_visible_items), scroll_position + 1) # Pozisyonu aşağı kaydır

# Yüz tanıma için gerekli veri yapıları oluşturulur
known_face_encodings = []  # Tanınan yüzlerin özellik vektörleri saklanır
known_face_names = []      # Tanınan yüzlerin isimleri saklanır
detected_people = set()    # Tespit edilen kişilerin kümesi tutulur
yoklama_durumu = {}       # Kişilerin yoklama durumu sözlük yapısında saklanır

# Faces klasöründeki fotoğraflar yüklenir ve işlenir
faces_dir = 'faces'  # Yüz fotoğraflarının bulunduğu klasör yolu
try:
    for filename in os.listdir(faces_dir):  # Klasördeki her dosya için döngü
        if filename.endswith(('.jpg', '.JPG', '.png', '.PNG')):  # Sadece desteklenen resim formatları işlenir
            filepath = os.path.join(faces_dir, filename)  # Dosyanın tam yolu oluşturulur
            try:
                # Görüntü yüklenir ve yüz kodlaması yapılır
                image = face_recognition.load_image_file(filepath)  # Görüntü dosyası yüklenir
                face_encodings = face_recognition.face_encodings(image)  # Yüz özellikleri çıkarılır
                
                if face_encodings:  # Eğer yüz tespit edildiyse
                    known_face_encodings.append(face_encodings[0])  # İlk yüzün özelliklerini kaydet
                    # Dosya adından Türkçe karakterler düzeltilir
                    name = os.path.splitext(filename)[0]  # Dosya uzantısı kaldırılır
                    name = name.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
                    name = name.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
                    known_face_names.append(name)  # İsim listeye eklenir
                    yoklama_durumu[name] = False   # Yoklama durumu başlangıçta false olarak ayarlanır
                    print(f"{name} yüklendi!")  # Kullanıcıya bilgi verilir
            except Exception as e:
                continue  # Hata durumunda sonraki dosyaya geç

    # Yükleme durumu özeti gösterilir
    print(f"\nYüklenen yüz sayısı: {len(known_face_names)}")
    print("Tanınacak kişiler:", ", ".join(known_face_names))
    print("\nKamera başlatılıyor...")

except Exception as e:
    print(f"Klasör okuma hatası: {e}")  # Klasör okuma hatası durumunda bilgi verilir
    exit()  # Program sonlandırılır

# Hiç yüz yüklenmemişse program sonlandırılır
if len(known_face_names) == 0:
    print("\nHiç yüz bulunamadı! Lütfen 'faces' klasörünü kontrol edin.")
    exit()

def init_camera():
    """
    Kamera başlatma ve ayarlama fonksiyonu
    """
    for i in range(3):  # 3 deneme hakkı verilir
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # DirectShow ile kamera açılır
        if cap.isOpened():  # Kamera başarıyla açıldıysa
            # Kamera ayarları optimize edilir
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Genişlik ayarlanır
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Yükseklik ayarlanır
            cap.set(cv2.CAP_PROP_FPS, 30)           # FPS ayarlanır
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     # Buffer boyutu ayarlanır
            return cap
        cap.release()  # Başarısız olursa kamera serbest bırakılır
        time.sleep(1)  # 1 saniye beklenir
    return None

# Kamera başlatılır
video_capture = init_camera()  # Kamera nesnesi oluşturulur
if video_capture is None:  # Kamera başlatılamazsa
    print("Hata: Kamera başlatılamadı!")
    exit()

# Pencere oluşturulur ve fare olayları bağlanır
cv2.namedWindow('Yuz Tanima Sistemi')  # Ana pencere oluşturulur
cv2.setMouseCallback('Yuz Tanima Sistemi', mouse_wheel)  # Fare olayları dinlenir

# Performans optimizasyonu için değişkenler
frame_count = 0  # İşlenen kare sayısı
process_interval = 3  # Kaç karede bir işlem yapılacağı
last_face_locations = []  # Son tespit edilen yüz konumları
last_face_names = []  # Son tespit edilen isimler

# Ana program döngüsü başlar
while True:
    ret, frame = video_capture.read()  # Kameradan bir kare alınır
    if not ret:  # Kare alınamazsa döngü sonlandırılır
        break
        
    frame = cv2.flip(frame, 1)  # Görüntü yatay olarak çevrilir
    
    # Her 3 karede bir yüz tanıma işlemi yapılır (performans için)
    process_this_frame = frame_count % process_interval == 0
    frame_count += 1
    
    if process_this_frame:  # İşlenecek kare ise
        # Görüntü ön işleme yapılır
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR'den RGB'ye dönüşüm
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)  # Görüntü küçültülür
        
        # Yüz tespiti ve tanıma işlemleri
        face_locations = face_recognition.face_locations(small_frame, model="hog")  # Yüz konumları bulunur
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)  # Yüz özellikleri çıkarılır

        last_face_locations = []  # Yüz konumları listesi temizlenir
        last_face_names = []  # Yüz isimleri listesi temizlenir

        # Her tespit edilen yüz için işlem yapılır
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Koordinatlar orijinal boyuta çevrilir
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            
            # Yüz eşleştirme işlemi yapılır
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            name = "Yetki Yok"  # Varsayılan isim
            
            if True in matches:  # Eşleşme varsa
                best_match_index = np.argmin(face_distances)  # En iyi eşleşme bulunur
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]  # Kişinin ismi alınır
                    similarity = (1 - face_distances[best_match_index]) * 100  # Benzerlik oranı hesaplanır
                    
                    # Yoklama kaydı yapılır
                    if not yoklama_durumu[name]:  # Daha önce kaydedilmemişse
                        yoklama_durumu[name] = True  # Durumu güncelle
                        yoklama_ekle(conn, ders_id, name, "KATILDI")  # Veritabanına ekle
                        print(f"\n{name} derse katıldı! - Benzerlik Orani: %{similarity:.1f}")

            last_face_locations.append((top, right, bottom, left))  # Konum kaydedilir
            last_face_names.append(name)  # İsim kaydedilir

    # Her karede yüz çerçevelerini çiz
    for (top, right, bottom, left), name in zip(last_face_locations, last_face_names):
        # Yüz çerçevesi
        cv2.rectangle(frame, (left-2, top-2), (right+2, bottom+2), (87, 187, 138), 2)
        
        # İsim paneli için arka plan
        panel_height = 30
        panel_width = right - left + 4
        gradient = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
        gradient[:, :] = (32, 33, 36)
        
        # Panel konumunu ayarla
        y1 = bottom
        y2 = min(bottom + panel_height, frame.shape[0])
        x1 = max(left - 2, 0)
        x2 = min(right + 2, frame.shape[1])
        
        # Gradient paneli yerleştir
        if y1 < frame.shape[0] and x1 < frame.shape[1] and y2 > y1 and x2 > x1:
            try:
                panel_region = frame[y1:y2, x1:x2]
                gradient_region = gradient[:y2-y1, :x2-x1]
                if panel_region.shape == gradient_region.shape:
                    frame[y1:y2, x1:x2] = cv2.addWeighted(
                        panel_region, 0.2,
                        gradient_region, 0.8,
                        0
                    )
            except:
                pass
        
        # İsmi yaz
        cv2.putText(frame, name, (left + 5, bottom + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Katılımcı listesi paneli
    panel_start_x = 10
    panel_width = 200
    panel_start_y = 10  # Panel başlangıç pozisyonu
    
    # Panel arka planı
    cv2.rectangle(frame, (panel_start_x-5, panel_start_y-5), 
                 (panel_start_x + panel_width, panel_start_y + 220),
                 (32, 33, 36), -1)
    
    # Başlık paneli
    cv2.rectangle(frame, (panel_start_x-5, panel_start_y-5), 
                 (panel_start_x + panel_width, panel_start_y + 20), 
                 (48, 51, 107), -1)
    cv2.putText(frame, "KATILIMCILAR", (panel_start_x + 10, panel_start_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Kaydırma çubuğu
    scrollbar_height = 200
    scrollbar_width = 5
    scrollbar_x = panel_start_x + panel_width - 10
    scrollbar_height = 180
    
    # Kaydırma çubuğu arka planı
    cv2.rectangle(frame,
                 (scrollbar_x, panel_start_y + 25),
                 (scrollbar_x + scrollbar_width, panel_start_y + scrollbar_height),
                 (60, 60, 60), -1)
    
    # Kaydırma göstergesi
    if len(known_face_names) > max_visible_items:
        scroll_ratio = scroll_position / (len(known_face_names) - max_visible_items)
        scroll_handle_pos = int(panel_start_y + 25 + (scrollbar_height - 30) * scroll_ratio)
        cv2.rectangle(frame,
                     (scrollbar_x, scroll_handle_pos),
                     (scrollbar_x + scrollbar_width, scroll_handle_pos + 30),
                     (100, 100, 100), -1)

    # Katılımcı listesini göster
    sorted_names = sorted(known_face_names)  # İsimleri alfabetik sırala
    visible_names = sorted_names[scroll_position:scroll_position + max_visible_items]  # Görünür isimleri al
    
    y_offset = panel_start_y + 30  # Liste başlangıç pozisyonu
    
    # Her görünür isim için
    for name in visible_names:
        # Kişi panel arka planı 
        cv2.rectangle(frame, (panel_start_x-5, y_offset-5), 
                     (panel_start_x + panel_width - 15, y_offset+20), 
                     (40, 42, 54), -1)
        
        # Katılım durumu
        durum = "KATILDI" if yoklama_durumu[name] else "KATILMADI"
        renk = (87, 187, 138) if yoklama_durumu[name] else (71, 75, 189)  # Yeşil veya kırmızı
        
        # İsim ve durumu yaz
        cv2.putText(frame, f"{name}", (panel_start_x, y_offset+10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, durum, (panel_start_x + 100, y_offset+10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, renk, 1)
        
        y_offset += 25  # Sonraki satıra geç

    # Görüntüyü göster
    cv2.imshow('Yuz Tanima Sistemi', frame)

    # 'q' tuşuna basılırsa çık
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Temizlik işlemleri
video_capture.release()  # Kamerayı serbest bırak
cv2.destroyAllWindows()  # Tüm pencereleri kapat

# Katılmayanları veritabanına ekle
for name, durum in yoklama_durumu.items():
    if not durum:
        yoklama_ekle(conn, ders_id, name, "KATILMADI")

# Sonuç tablosunu göster
sonuc_tablosu_goster(yoklama_durumu, ders_id)

# Veritabanı bağlantısını kapat
if conn:
    conn.close()