# -*- coding: utf-8 -*-
"""
Стол для сборки пазлов — модель FreeCAD по файлу «спецификация и размеры».
Запуск: FreeCAD -> Макрос -> Выполнить макрос (или `freecad puzzle_table_freecad.py`).

Система координат (мм): X — длинная сторона (1200), Y — короткая (800), Z — вверх.
Центр стола в (0,0), пол z=0.

Каждая деталь — отдельный объект Part::Feature с размерами ТОЧНО из спецификации.
Размеры, которых в спецификации нет, вынесены в блок ДОПУЩЕНИЯ и помечены (*).
"""
import math
import FreeCAD as App
import Part
from FreeCAD import Vector, Placement, Rotation

# ----------------------------------------------------------------------------
# ДОПУЩЕНИЯ (*) — в спецификации не заданы, можно править
# ----------------------------------------------------------------------------
FACADE_H = 41          # (*) высота фасада ящика: «400x» — вторая размерность не указана
FACADE_T = 15          # (*) толщина фасада
HANDLE_DIM = (100, 25, 10)   # (*) ручка ящика (самодельная): длина, высота, вылет
LATCH_DIM = (40, 20, 10)     # (*) защёлка ящика (самодельная)
HINGE_DIM = (70, 30, 1.5)    # (*) лист петли-бабочки (размер не указан)
LEG_MECH_DIM = (60, 40, 4)   # (*) механизм складывания ножки
LIFT_MECH_DIM = (400, 35, 15)  # (*) подъёмный механизм (самодельный), 2 шт.
MAGNET_TAPE_T = (10, 1.5)    # (*) магнитная лента: ширина, толщина (длина 800 из спец.)
FELT_T = 1.0                 # (*) толщина фетра
DRAWER_BOTTOM_W = 300        # (*) в спец. «550x35x3» — 35 похоже на опечатку; ширина дна = 300
# --- ПОДВИЖНЫЕ УЗЛЫ (углы в градусах, 0 = стол собран; меняйте здесь или в FreeCAD через Placement узла)
TILT_ANGLE = 0         # подъём ВСЕЙ столешницы (рама+фанера+фетр+ящики+оргстекло) с одной стороны
TILT_HINGE = 'back'    # ось подъёма: 'back' — задняя длинная сторона (+Y), 'front' — передняя (-Y)
LID_ANGLE = 0          # откидывание оргстекла на петлях-бабочках (передняя длинная сторона)
DRAWER_OPEN = {}       # выдвижение ящиков, мм: {1: 250, 3: 100} — номера ящиков 1..4
BRACE_LEN = 250        # (*) длина косынки «жёсткость стола» по эскизу (в спец. 750 не используется)

# ----------------------------------------------------------------------------
# СПЕЦИФИКАЦИЯ (L x W x H, мм)
# ----------------------------------------------------------------------------
SPEC = dict(
    rail_long=(1220, 40, 20), rail_long_n=2,        # планка по длинной стороне - столешница
    rail_short=(820, 40, 20), rail_short_n=2,       # планка по короткой стороне - столешница
    top_ply=(1200, 800, 8),                         # столешница фанера берёзовая
    mid_short=(800, 35, 15),                        # планка середина короткая
    mid_long=(1200, 35, 15),                        # планка середина длинная
    felt=(1250, 850),                               # фетр
    plexi=(1200, 800, 3),                           # оргстекло
    hinge_n=2,                                      # петли-бабочки
    magnet_len=800, magnet_n=2,                     # магнитная лента на оргстекло
    lift_n=2,                                       # подъёмный механизм
    drawer_long=(600, 35, 10), drawer_long_n=8,     # длинные планки ящика
    drawer_short=(300, 35, 10), drawer_short_n=8,   # короткие планки ящика
    facade_w=400, facade_n=4,                       # фасады ящика
    handle_n=4,                                     # ручки
    roller=(550, 35, 10), roller_n=8,               # роликовые направляющие
    latch_n=4,                                      # защёлки
    drawer_bottom_l=550, drawer_bottom_t=3, drawer_bottom_n=4,  # дно ящика
    lift_ply=(1200, 800, 6),                        # фанера для подъёмного механизма
    sub_long=(1220, 70, 20), sub_long_n=2,          # длинные планки подстолья
    sub_short=(820, 70, 20), sub_short_n=2,         # короткие планки подстолья
    leg=(50, 50, 730), leg_n=4,                     # брус для ножек
    brace_750=(750, 40, 20), brace_750_n=2,         # перемычки для ножек 750
    brace_650=(650, 40, 20), brace_650_n=2,         # перемычки для ножек 650
    leg_mech_n=4,                                   # механизм для складывания ножек
)

