import random
from ursina import *

# =====================================================================
# 1. KURULUM
# =====================================================================
app = Ursina(title='Otoban Makasi')
window.fps_counter.enabled = True
window.entity_counter.enabled = False
window.collider_counter.enabled = False
camera.fov = 70


def world(**kw):
    """Standart shader ile nesne üretir (beyazlama yapmaz)."""
    return Entity(**kw)


# =====================================================================
# 2. GÖKYÜZÜ
# =====================================================================
Sky(texture='sky_sunset')


# =====================================================================
# 3. SABİTLER
# =====================================================================
LANE_W = 3.5
LANES = [-LANE_W, 0, LANE_W]
ROAD_HALF = 5.3
MAX_TRAFFIC = 14
TOP_SPEED = 200
TURBO_BONUS = 40

CAR_COLORS = [
    color.rgb(20, 50, 110),           # BMW mavisi
    color.rgb(15, 15, 15),            # siyah
    color.rgb(170, 20, 30),           # kırmızı
    color.rgb(230, 230, 235),         # beyaz
    color.rgb(60, 120, 40),           # yeşil
]
TRAFFIC_COLORS = [
    color.rgb(200, 200, 205), color.rgb(40, 40, 45),
    color.rgb(150, 30, 30), color.rgb(30, 80, 160),
    color.rgb(230, 200, 60),
]


# =====================================================================
# 4. ARABA MODELİ (BMW G20 benzeri)
# =====================================================================
def build_car(root, body_col):
    """Arabayı 'root' altında kurar. Ön taraf +Z yönündedir."""
    # Yere düşen sahte gölge
    Entity(parent=root, model='quad', color=color.rgba(0, 0, 0, 120),
           scale=(2.6, 5.0), rotation_x=90, y=0.03)

    # Ana gövde
    world(parent=root, model='cube', color=body_col,
          scale=(1.9, 0.45, 4.4), y=0.55)
    # Kaput
    world(parent=root, model='cube', color=body_col,
          scale=(1.85, 0.25, 1.4), position=(0, 0.8, 1.35))
    # Bagaj
    world(parent=root, model='cube', color=body_col,
          scale=(1.85, 0.5, 1.0), position=(0, 0.85, -1.7))
    # Cam kabin
    world(parent=root, model='cube', color=color.rgb(20, 22, 28),
          scale=(1.6, 0.5, 2.0), position=(0, 1.1, -0.15))
    # Tavan
    world(parent=root, model='cube', color=body_col,
          scale=(1.65, 0.1, 1.6), position=(0, 1.38, -0.2))

    # Böbrek ızgara
    for x in (-0.36, 0.36):
        world(parent=root, model='cube', color=color.rgb(20, 20, 22),
              scale=(0.62, 0.42, 0.06), position=(x, 0.6, 2.2))
    # Ön tampon
    world(parent=root, model='cube', color=color.rgb(30, 30, 30),
          scale=(1.9, 0.3, 0.1), position=(0, 0.33, 2.22))

    # Farlar (ön) ve stoplar (arka)
    for x in (-0.65, 0.65):
        world(parent=root, model='cube', color=color.rgb(255, 250, 220),
              scale=(0.55, 0.14, 0.05), position=(x, 0.78, 2.19))
        world(parent=root, model='cube', color=color.rgb(200, 20, 20),
              scale=(0.5, 0.12, 0.05), position=(x, 0.78, -2.19))

    # Yan aynalar
    for x in (-1.0, 1.0):
        world(parent=root, model='cube', color=body_col,
              scale=(0.15, 0.12, 0.25), position=(x, 1.0, 0.5))

    # Tekerlekler
    for x in (-0.95, 0.95):
        for z in (1.45, -1.45):
            world(parent=root, model='cylinder', color=color.rgb(15, 15, 15),
                  rotation_z=90, scale=(0.7, 0.3, 0.7), position=(x, 0.35, z))
            world(parent=root, model='cylinder', color=color.rgb(170, 170, 175),
                  rotation_z=90, scale=(0.42, 0.34, 0.42),
                  position=(x * 1.02, 0.35, z))
    return root


