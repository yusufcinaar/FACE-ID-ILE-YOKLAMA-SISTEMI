"""Kamera kütüphanelerinden bağımsız eşleştirme ve doğrulama kuralları."""

from pathlib import Path
import math


def yuzleri_yukle(folder, engine, notify=print):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Fotoğraf klasörü bulunamadı: {folder}")
    encodings, names = [], []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            continue
        name = path.stem.strip()
        if not name or name in names:
            notify(f"Atlandı: {path.name} — boş veya tekrar eden öğrenci adı.")
            continue
        try:
            image = engine.load_image_file(str(path))
            found = engine.face_encodings(image)
            if len(found) != 1:
                notify(f"Atlandı: {path.name} — tam bir yüz gerekli, bulunan: {len(found)}.")
                continue
        except Exception as exc:
            notify(f"Okunamadı: {path.name} — {exc}")
            continue
        encodings.append(found[0])
        names.append(name)
    if not names:
        raise ValueError("Kullanılabilir yüz yok. Fotoğrafları kontrol et veya --demo ile dene.")
    return encodings, names


def en_yakin_eslesme(names, distances, tolerance=0.5, margin=0.04):
    """Mesafe bir olasılık yüzdesi değildir; belirsiz eşleşmeleri reddet."""
    if len(names) != len(distances) or not names:
        return None
    if any(not math.isfinite(float(value)) for value in distances):
        return None
    ordered = sorted(zip(distances, names))
    if ordered[0][0] > tolerance:
        return None
    if len(ordered) > 1 and ordered[1][0] - ordered[0][0] < margin:
        return None
    return ordered[0][1]


class DogrulamaTakibi:
    """Bir öğrenciyi ardışık işlenen karelerde görmeden yoklamaya ekleme."""

    def __init__(self, required=3):
        if required < 1:
            raise ValueError("Doğrulama sayısı en az 1 olmalı.")
        self.required = required
        self.counts = {}
        self.confirmed = set()

    def update(self, names):
        visible = {name for name in names if name is not None}
        self.counts = {name: self.counts.get(name, 0) + 1 for name in visible}
        newly_confirmed = {name for name, count in self.counts.items()
                           if count >= self.required and name not in self.confirmed}
        self.confirmed.update(newly_confirmed)
        return newly_confirmed