# цвета
OAK = (0.78, 0.60, 0.36); PLY = (0.86, 0.72, 0.50); FELT = (0.10, 0.22, 0.17)
STEEL = (0.70, 0.71, 0.74); PLEXI = (0.75, 0.90, 0.95)

doc = App.newDocument("PuzzleTable")
GROUPS = {}


# Подвижные узлы — контейнеры App::Part: у них есть Placement, поэтому весь узел
# (со всеми деталями внутри) поворачивается/сдвигается как одно тело.
# Иерархия: Столешница_поднимаемая -> { Крышка_оргстекло, Ящик_1..4 }
TILT = "Столешница_поднимаемая"; LID = "Крышка_оргстекло"
PARTS = {TILT: None, LID: TILT, "Ящик_1": TILT, "Ящик_2": TILT, "Ящик_3": TILT, "Ящик_4": TILT}


def group(name):
    if name not in GROUPS:
        if name in PARTS:
            GROUPS[name] = doc.addObject("App::Part", name)
            GROUPS[name].Label = name
            if PARTS[name]:
                group(PARTS[name]).addObject(GROUPS[name])
        else:
            GROUPS[name] = doc.addObject("App::DocumentObjectGroup", name)
            GROUPS[name].Label = name
    return GROUPS[name]


def add(grp, name, dims, pos, color, rot=None, center=False):
    """dims=(dx,dy,dz) вдоль осей X,Y,Z; pos=(x,y,z) — минимальный угол (или центр, если center=True)."""
    dx, dy, dz = dims
    if rot is None:
        shp = Part.makeBox(dx, dy, dz, Vector(*pos))
    else:  # поворот вокруг оси Y вокруг центра бруса
        shp = Part.makeBox(dx, dy, dz, Vector(-dx / 2, -dy / 2, -dz / 2))
        shp.Placement = Placement(Vector(*pos), Rotation(Vector(0, 1, 0), rot))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shp
    obj.Label = name
    try:
        obj.ViewObject.ShapeColor = color
    except Exception:
        pass
    group(grp).addObject(obj)
    return obj


def cyl_x(grp, name, length, r, pos_center, color):
    c = Part.makeCylinder(r, length, Vector(pos_center[0] - length / 2, pos_center[1], pos_center[2]), Vector(1, 0, 0))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = c
    obj.Label = name
    try:
        obj.ViewObject.ShapeColor = color
    except Exception:
        pass
    group(grp).addObject(obj)
    return obj


# ----------------------------------------------------------------------------
# ВЕРТИКАЛЬНАЯ КОМПОНОВКА (z)
# ----------------------------------------------------------------------------
LEG_H = SPEC['leg'][2]                      # 730
Z_SUB_TOP = LEG_H                           # верх подстолья = верх ножек
Z_SUB_BOT = Z_SUB_TOP - SPEC['sub_long'][1]  # 660
Z_LIFT0 = Z_SUB_TOP                         # фанера подъёмного механизма
Z_LIFT1 = Z_LIFT0 + SPEC['lift_ply'][2]     # 736
RAIL_H = SPEC['drawer_long'][1] + SPEC['top_ply'][2]   # 43 — ВЫШЕ спец. (40): ящик 35 + фанера 8, по решению заказчика
Z_RAIL0 = Z_LIFT1
Z_RAIL1 = Z_RAIL0 + RAIL_H                  # 776
DRAWER_H = SPEC['drawer_long'][1]           # 35
Z_DRAWER0 = Z_LIFT1
Z_TOPPLY0 = Z_DRAWER0 + DRAWER_H            # 771 — верх ящика = низ фанеры столешницы
Z_TOPPLY1 = Z_TOPPLY0 + SPEC['top_ply'][2]  # 779
Z_FELT0 = Z_TOPPLY1
Z_PLEXI0 = Z_FELT0 + FELT_T
Z_PLEXI1 = Z_PLEXI0 + SPEC['plexi'][2]

TW, TL = SPEC['top_ply'][0], SPEC['top_ply'][1]   # 1200 x 800
HX, HY = TW / 2, TL / 2                           # 600, 400