# =====================================================================
# 5. OYUNCU VE YOL
# =====================================================================
player = Entity(position=(0, 0, 0))
build_car(player, CAR_COLORS[0])

ground = world(model='cube', color=color.rgb(60, 120, 55),
               scale=(400, 0.2, 1200), y=-0.12)
road = world(model='cube', color=color.rgb(45, 45, 50),
             scale=(ROAD_HALF * 2, 0.04, 1200), y=0.0)
edge_l = world(model='cube', color=color.rgb(235, 225, 170),
               scale=(0.18, 0.05, 1200), x=-ROAD_HALF, y=0.03)
edge_r = world(model='cube', color=color.rgb(235, 225, 170),
               scale=(0.18, 0.05, 1200), x=ROAD_HALF, y=0.03)

DASH_LEN = 3.5
DASH_GAP = 4.5
DASH_CYCLE = DASH_LEN + DASH_GAP
DASH_COUNT = 70
dashes = []
for x in (-LANE_W / 2, LANE_W / 2):
    for i in range(DASH_COUNT):
        d = world(model='cube', color=color.rgb(240, 240, 240),
                  scale=(0.14, 0.05, DASH_LEN), x=x, y=0.03)
        dashes.append([d, i * DASH_CYCLE])


# =====================================================================
# 6. OYUN DURUMU
# =====================================================================
speed = 0.0
score = 0.0
gold = 0
distance = 0.0
lane_x = 0.0
turbo_t = 0.0
mult_t = 0.0
crash_cd = 0.0
color_idx = 0
cam_mode = 'chase'
shop_open = False
next_coin_z = 30.0
traffic = []
coins = []


# =====================================================================
# 7. ARAYÜZ (HUD)
# =====================================================================
Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 150),
       scale=(window.aspect_ratio, 0.075), y=0.4625)
Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 150),
       scale=(window.aspect_ratio, 0.05), y=-0.475)

hud_km = Text(parent=camera.ui, text='0.00 km',
              position=window.top + Vec2(0, -0.035),
              origin=(0, 0.5), scale=2, color=color.white)
hud_score = Text(parent=camera.ui, text='',
                 position=window.top_left + Vec2(0.02, -0.035),
                 origin=(-0.5, 0.5), scale=1.5, color=color.yellow)
hud_gold = Text(parent=camera.ui, text='',
                position=window.top_right + Vec2(-0.02, -0.035),
                origin=(0.5, 0.5), scale=1.5, color=color.rgb(255, 210, 60))

Text(parent=camera.ui,
     text='W gaz | S fren | A/D sag-sol | C kamera | E magaza | Q cikis',
     position=window.bottom_left + Vec2(0.02, 0.012),
     origin=(-0.5, -0.5), scale=1, color=color.white)

SP_C = window.bottom_right + Vec2(-0.17, 0.2)
Entity(parent=camera.ui, model='circle', color=color.rgb(15, 15, 20),
       scale=0.22, position=SP_C)
needle = Entity(parent=camera.ui, model='quad', color=color.red,
                scale=(0.008, 0.095), origin=(0, -0.5), position=SP_C)
sp_text = Text(parent=camera.ui, text='0', position=SP_C + Vec2(0, -0.03),
               origin=(0, 0), scale=1.6, color=color.white)
Text(parent=camera.ui, text='km/h', position=SP_C + Vec2(0, -0.075),
     origin=(0, 0), scale=0.9, color=color.rgb(200, 200, 200))


def popup(txt, col):
    t = Text(parent=camera.ui, text=txt, position=Vec2(0, 0.25),
             origin=(0, 0), scale=2, color=col)
    destroy(t, delay=1)


# =====================================================================
# 8. MAĞAZA
# =====================================================================
shop_root = Entity(parent=camera.ui, enabled=False)
Entity(parent=shop_root, model='quad', color=color.rgba(10, 10, 20, 230),
       scale=(0.75, 0.65))
