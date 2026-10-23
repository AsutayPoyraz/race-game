import pygame
import random
import sys

# Pygame başlatma
pygame.init()

# Ekran ayarları
GENISLIK = 800
YUKSEKLIK = 600
pencere = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("2D Araba Oyunu")

# Renkler
SIYAH = (0, 0, 0)
BEYAZ = (255, 255, 255)
KIRMIZI = (255, 0, 0)
MAVI = (0, 0, 255)
YESIL = (0, 255, 0)
SARI = (255, 255, 0)

# Oyuncu arabası ayarları
araba_genislik = 50
araba_yukseklik = 80
araba_x = GENISLIK // 2 - araba_genislik // 2
araba_y = YUKSEKLIK - araba_yukseklik - 20
araba_hiz = 8

# Engel ayarları
engel_genislik_min = 40
engel_genislik_max = 80
engel_yukseklik_min = 50
engel_yukseklik_max = 100
engel_hiz = 5
engel_olusturma_sikligi = 25  # Düşük değer = daha sık engel
engeller = []

# Oyun değişkenleri
skor = 0
oyun_aktif = True
saat = pygame.time.Clock()
FPS = 60

# Font ayarları
font = pygame.font.SysFont(None, 36)

def engel_olustur():
    """Rastgele engel oluşturur"""
    engel_x = random.randint(0, GENISLIK - engel_genislik_max)
    engel_y = -engel_yukseklik_max
    engel_genislik = random.randint(engel_genislik_min, engel_genislik_max)
    engel_yukseklik = random.randint(engel_yukseklik_min, engel_yukseklik_max)
    renk = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
    
    return {
        'rect': pygame.Rect(engel_x, engel_y, engel_genislik, engel_yukseklik),
        'renk': renk,
        'hiz': engel_hiz
    }

def carpisma_kontrolu(araba, engel):
    """Çarpışma kontrolü yapar"""
    return araba.colliderect(engel['rect'])

# Ana oyun döngüsü
while True:
    # Olay yönetimi
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        # Oyun bittiğinde yeniden başlatma
        if not oyun_aktif and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                oyun_aktif = True
                skor = 0
                engeller = []
                araba_x = GENISLIK // 2 - araba_genislik // 2

    if oyun_aktif:
        # Klavye kontrolleri
        tuslar = pygame.key.get_pressed()
        if tuslar[pygame.K_LEFT] and araba_x > 0:
            araba_x -= araba_hiz
        if tuslar[pygame.K_RIGHT] and araba_x < GENISLIK - araba_genislik:
            araba_x += araba_hiz

        # Oyuncu arabası rect objesi
        araba_rect = pygame.Rect(araba_x, araba_y, araba_genislik, araba_yukseklik)

        # Yeni engel oluşturma
        if random.randint(1, engel_olusturma_sikligi) == 1:
            engeller.append(engel_olustur())

        # Engelleri hareket ettirme ve çarpışma kontrolü
        for engel in engeller[:]:
            engel['rect'].y += engel['hiz']
            
            # Çarpışma kontrolü
            if carpisma_kontrolu(araba_rect, engel):
                oyun_aktif = False
            
            # Ekran dışına çıkan engelleri kaldırma
            if engel['rect'].y > YUKSEKLIK:
                engeller.remove(engel)
                skor += 10

        # Skoru artırma (sürekli)
        skor += 0.1

    # Ekranı temizleme
    pencere.fill(SIYAH)

    # Yol çizgileri (görsel efekt)
    for i in range(10):
        pygame.draw.rect(
            pencere, 
            BEYAZ, 
            (GENISLIK // 2 - 5, (i * 70) - (skor % 70), 10, 40)
        )

    # Engelleri çizme
    for engel in engeller:
        pygame.draw.rect(pencere, engel['renk'], engel['rect'])

    # Oyuncu arabasını çizme
    pygame.draw.rect(pencere, MAVI, (araba_x, araba_y, araba_genislik, araba_yukseklik))
    
    # Skor gösterme
    skor_yazi = font.render(f'Skor: {int(skor)}', True, BEYAZ)
    pencere.blit(skor_yazi, (10, 10))

    # Oyun bitti ekranı
    if not oyun_aktif:
        bitis_yazi = font.render('OYUN BİTTİ! (R ile Yeniden Başla)', True, KIRMIZI)
        pencere.blit(bitis_yazi, (GENISLIK//2 - bitis_yazi.get_width()//2, YUKSEKLIK//2))
        son_skor = font.render(f'Skor: {int(skor)}', True, SARI)
        pencere.blit(son_skor, (GENISLIK//2 - son_skor.get_width()//2, YUKSEKLIK//2 + 50))

    # Ekranı güncelleme
    pygame.display.flip()
    saat.tick(FPS)