"""
3D Kalp Modeli - Python ile çizim ve animasyon
-----------------------------------------------
Matematiksel bir "kalp yüzeyi" denklemi kullanılarak 3 boyutlu bir kalp
modeli oluşturulur ve bu kalp, program çalıştırıldığında TAM OLARAK
5 SANİYE içinde "büyüyerek" tamamlanan bir animasyon ile çizilir.
Kalbin bir yarısı PEMBE, diğer yarısı MOR renktedir.

Gerekli kütüphaneler:
    pip install numpy matplotlib scikit-image

Çalıştırmak için:
    python heart_3d.py
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.animation import FuncAnimation
from skimage import measure

# ============================================================
# 1) KALP YÜZEYİNİN MATEMATİKSEL TANIMI (implicit denklem)
#    (x^2 + 9/4*y^2 + z^2 - 1)^3 - x^2*z^3 - 9/80*y^2*z^3 = 0
#    Bu denklem, 3 boyutlu uzayda gerçek bir "kalp" yüzeyi tanımlar.
# ============================================================
N = 75          # ızgara çözünürlüğü (kaliteyi/performansı dengeler)
LIM = 1.5

gx, gy, gz = np.mgrid[-LIM:LIM:N * 1j, -LIM:LIM:N * 1j, -LIM:LIM:N * 1j]
F = (gx**2 + (9 / 4) * gy**2 + gz**2 - 1) ** 3 - gx**2 * gz**3 - (9 / 80) * gy**2 * gz**3

spacing = (2 * LIM / (N - 1),) * 3
verts, faces, _, _ = measure.marching_cubes(F, level=0, spacing=spacing)
verts -= LIM  # ızgarayı -LIM..+LIM aralığına geri kaydır

# Üçgenler: her biri 3 köşe noktasından oluşan (N_ucgen, 3, 3) dizisi
triangles = verts[faces]

# ============================================================
# 2) Üçgenleri sivri UÇTAN (alt) başlayıp iki KULAKÇIĞA (üst)
#    doğru sıraya diziyoruz ki animasyon kalbi alttan yukarı
#    doğru "büyüyormuş" gibi çizsin.
# ============================================================
centroid_z = triangles[:, :, 2].mean(axis=1)   # yükseklik ortalaması
centroid_x = triangles[:, :, 0].mean(axis=1)   # sol/sağ ortalaması

order = np.argsort(centroid_z)
triangles = triangles[order]
centroid_x = centroid_x[order]

# ============================================================
# 3) Renklendirme: SOL yarı PEMBE, SAĞ yarı MOR
# ============================================================
PEMBE = "#FF3E8E"
MOR = "#8B2FC9"
face_colors = np.where(centroid_x < 0, PEMBE, MOR)

# ============================================================
# 4) Sahneyi hazırla
# ============================================================
fig = plt.figure(figsize=(7, 7), facecolor="black")
ax = fig.add_subplot(111, projection="3d")
ax.set_facecolor("black")
ax.set_axis_off()

pad = 1.08
ax.set_xlim(verts[:, 0].min() * pad, verts[:, 0].max() * pad)
ax.set_ylim(verts[:, 1].min() * pad, verts[:, 1].max() * pad)
ax.set_zlim(verts[:, 2].min() * pad, verts[:, 2].max() * pad)
ax.set_box_aspect((1, 1, 1))

BASE_ELEV, BASE_AZIM = 10, -90
ax.view_init(elev=BASE_ELEV, azim=BASE_AZIM)

poly = Poly3DCollection([], edgecolor="none")
ax.add_collection3d(poly)

# ============================================================
# 5) ANİMASYON: tam olarak 5 saniyede tamamlanır
# ============================================================
TOPLAM_SURE_MS = 5000
KARE_SAYISI = 100
INTERVAL_MS = TOPLAM_SURE_MS / KARE_SAYISI   # kare başına ms

total_faces = len(triangles)


def update(frame):
    ilerleme = (frame + 1) / KARE_SAYISI           # 0 -> 1
    n = max(1, int(ilerleme * total_faces))
    poly.set_verts(triangles[:n])
    poly.set_facecolor(face_colors[:n])

    # Hafif bir sallanma/döndürme efekti (kalp şeklini bozmadan)
    azim = BASE_AZIM + 10 * np.sin(2 * np.pi * frame / KARE_SAYISI)
    ax.view_init(elev=BASE_ELEV, azim=azim)
    return (poly,)


ani = FuncAnimation(
    fig, update, frames=KARE_SAYISI, interval=INTERVAL_MS, blit=False, repeat=True
)

if __name__ == "__main__":
    # Ekranda canlı olarak izlemek için aşağıdaki satırı etkinleştirin:
    # plt.show()

    # GIF olarak dışa aktarmak için:
    fps = 1000 / INTERVAL_MS
    ani.save("heart_3d.gif", writer="pillow", fps=fps)
    print("heart_3d.gif oluşturuldu (5 saniyede tamamlanan animasyon).")