Text(parent=shop_root, text='MAGAZA', position=Vec2(0, 0.25),
     origin=(0, 0), scale=2, color=color.white)
shop_gold = Text(parent=shop_root, text='', position=Vec2(0, 0.17),
                 origin=(0, 0), scale=1.2, color=color.yellow)


def add_score(pts, text=None, col=color.yellow):
    global score
    if pts > 0 and mult_t > 0:
        pts *= 2
    score = max(0, score + pts)
    if text:
        popup(text, col)


def buy_turbo():
    global gold, turbo_t
    if gold >= 10:
        gold -= 10
        turbo_t += 10
        popup('TURBO!', color.azure)


def buy_mult():
    global gold, mult_t
    if gold >= 15:
        gold -= 15
        mult_t += 20
        popup('PUAN x2!', color.lime)


def buy_color():
    global gold, color_idx
    if gold >= 5:
        gold -= 5
        color_idx = (color_idx + 1) % len(CAR_COLORS)
        recolor_player()


def recolor_player():
    # Gövde, build_car içinde ilk eklenen 'Entity(quad)' gölgesinden sonra
    # ikinci çocuk olduğu için children[1] kullanılır.
    player.children[1].color = CAR_COLORS[color_idx]


def toggle_shop():
    global shop_open
    shop_open = not shop_open
    shop_root.enabled = shop_open


Button(parent=shop_root, text='Turbo +40 km/h (10 altin)',
       position=(0, 0.08), scale=(0.6, 0.1),
       color=color.rgb(40, 90, 160), on_click=buy_turbo)
Button(parent=shop_root, text='Puan x2, 20 sn (15 altin)',
       position=(0, -0.03), scale=(0.6, 0.1),
       color=color.rgb(40, 130, 60), on_click=buy_mult)
Button(parent=shop_root, text='Renk degistir (5 altin)',
       position=(0, -0.14), scale=(0.6, 0.1),
       color=color.rgb(120, 60, 140), on_click=buy_color)
Button(parent=shop_root, text='Kapat (E)',
       position=(0, -0.25), scale=(0.6, 0.1),
       color=color.rgb(120, 40, 40), on_click=toggle_shop)


# =====================================================================
# 9. TRAFİK
# =====================================================================
def spawn_traffic():
    lane = random.choice(LANES)
    if random.random() < 0.6:
        z = player.z + random.uniform(110, 240)
        kmh = random.uniform(70, 120)
    else:
        z = player.z - random.uniform(70, 150)
        kmh = random.uniform(170, 220)

    for t in traffic:
        if t['lane'] == lane and abs(t['root'].z - z) < 35:
            return

    root = Entity(position=(lane, 0, z))
    build_car(root, random.choice(TRAFFIC_COLORS))
    traffic.append({'root': root, 'lane': lane,
                    'v': kmh / 3.6,
                    'prev': z - player.z})


def update_traffic(dt):
    global speed, crash_cd
    for t in traffic[:]:
        root = t['root']
        root.z += t['v'] * dt
        rel = root.z - player.z
        dx = abs(root.x - lane_x)

        if crash_cd <= 0 and abs(rel) < 4.5 and dx < 1.9:
            speed *= 0.3
            add_score(-150, 'CARPTIN! -150', color.red)
            crash_cd = 1.5

        if abs(rel) < 6 and 1.9 <= dx < 3.2:
            add_score((3.2 - dx) * 30 * dt)

        if (rel > 0) != (t['prev'] > 0) and 1.9 <= dx < 4.2:
            pts = 100 + int((4.2 - dx) * 50)
            add_score(pts, f'MAKAS +{pts}', color.lime)

        t['prev'] = rel

        if abs(rel) > 300:
            destroy(root)
            traffic.remove(t)