# ----------------------------------------------------------------------------
# ПОДСТОЛЬЕ
# ----------------------------------------------------------------------------
g = "Подстолье"
sl = SPEC['sub_long']; ss = SPEC['sub_short']
for i, sy in enumerate((-1, 1)):                  # 2 × 1220x70x20
    add(g, "Подстолье_длинная_%d" % (i + 1), (sl[0], sl[2], sl[1]), (-sl[0] / 2, sy * 400 - sl[2] / 2, Z_SUB_BOT), OAK)
for i, sx in enumerate((-1, 1)):                  # 2 × 820x70x20 (вдоль Y, между длинными)
    add(g, "Подстолье_короткая_%d" % (i + 1), (ss[2], ss[0] - 2 * sl[2], ss[1]),
        (sx * (sl[0] / 2 - ss[2] / 2) - ss[2] / 2, -(ss[0] - 2 * sl[2]) / 2, Z_SUB_BOT), OAK)
# NB: короткая планка 820 в углах перекрывается с длинной на 20 мм — длина в модели 780 (820-2*20),
#     чтобы не было пересечения тел; габарит подстолья остаётся 1220 x 820.

# ножки 50x50x730: внутри подстолья, в углах
g = "Ножки"
lg = SPEC['leg']
n = 0
for sx in (-1, 1):
    for sy in (-1, 1):
        n += 1
        cx = sx * (sl[0] / 2 - ss[2] - lg[0] / 2)       # внутренний угол подстолья
        cy = sy * (ss[0] / 2 - sl[2] - lg[1] / 2 - 15)   # 15 мм зазор -> между ножками внутри 650 (перемычка 650)
        add(g, "Ножка_%d" % n, lg, (cx - lg[0] / 2, cy - lg[1] / 2, 0), OAK)
LEG_CX = sl[0] / 2 - ss[2] - lg[0] / 2          # 535
LEG_CY = ss[0] / 2 - sl[2] - lg[1] / 2 - 15     # 350
# расстояние между ножками по Y в свету
gap_y = 2 * (LEG_CY - lg[1] / 2)                 # 650 -> под перемычку 650
gap_x = 2 * (LEG_CX - lg[0] / 2)                 # 1020

# перемычки 650x40x20 — по коротким сторонам между ножками (боковой вид), z≈150
g = "Перемычки"
b6 = SPEC['brace_650']
for i, sx in enumerate((-1, 1)):
    add(g, "Перемычка_650_%d" % (i + 1), (b6[2], b6[0], b6[1]),
        (sx * LEG_CX - b6[2] / 2, -b6[0] / 2, 130), OAK)

# механизм складывания ножек ×4 (размер не задан (*))
g = "Механизмы"
n = 0
for sx in (-1, 1):
    for sy in (-1, 1):
        n += 1
        add(g, "Механизм_ножки_%d" % n, (LEG_MECH_DIM[0], LEG_MECH_DIM[1], LEG_MECH_DIM[2]),
            (sx * LEG_CX - LEG_MECH_DIM[0] / 2, sy * LEG_CY - LEG_MECH_DIM[1] / 2, Z_SUB_BOT - LEG_MECH_DIM[2]), STEEL)

# ----------------------------------------------------------------------------
# ФАНЕРА ПОДЪЁМНОГО МЕХАНИЗМА 1200x800x6 + подъёмный механизм ×2 (*)
# ----------------------------------------------------------------------------
g = "Подстолье"
lp = SPEC['lift_ply']
add(g, "Фанера_подъёмного_механизма", lp, (-lp[0] / 2, -lp[1] / 2, Z_LIFT0), PLY)
for i, sy in enumerate((-1, 1)):
    add("Механизмы", "Подъёмный_механизм_%d" % (i + 1), LIFT_MECH_DIM,
        (-LIFT_MECH_DIM[0] / 2, sy * 200 - LIFT_MECH_DIM[1] / 2, Z_LIFT0 - LIFT_MECH_DIM[2]), OAK)

# ----------------------------------------------------------------------------
# СТОЛЕШНИЦА: окантовка, середина, фанера, фетр, оргстекло
# ----------------------------------------------------------------------------
g = TILT      # всё ниже — единый поднимаемый узел
rl = SPEC['rail_long']
for i, sy in enumerate((-1, 1)):                    # 2 × 1220x40x20 по длинным сторонам
    yc = sy * (HY + rl[2] / 2)
    add(g, "Планка_столешницы_длинная_%d" % (i + 1), (rl[0], rl[2], rl[1]), (-rl[0] / 2, yc - rl[2] / 2, Z_RAIL0), OAK)
# Короткие планки 820x40x20 на торцах не нужны (решение заказчика): там фасады ящиков.

