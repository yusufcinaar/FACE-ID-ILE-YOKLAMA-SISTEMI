# Face ID ile Yoklama Sistemi

Bu projeyi üniversitedeyken yapmıştım. Kameranın karşısına geçen öğrenciyi tanıyıp yoklamaya ekliyor. Ders bitince de katılanları ve katılmayanları ayrı ayrı görebiliyorum. Kayıtlar bilgisayardaki SQLite veritabanında tutuluyor, geçmiş derslere sonradan bakılabiliyor.

Bir süre sonra projeyi tekrar açıp eksik kalan kısımlarını toparladım. İlk halinde sadece kendi bilgisayarımda çalıştırmaya odaklanmıştım. Bu güncellemede kurulumu anlatan notlar, kamerasız deneme ve CSV çıktısı ekledim; kayıt alma tarafındaki bazı hataları da düzelttim.

## Önce bir görmek istersen

Python 3.12 ile deneyebilirsin. Kamerayı ve yüz tanıma paketlerini kurmadan sonuç ekranını görmek için:

```powershell
python FACE_ID/deneme.py --demo
```

Windows'ta `DEMO-BASLAT.bat` dosyasına çift tıklamak da aynı ekranı açıyor. Python'un bilgisayarda kurulu olması gerekiyor.

Demo, 8 örnek öğrenciyle açılıyor. 5'i katıldı, 3'ü katılmadı olarak görünüyor. Bunlar gerçek yoklama kayıtları değil. Deneme kayıtları ayrı bir `demo_yoklama.db` dosyasına yazılıyor.

## Kamerayla nasıl kullanılıyor?

Önce proje klasöründe bir Python ortamı oluşturup paketleri kur:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python FACE_ID/deneme.py --lesson "Yazılım Mühendisliği"
```

Tanıtmak istediğin kişilerin izinli fotoğraflarını `FACE_ID/faces` klasörüne koy. Dosya adı kişinin adı oluyor; örneğin `Örnek Öğrenci.jpg`. Her fotoğrafta tek yüz olmalı. Fotoğrafta yüz bulunmazsa veya birden fazla yüz varsa program artık bunu söylüyor.

Kamera açılınca tanınan kişi birkaç kez üst üste görülürse yoklamaya ekleniyor. **Q** ile dersi bitirdiğinde görülmeyen kişiler katılmadı olarak kaydediliyor. **Esc** ile iptal edersen ya da kamera bağlantısı kesilirse, görülmeyen kişiler belirsiz bırakılıyor.

Kamera numarasını değiştirmek gerekirse:

```powershell
python FACE_ID/deneme.py --camera 1
```

**Kurulum notu:** Yüz tanıma için kullanılan `face_recognition`, `dlib` paketine bağlı. Windows'ta kurulum CMake ve C++ derleme araçları isteyebiliyor. Bu bilgisayarda derleyici eksik olduğu için canlı kamera kurulumu tamamlanamadı; demo ve aşağıdaki otomatik testler çalıştırıldı. Kütüphanenin [kurulum açıklaması burada](https://pypi.org/project/face-recognition/#installation).

## Bu güncellemede ne değişti?

- Yanlış eşleşmeleri azaltmak için ek doğrulama kontrolleri ekledim. Varsayılan olarak aynı kişinin işlenen 3 karede art arda eşleşmesi gerekiyor.
- Kamera açılmadan boş ders kaydı oluşturulmuyor.
- Sonuç ekranında öğrencinin gerçekten kaydedildiği saat gösteriliyor.
- Aynı kişi tekrar tanınırsa ilk katılım saati değişmiyor.
- İki kişiye ait eşleşme mesafeleri birbirine çok yakınsa sonuç belirsiz sayılıyor ve otomatik yoklamaya eklenmiyor.
- Kamera veya fotoğraf hataları artık sessizce geçilmiyor.
- Sonuçlar **CSV olarak kaydet** düğmesiyle dışarı aktarılabiliyor. Türkçe karakterlerle Excel'de açılabiliyor.
- Farklı klasörden çalıştırınca dosya yolları bozulmuyor.
- Geçmiş ekranında ders adı ve oturumun tamamlanıp tamamlanmadığı görülebiliyor.

Bu kontrolleri ekledim ama henüz gerçek kamera görüntülerinde önceki sürümle karşılaştırmalı bir başarı ölçümü yapmadım. Bu yüzden bir doğruluk yüzdesi vermiyorum. Daha sıkı kontrol bazı kişilerin tanınmasını geciktirebilir.

## Hangi dille yazdım?

Proje **Python** ile yazıldı. Yüz eşleştirme için `face_recognition`, kamera görüntüsü için OpenCV, sonuç pencereleri için Tkinter ve kayıtlar için SQLite kullanılıyor. Demo modu kamera paketleri olmadan da açılabiliyor.

## Diğer seçenekler

```powershell
# Kamera açmadan geçmiş dersleri görüntüle
python FACE_ID/deneme.py --history

# Demo sonuçlarını pencere açmadan CSV'ye kaydet
python FACE_ID/deneme.py --demo --no-gui --export reports/demo.csv

# Başka bir fotoğraf klasörü ve veritabanı kullan
python FACE_ID/deneme.py --faces-dir "D:\Yoklama\faces" --db "D:\Yoklama\yoklama.db"
```

Normal kayıtlar `FACE_ID/yoklama.db` dosyasında. Eski veritabanını kullanıyorsan `--db` ile gösterebilirsin; yeni alanlar mevcut kayıtlara dokunmadan ekleniyor. Önce bir kopyasını almak iyi olur.

Fotoğraflar, veritabanları ve raporlar Git'e eklenmiyor. Önceki commit'lerde bulunan fotoğraflar son sürümden çıkarıldı; eski Git geçmişinde hâlâ bulunabilir.

## Testler

```powershell
python -m unittest discover -s tests -v
```

Testler için yüz fotoğrafı veya kamera gerekmiyor. Kayıtların korunması, CSV, eski veritabanı, eşleştirme kuralları ve kamera hata akışları kontrol ediliyor. Kamera testlerinde taklit nesneler kullanılıyor; gerçek kamerada tanıma başarısını ölçmüyorlar.

Bu hâlâ bir öğrenci projesi. Yüz tanıma ışık, açı ve fotoğrafa göre yanılabilir; sonuçları kontrol ederek kullanmak gerekiyor. Fotoğraf/video ile kandırılmayı engelleyen bir canlılık kontrolü de yok.