# =====================================================================
# 10. ALTINLAR
# =====================================================================
def update_coins(dt):
    global next_coin_z, gold
    while next_coin_z < player.z + 300:
        lane = random.choice(LANES)
        n = 5 if random.random() < 0.3 else 1
        for i in range(n):
            c = world(model='sphere', color=color.rgb(255, 200, 0),
                      scale=0.6, position=(lane, 0.8, next_coin_z + i * 4))
            coins.append(c)
        next_coin_z += random.uniform(15, 35)

    for c in coins[:]:
        c.rotation_y += 200 * dt
        if c.z < player.z - 20:
            destroy(c)
            coins.remove(c)
            continue
        if abs(c.z - player.z) < 2.0 and abs(c.x - lane_x) < 1.6:
            gold += 1
            add_score(10)
            destroy(c)
            coins.remove(c)


# =====================================================================
# 11. YOL DÖNGÜSÜ
# =====================================================================
def update_road():
    road.z = ground.z = player.z
    edge_l.z = edge_r.z = player.z
    ws = player.z - 120
    for ent, base in dashes:
        ent.z = ws + ((base - ws) % DASH_CYCLE)


# =====================================================================
# 12. KAMERA
# =====================================================================
def update_camera(dt):
    if cam_mode == 'chase':
        tx, ty, tz, rx = player.x * 0.5, 3.0, player.z - 10, 10
    else:
        tx, ty, tz, rx = player.x, 32, player.z - 22, 55
    k = min(1, dt * 6)
    camera.x += (tx - camera.x) * k
    camera.y += (ty - camera.y) * k
    camera.z += (tz - camera.z) * k
    camera.rotation_x = rx
    camera.rotation_y = 0


# =====================================================================
# 13. HUD
# =====================================================================
def update_hud():
    hud_km.text = f'{distance / 1000:.2f} km'
    hud_score.text = f'PUAN: {int(score)}'
    hud_gold.text = f'ALTIN: {gold}'
    sp_text.text = str(int(speed))
    needle.rotation_z = 135 - min(1, speed / 260) * 270
    shop_gold.text = f'Altin: {gold}'


# =====================================================================
# 14. SÜRÜŞ
# =====================================================================
def drive(dt):
    global speed, distance, lane_x, turbo_t, mult_t, crash_cd

    top = TOP_SPEED + (TURBO_BONUS if turbo_t > 0 else 0)

    if held_keys['w']:
        speed += 55 * dt
    elif held_keys['s']:
        speed -= 130 * dt
    else:
        speed -= 18 * dt
    speed = max(0, min(top, speed))

    steer = (1 if held_keys['d'] else 0) - (1 if held_keys['a'] else 0)
    if speed > 5:
        lane_x += steer * dt * (3 + speed / 70)
    lane_x = max(-ROAD_HALF + 1, min(ROAD_HALF - 1, lane_x))
    player.x = lane_x
    player.rotation_y += (-steer * 8 - player.rotation_y) * min(1, dt * 6)

    v = speed / 3.6
    player.z += v * dt
    distance += v * dt

    turbo_t = max(0, turbo_t - dt)
    mult_t = max(0, mult_t - dt)
    crash_cd = max(0, crash_cd - dt)


# =====================================================================
# 15. GİRDİ
# =====================================================================
def input(key):
    global cam_mode
    if key == 'c':
        cam_mode = 'drone' if cam_mode == 'chase' else 'chase'
    elif key == 'e':
        toggle_shop()
    elif key == 'q':
        application.quit()


# =====================================================================
# 16. ANA DÖNGÜ
# =====================================================================
for _ in range(6):
    spawn_traffic()


def update():
    dt = min(time.dt, 0.05)

    if shop_open:
        update_camera(dt)
        update_hud()
        return

    drive(dt)
    update_road()
    update_coins(dt)

    if len(traffic) < MAX_TRAFFIC and random.random() < dt * 2.5:
        spawn_traffic()
    update_traffic(dt)

    update_camera(dt)
    update_hud()


app.run()