add(g, "Планка_середина_длинная", (SPEC['mid_long'][0], SPEC['mid_long'][2], SPEC['mid_long'][1]),
    (-SPEC['mid_long'][0] / 2, -SPEC['mid_long'][2] / 2, Z_DRAWER0), OAK)
add(g, "Планка_середина_короткая", (SPEC['mid_short'][2], SPEC['mid_short'][0], SPEC['mid_short'][1]),
    (-SPEC['mid_short'][2] / 2, -SPEC['mid_short'][0] / 2, Z_DRAWER0), OAK)

tp = SPEC['top_ply']
add(g, "Столешница_фанера_берёзовая", tp, (-tp[0] / 2, -tp[1] / 2, Z_TOPPLY0), PLY)
fl = SPEC['felt']
add(g, "Фетр", (fl[0], fl[1], FELT_T), (-fl[0] / 2, -fl[1] / 2, Z_FELT0), FELT)
px = SPEC['plexi']
add(LID, "Оргстекло", px, (-px[0] / 2, -px[1] / 2, Z_PLEXI0), PLEXI)

# магнитная лента 2 × 800 — под оргстеклом вдоль сторон 800
for i, sx in enumerate((-1, 1)):
    add(LID, "Магнитная_лента_%d" % (i + 1), (MAGNET_TAPE_T[0], SPEC['magnet_len'], MAGNET_TAPE_T[1]),
        (sx * (HX - 5) - MAGNET_TAPE_T[0] / 2, -SPEC['magnet_len'] / 2, Z_PLEXI0 - MAGNET_TAPE_T[1]), STEEL)

# петли-бабочки ×2 по длинной стороне (*)
for i, xc in enumerate((-380, 410)):
    add(LID, "Петля_бабочка_%d_лист_оргстекло" % (i + 1), HINGE_DIM,
        (xc - HINGE_DIM[0] / 2, -HY, Z_PLEXI1), STEEL)
    add(TILT, "Петля_бабочка_%d_лист_планка" % (i + 1), (HINGE_DIM[0], rl[2], HINGE_DIM[2]),
        (xc - HINGE_DIM[0] / 2, -HY - rl[2], Z_PLEXI0), STEEL)
    cyl_x(LID, "Петля_бабочка_%d_ось" % (i + 1), HINGE_DIM[0], 3, (xc, -HY - 0.5, Z_PLEXI1 + 3), STEEL)

# ----------------------------------------------------------------------------
# ЯЩИКИ ×4 (по 2 на каждой стороне 800)
# ----------------------------------------------------------------------------
dl = SPEC['drawer_long']; ds = SPEC['drawer_short']
fw = SPEC['facade_w']; rol = SPEC['roller']
n = 0
for sx in (-1, 1):
    for k, sy in enumerate((-1, 1)):
        n += 1
        d = 0          # геометрия строится в закрытом положении; выдвижение — Placement узла «Ящик_n» (см. ниже)
        yc = sy * fw / 2
        gname = "Ящик_%d" % n
        # фасад 400 x FACADE_H x FACADE_T
        xf_in = sx * (HX + d)                         # внутренняя грань фасада
        xf0 = xf_in if sx == 1 else xf_in - FACADE_T
        add(gname, "Фасад_%d" % n, (FACADE_T, fw - 2, FACADE_H), (xf0, yc - fw / 2 + 1, Z_DRAWER0 + 1), OAK)
        # ручка (*)
        hx_ = xf0 + FACADE_T if sx == 1 else xf0 - HANDLE_DIM[2]
        add(gname, "Ручка_%d" % n, (HANDLE_DIM[2], HANDLE_DIM[0], HANDLE_DIM[1]),
            (hx_, yc - HANDLE_DIM[0] / 2, Z_DRAWER0 + FACADE_H / 2 - HANDLE_DIM[1] / 2 + 1), OAK)
        # корпус: 2 × 600x35x10 + 2 × 300x35x10 (внутри от фасада)
        bx0 = xf_in - dl[0] if sx == 1 else xf_in             # x-диапазон корпуса [bx0, bx0+600]
        bw = ds[0] + 2 * dl[2]                                # 320 по Y
        for j, sj in enumerate((-1, 1)):
            add(gname, "Ящик_%d_длинная_%d" % (n, j + 1), (dl[0], dl[2], dl[1]),
                (bx0, yc + sj * (ds[0] / 2 + dl[2] / 2) - dl[2] / 2, Z_DRAWER0), OAK)
        for j, xs in enumerate((bx0, bx0 + dl[0] - ds[2])):
            add(gname, "Ящик_%d_короткая_%d" % (n, j + 1), (ds[2], ds[0], ds[1]),
                (xs, yc - ds[0] / 2, Z_DRAWER0), OAK)
        # дно 550 x 300 x 3 (*ширина)
        add(gname, "Дно_%d" % n, (SPEC['drawer_bottom_l'], DRAWER_BOTTOM_W, SPEC['drawer_bottom_t']),
            (bx0 + ds[2], yc - DRAWER_BOTTOM_W / 2, Z_DRAWER0 + 3), PLY)
        # 2 роликовые направляющие 550x35x10 (вдоль боков ящика, снаружи)
        for j, sj in enumerate((-1, 1)):
            yr = yc + sj * (bw / 2 + rol[2] / 2)
            add(gname, "Ролик_%d_%d" % (n, j + 1), (rol[0], rol[2], rol[1]),
                (bx0 + (dl[0] - rol[0]) / 2, yr - rol[2] / 2, Z_DRAWER0), STEEL)
        # защёлка (*) на задней стенке
        xl = bx0 + ds[2] if sx == 1 else bx0 + dl[0] - ds[2] - LATCH_DIM[2]
        add(gname, "Защёлка_%d" % n, (LATCH_DIM[2], LATCH_DIM[0], LATCH_DIM[1]),
            (xl, yc - LATCH_DIM[0] / 2, Z_DRAWER0 + 3), OAK)

