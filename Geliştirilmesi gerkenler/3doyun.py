from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import time

# Oyunu başlat
app = Ursina()

# Oyun ayarları
window.title = '3D Araba Yarışı'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False

# Kamera modu: 0 = 3. şahıs, 1 = 1. şahıs
camera_mode = 0

# Yol oluşturma
yol = Entity(
    model='cube',
    color=color.gray,
    scale=(10, 0.1, 1000),  # Genişlik, kalınlık, uzunluk
    position=(0, 0, 0),
    texture='white_cube',
    texture_scale=(1, 100)  # Yolun dokusunu uzat
)

# Yol şeritleri için çizgiler
for i in range(-1, 2, 2):  # -1 ve 1 için
    yol_cizgisi = Entity(
        model='cube',
        color=color.white,
        scale=(0.1, 0.11, 1000),  # İnce uzun çizgiler
        position=(i * 3, 0.01, 0),  # Yolun üstünde olmalı
        parent=yol
    )

# Oyuncu arabası (basit bir kutu ile temsil edilecek)
araba = Entity(
    model='cube',
    color=color.blue,
    scale=(1.5, 1, 3),
    position=(0, 1, -10),  # Kamera açısına göre başlangıç pozisyonu
    collider='box'
)

# Araba için BMW benzeri detaylar ekleme
bmw_logo = Entity(
    model='quad',
    texture='white_cube',
    color=color.white,
    scale=(0.5, 0.5),
    position=(araba.x, araba.y + 0.6, araba.z - 1.4),
    parent=araba
)
far_sol = Entity(
    model='cube',
    color=color.yellow,
    scale=(0.2, 0.2, 0.2),
    position=(araba.x - 0.7, araba.y + 0.3, araba.z - 1.4),
    parent=araba
)
far_sag = duplicate(far_sol, x=araba.x + 0.7)

# Düşman arabalar listesi
dusman_arabalar = []

# Skor
skor = 0
skor_yazisi = Text(text=f'Skor: {skor}', position=(-0.8, 0.4), origin=(0,0))

# Oyun durumu
oyun_devam = True

# Kamera ayarları
# İlk kamera: 3. şahıs (arabanın arkası)
kamera_3sahis = EditorCamera()
kamera_3sahis.position = (0, 5, -15)  # Arabaya göre konum
kamera_3sahis.rotation_x = 20  # Hafif yukarı bakış

# İkinci kamera: 1. şahıs (araba içi) - Arabanın içine yerleştirilmiş bir kamera
kamera_1sahis = EditorCamera()
kamera_1sahis.position = (0, 2, 0)  # Arabanın içinde
kamera_1sahis.rotation_x = 0
kamera_1sahis.enabled = False  # Başlangıçta 3. şahıs kamera aktif

# Kamera modunu değiştiren fonksiyon
def kamera_degistir():
    global camera_mode
    camera_mode = 1 - camera_mode  # 0 ise 1, 1 ise 0 yapar
    if camera_mode == 0:
        kamera_3sahis.enabled = True
        kamera_1sahis.enabled = False
    else:
        kamera_3sahis.enabled = False
        kamera_1sahis.enabled = True
        # 1. şahıs kamerasını arabanın içine sabitle
        kamera_1sahis.position = (araba.x, araba.y + 1, araba.z + 1.5)
        kamera_1sahis.rotation = araba.rotation

# Kamera değiştirme tuşu
def input(key):
    if key == 'v':
        kamera_degistir()
    # Oyun bitince çıkış
    if key == 'escape':
        quit()

# Düşman araba oluşturma fonksiyonu
def dusman_olustur():
    if not oyun_devam:
        return
        
    # Rastgele şerit seç: -1 (sol), 0 (orta), 1 (sağ)
    serit = random.choice([-1, 0, 1])
    # Rastgele hız (ileriye doğru, düşman arabalar aslında geriye doğru hareket ediyor gibi görünecek)
    hiz = random.uniform(5, 15)
    # Rastgele renk (kırmızı, yeşil, sarı, turuncu)
    renk = random.choice([color.red, color.green, color.yellow, color.orange])
    
    dusman = Entity(
        model='cube',
        color=renk,
        scale=(1.5, 1, 3),
        position=(serit * 3, 1, 50),  # Yolun ilerisinde
        collider='box'
    )
    
    # Düşman arabaya detaylar ekle
    dusman_far = Entity(
        model='cube',
        color=color.yellow,
        scale=(0.2, 0.2, 0.2),
        position=(dusman.x, dusman.y + 0.3, dusman.z - 1.4),
        parent=dusman
    )
    
    dusman_arabalar.append((dusman, hiz))
    
    # Belirli aralıklarla düşman oluştur
    invoke(dusman_olustur, delay=random.uniform(0.5, 2))

# Düşman arabaları hareket ettirme ve çarpışma kontrolü
def dusman_guncelle():
    global oyun_devam, skor
    if not oyun_devam:
        return
        
    for dusman, hiz in dusman_arabalar[:]:
        dusman.z -= hiz * time.dt
        
        # Ekran dışına çıkan arabaları sil
        if dusman.z < -100:
            destroy(dusman)
            dusman_arabalar.remove((dusman, hiz))
            skor += 10
            skor_yazisi.text = f'Skor: {skor}'
        
        # Çarpışma kontrolü
        if dusman.intersects(araba):
            oyun_devam = False
            oyun_bitir()

# Oyun bitiş fonksiyonu
def oyun_bitir():
    oyun_bitti_yazisi = Text(
        text='OYUN BITTI! (ESC ile çık)',
        position=(0, 0.1),
        origin=(0,0),
        scale=2,
        color=color.red
    )
    son_skor_yazisi = Text(
        text=f'Son Skor: {skor}',
        position=(0, -0.1),
        origin=(0,0),
        scale=1.5,
        color=color.yellow
    )

# Güncelleme fonksiyonu
def update():
    global oyun_devam
    
    if not oyun_devam:
        return
        
    # Arabayı hareket ettirme (sağ-sol)
    if held_keys['left arrow'] and araba.x > -3:
        araba.x -= 5 * time.dt
    if held_keys['right arrow'] and araba.x < 3:
        araba.x += 5 * time.dt
        
    # 1. şahıs kamerasını arabaya bağlama
    if camera_mode == 1:
        kamera_1sahis.position = (araba.x, araba.y + 1, araba.z + 1.5)
        kamera_1sahis.rotation = araba.rotation
        
    # Düşman arabaları güncelle
    dusman_guncelle()
    
    # Skoru sürekli artır (zamanla)
    global skor
    skor += time.dt
    skor_yazisi.text = f'Skor: {int(skor)}'

# İlk düşmanı oluşturma
dusman_olustur()

# Gökyüzü
Sky(texture='sky_sunset')

# Oyunu çalıştır
app.run()