# ----------------------------------------------------------------------------
# ПОДВИЖНЫЕ УЗЛЫ: Placement контейнеров
# ----------------------------------------------------------------------------
def set_tilt(angle_deg, hinge=TILT_HINGE):
    """Поднять столешницу: ось — внешняя кромка длинной стороны на уровне низа рамы."""
    rail_out = HY + SPEC['rail_long'][2]
    if hinge == 'back':
        cy, a = rail_out, -angle_deg      # ось сзади, передняя сторона идёт вверх
    else:
        cy, a = -rail_out, angle_deg
    GROUPS[TILT].Placement = Placement(Vector(0, 0, 0), Rotation(Vector(1, 0, 0), a), Vector(0, cy, Z_LIFT1))


def set_lid(angle_deg):
    """Откинуть оргстекло: ось — линия петель на передней стороне (в системе узла столешницы)."""
    GROUPS[LID].Placement = Placement(Vector(0, 0, 0), Rotation(Vector(1, 0, 0), angle_deg), Vector(0, -HY, Z_PLEXI0))


def set_drawer(num, mm):
    """Выдвинуть ящик №num (1..4) на mm мм наружу."""
    sx = -1 if num <= 2 else 1
    GROUPS["Ящик_%d" % num].Placement = Placement(Vector(sx * mm, 0, 0), Rotation())


set_tilt(TILT_ANGLE)
set_lid(LID_ANGLE)
for _n in range(1, 5):
    set_drawer(_n, DRAWER_OPEN.get(_n, 0))

doc.recompute()

# ----------------------------------------------------------------------------
# Проверка по спецификации: количество деталей
# ----------------------------------------------------------------------------
def count(prefix):
    return len([o for o in doc.Objects if o.Label.startswith(prefix)])

print("=== Проверка количества деталей ===")
checks = [("Подстолье_длинная", 2), ("Подстолье_короткая", 2), ("Ножка_", 4), ("Перемычка_650", 2),
          ("Косынка_", 2), ("Механизм_ножки", 4), ("Подъёмный_механизм", 2),
          ("Планка_столешницы_длинная", 2), ("Планка_столешницы_короткая", 0),
          ("Фасад_", 4), ("Ручка_", 4), ("Дно_", 4), ("Ролик_", 8), ("Защёлка_", 4),
          ("Магнитная_лента", 2)]
for pref, need in checks:
    got = count(pref)
    print("%-32s %d (по спец. %d) %s" % (pref, got, need, "OK" if got == need else "<-- ПРОВЕРИТЬ"))
print("Планки ящиков: длинные %d (8), короткие %d (8)" % (
    len([o for o in doc.Objects if "_длинная_" in o.Label and o.Label.startswith("Ящик_")]),
    len([o for o in doc.Objects if "_короткая_" in o.Label and o.Label.startswith("Ящик_")])))

try:
    import FreeCADGui
    FreeCADGui.activeDocument().activeView().viewIsometric()
    FreeCADGui.SendMsgToActiveView("ViewFit")
except Exception:
    pass
