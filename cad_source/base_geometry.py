#!/usr/bin/env python3
"""Mimic R5a CONCEPT head: original exposed animatronic endoskeleton (CadQuery 2.8, mm).

Datums (R4): X right, Y rear, Z up, face toward -Y, head deck underside Z0.
Outputs (OUT dir): STEP/parts/*.step (plain SI mm, assembly coordinates), STEP/assembly/*.step
(named instances incl. purchased placeholders), STL/*.stl (flat print orientation), parts_meta.json,
parameters.json, scene.json (instances, groups, materials) for posing/rendering.
Status: concept CAD. Mechanism geometry is real; fasteners/inserts not yet detailed; nothing printed.
Usage: python build_r5a.py OUT_DIR R4_STEP_PARTS_DIR
"""
import json, math, sys, pathlib
import cadquery as cq

OUT = pathlib.Path(__file__).parent; R4P = OUT / "references"


# ---------------------------------------------------------------- parameters
# value, unit, source
PM = {
 "eye_x": (33.75, "mm", "R4 interface"), "eye_y": (-36.25, "mm", "R4 globe centre (pivot moved here)"),
 "eye_z": (112.5, "mm", "R4 interface"), "globe_r": (16.0, "mm", "design: Phase1 audit 30-32 mm globes"),
 "globe_cavity_r": (13.5, "mm", "design: 2.5 mm shell"),
 "bottom_cone_half_deg": (36.0, "deg", "derived: pitch 18 + asin(3.5/13.5)=15 + 3 margin"),
 "pin_d": (2.0, "mm", "M2 screw/pin"), "pin_hole_d": (2.2, "mm", "fdm: M2 running clearance (calibrate)"),
 "block": (8.0, "mm", "design: U-joint cross block"), "post_r": (3.5, "mm", "design: vertical eye post from below"),
 "C0": ((0.0, 24.0, 0.0), "mm", "design: control ball directly behind eye centre (decoupled yaw/pitch); 24 keeps sockets clear of globes"),
 "ball_r": (2.0, "mm", "design: 4 mm ball in wrap-around socket (60 deg opening, M1.6 stud)"),
 "lid_r_in": (17.2, "mm", "design: 1.2 mm gap to globe"), "lid_r_out": (18.7, "mm", "design: 1.5 shell"),
 "lid_arm_x": ((17.8, 19.3), "mm", "design"), "prong_x": ((19.8, 22.8), "mm", "design"),
 "lid_lever": ((9.8, -4.1), "mm", "design: lever pin (y,z) from lid axis; phased -22.5 deg so it is horizontal mid-travel (no toggle)"),
 "lid_rod_x": (16.5, "mm", "design: lid rod plane offset from eye centre (inner side of the outer arm)"),
 "lid_pin0_z": (186.0, "mm", "design: lid horn pin height at lid 0"),
 "lid_horn_phase_deg": (35.0, "deg", "design: horn arm 35 deg below horizontal at lid 0 -> horizontal at mid-travel (no toggle)"),
 "horn_r": (10.0, "mm", "lid horns: OEM single-arm hole radius (verify)"),
 "eye_horn_r": (14.0, "mm", "yaw/pitch horns: outer OEM hole radius for +-8.9 mm throw (verify)"),
 "yaw_ball": ((2.5, -12.25, 140.0), "mm", "design: tab ball for yaw rod (rod along +X)"), "yaw_rod_len": (30.0, "mm", "design: longer rod reduces pitch->yaw coupling"),
 "pitch_ball": ((0.0, -12.25, 146.5), "mm", "design: tab-top ball for pitch rod (rod along +Z)"), "pitch_rod_len": (30.0, "mm", "design: longer rod reduces yaw->pitch coupling"),
 "eye_deck_z": ((80.0, 84.0), "mm", "design: plate under the eyes carrying posts and lid prongs"),
 "jaw_axis": ((12.5, 56.25), "mm", "R4 interface (y,z)"), "ramus_x": ((59.5, 64.5), "mm", "design"),
 "jaw_tip_x": (-57.5, "mm", "design: jaw servo spline tip"), "chin_z": (8.0, "mm", "design: Phase1 proportion"),
 "wall_x": ((68.0, 74.0), "mm", "design: lower side wall"), "plate_x": ((74.0, 79.0), "mm", "design: upper cranial plate"),
 "mask_y": ((-62.0, -57.5), "mm", "design: face plane"), "orbit_wh": ((42.0, 36.0), "mm", "design: anatomical orbit"),
 "deck_z": ((154.0, 158.0), "mm", "design: mechanism deck"), "deck_y": ((-21.0, 20.0), "mm", "design: clears lid rods"),
 "neck_pattern": ((80.0, 45.0), "mm", "R4 interface"),
 "m3_clear": (3.4, "mm", "R4 fit coupon value"), "teeth_gap_front": (2.5, "mm", "design"), "molar_gap": (0.8, "mm", "design: soft stop before incisors"),
}
P = {k: v[0] for k, v in PM.items()}
EX, EY, EZ, GR = P["eye_x"], P["eye_y"], P["eye_z"], P["globe_r"]
_hr = P["eye_horn_r"]
_yb, _pb = P["yaw_ball"], P["pitch_ball"]
P["yaw_pin0"] = (_yb[0] + P["yaw_rod_len"], _yb[1], _yb[2]); P["yaw_S"] = (P["yaw_pin0"][0], _yb[1] + _hr, _yb[2])
P["pitch_pin0"] = (_pb[0], _pb[1], _pb[2] + P["pitch_rod_len"]); P["pitch_S"] = (_pb[0], _pb[1] + _hr, P["pitch_pin0"][2])
_ly, _lz = P["lid_lever"]; _ph = math.radians(P["lid_horn_phase_deg"]); _lr = P["horn_r"]
P["lid_pin0"] = (P["lid_rod_x"], EY + _ly, P["lid_pin0_z"])                  # x is an offset from the eye centre
P["lid_S"] = (P["lid_rod_x"], EY + _ly + _lr * math.cos(_ph), P["lid_pin0_z"] + _lr * math.sin(_ph))
for k in ("yaw_pin0", "yaw_S", "pitch_pin0", "pitch_S", "lid_pin0", "lid_S"):
    PM[k] = (P[k], "mm", "derived: horn arm perpendicular to its rod at neutral")
V = cq.Vector


# ---------------------------------------------------------------- helpers
def prism(pts3, vec):
    w = cq.Wire.makePolygon([V(*p) for p in pts3], close=True)
    return cq.Solid.extrudeLinear(cq.Face.makeFromWires(w), V(*vec))


def prism_yz(pts, x0, t):   # (y,z) polygon extruded along +X from x0
    return prism([(x0, y, z) for y, z in pts], (t, 0, 0))


def prism_xz(pts, y0, t):   # (x,z) polygon extruded along +Y from y0
    return prism([(x, y0, z) for x, z in pts], (0, t, 0))


def prism_xy(pts, z0, t):
    return prism([(x, y, z0) for x, y in pts], (0, 0, t))


def box(c, s):
    return cq.Solid.makeBox(s[0], s[1], s[2], V(c[0] - s[0] / 2, c[1] - s[1] / 2, c[2] - s[2] / 2))


def cyl(r, p0, p1):
    a, b = V(*p0), V(*p1)
    return cq.Solid.makeCylinder(r, (b - a).Length, a, (b - a).normalized())


def sphere(r, c):
    return cq.Solid.makeSphere(r, V(*c), angleDegrees1=-90, angleDegrees2=90)


def U(*s):
    a = s[0]
    for b in s[1:]:
        a = a.fuse(b)
    return a.clean()


def D(a, *s):
    for b in s:
        a = a.cut(b)
    return a.clean()


def catmull(ctrl, n=10):
    out = []; m = len(ctrl)
    for i in range(m):
        p0, p1, p2, p3 = ctrl[i - 1], ctrl[i], ctrl[(i + 1) % m], ctrl[(i + 2) % m]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


def ellipse_pts(c, a, b, n=40, rot=0.0):
    cr, sr = math.cos(rot), math.sin(rot)
    return [(c[0] + a * math.cos(t) * cr - b * math.sin(t) * sr, c[1] + a * math.cos(t) * sr + b * math.sin(t) * cr)
            for t in [2 * math.pi * i / n for i in range(n)]]


def rrect_pts(c, w, h, r, n=8):
    pts = []
    for cx, cy, a0 in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((c[0] + cx + r * math.cos(a), c[1] + cy + r * math.sin(a)))
    return pts


def mirror_x(s):
    return s.mirror("YZ")


parts, inst = {}, []


def part(pid, name, shape, mat, qty=1):
    assert shape.isValid(), pid
    sols = shape.Solids()
    assert len(sols) == 1, f"{pid} has {len(sols)} solids"
    parts[pid] = dict(id=pid, name=name, shape=sols[0], mat=mat, qty=qty)
    return sols[0]


def place(name, pid, shape, group, mat):
    inst.append(dict(name=name, pid=pid, shape=shape, group=group, mat=mat))


# ---------------------------------------------------------------- servo placeholder (R4 geometry)
def servo_local():
    body = box((0, 6, -17.35), (12.2, 22.8, 22.3))
    tabs = box((0, 6, -9), (12.2, 32.5, 2))
    for dy in (-14.0, 14.0):
        tabs = D(tabs, cyl(1.15, (0, 6 + dy, -11), (0, 6 + dy, -7)))
    spline = cyl(2.5, (0, 0, -6.2), (0, 0, 0))
    boss = cyl(5.0, (0, 0, -6.2), (0, 0, -6.19 + 0.01))
    return U(body, tabs, spline)


def at_frame(shape, origin, z_dir, y_dir):
    z = V(*z_dir).normalized(); y = V(*y_dir).normalized(); x = y.cross(z)
    return shape.moved(cq.Location(cq.Plane(V(*origin), x, z)))


def servo_at(tip, shaft_dir, length_dir):
    return at_frame(servo_local(), tip, shaft_dir, length_dir)


def horn_arm(S, P_, axis, t=2.0):
    """single-arm OEM horn from axis point S to hole P_, thickness t along axis"""
    a = V(*axis).normalized()
    hub = cyl(3.6, tuple(V(*S) - a * (t / 2)), tuple(V(*S) + a * (t / 2)))
    d = V(*P_) - V(*S); L = d.Length; u = d.normalized(); w = a.cross(u)
    c = V(*S) + d * 0.5
    arm = box((0, 0, 0), (L, 4.0, t))
    arm = arm.moved(cq.Location(cq.Plane(c, u, a)))
    tip = cyl(2.6, tuple(V(*P_) - a * (t / 2)), tuple(V(*P_) + a * (t / 2)))
    return U(hub, arm, tip)


def rod(p0, p1, r=1.0, trim=3.0):
    a, b = V(*p0), V(*p1); u = (b - a).normalized()
    return cyl(r, tuple(a + u * trim), tuple(b - u * trim))


# ================================================================ STRUCTURE
# Skull silhouette (y,z) used for side walls / plates / arches
SIL = catmull([(-58, 132), (-57, 152), (-52, 182), (-37, 206), (-12, 222), (20, 227), (50, 216), (72, 192),
               (82, 160), (81, 128), (74, 100), (60, 72), (46, 46), (40, 20), (34, 4), (16, 30), (-20, 34), (-21, 100), (-40, 118)], 8)


def sil_top_z(y):
    zs = [p[1] for p in SIL if abs(p[0] - y) < 3.0 and p[1] > 120]
    return max(zs) if zs else None


# --- P20 base plate (neck interface 80x45, R4 cable opening 16x18 at (0,8))
bp = prism_xy([(-46, -28), (46, -28), (46, 30), (68, 30), (68, 58), (-68, 58), (-68, 30), (-46, 30)], 0, 6)   # walls bolt to its side edges
for sx in (-1, 1):
    for sy in (-1, 1):
        bp = D(bp, cyl(P["m3_clear"] / 2, (sx * 40, sy * 22.5, -1), (sx * 40, sy * 22.5, 7)))
bp = D(bp, box((0, 8, 3), (16, 18, 8)))
P20 = part("P20", "skull_base_plate", bp, "frame_dark")

# --- P21/P22 lower side walls (YZ plane, |x| 68..74)
lw_pts = [(-20, 34), (-20, 128), (80.5, 128), (81, 124), (74, 100), (60, 72), (46, 46), (40, 20), (34, 0), (18, 0), (16, 30)]
lw = prism_yz(lw_pts, -74, 6)
for (yc, zc, a, b, r) in [(36, 100, 27, 17, 0.15), (60, 58, 9, 17, 0.55), (-8, 112, 6.5, 8, 0.0), (32, 26, 7, 9, 0.0), (10, 92, 9, 7, 0.0)]:
    lw = D(lw, prism_yz(ellipse_pts((yc, zc), a, b, 36, r), -75, 8))
# jaw pivot boss + bore (outboard support for both rami)
jy, jz = P["jaw_axis"]
lw = U(lw, cyl(8.5, (-77, jy, jz), (-68, jy, jz)))
lw = D(lw, cyl(1.7, (-80, jy, jz), (-60, jy, jz)))
lwL = lw
P21 = part("P21", "lower_wall_L", lwL, "frame_dark")
P22 = part("P22", "lower_wall_R", mirror_x(lwL), "frame_dark")

# --- P23/P24 upper cranial plates (|x| 74..79), layered over the lower walls
up_pts = catmull([(-56, 122), (-58, 138), (-55, 153), (-46, 166), (-24, 175), (10, 179), (45, 175), (70, 164),
                  (81, 146), (81, 124), (74, 112), (20, 110), (-30, 112), (-46, 114)], 8)
upL = prism_yz(up_pts, -79, 5)
for (yc, zc, a, b, r) in [(-20, 150, 24, 13, -0.2), (23, 155, 21, 14, 0.25), (60, 142, 11, 16, 0.0)]:
    upL = D(upL, prism_yz(ellipse_pts((yc, zc), a, b, 36, r), -80, 7))
P23 = part("P23", "upper_cranial_plate_L", upL, "frame_steel")
P24 = part("P24", "upper_cranial_plate_R", mirror_x(upL), "frame_steel")


# --- P25-27 cranial arches (XZ bands at y = -45, 0, 50), P28 sagittal crest
def arch(yc, t=8, band=9, spring=152):
    top = sil_top_z(yc) - 2.0
    a, b = 74.0, top - spring
    outer = [(a * math.cos(t_), spring + b * math.sin(t_)) for t_ in [math.pi * i / 48 for i in range(49)]]
    inner = [((a - band) * math.cos(t_), spring + (b - band) * math.sin(t_)) for t_ in [math.pi * i / 48 for i in range(48, -1, -1)]]
    pts = outer + inner
    s = prism_xz(pts, yc - t / 2, t)
    # lightening holes along the band
    for k in range(1, 6):
        t_ = math.pi * k / 6
        cx, cz = (a - band / 2) * math.cos(t_), spring + (b - band / 2) * math.sin(t_)
        s = D(s, cyl(2.2, (cx, yc - 10, cz), (cx, yc + 10, cz)))
    return s


P25 = part("P25", "cranial_arch_front", arch(-45), "frame_dark")
P26 = part("P26", "cranial_arch_mid", arch(2), "frame_dark")
P27 = part("P27", "cranial_arch_rear", arch(52), "frame_dark")
crest_out = [p for p in SIL if p[1] > 150 and -52 <= p[0] <= 78]
crest_in = [(y, z - 9) for y, z in reversed(crest_out)]
crest = prism_yz(crest_out + crest_in, -3, 6)
# halving joints: crest keeps its upper half, arches keep their lower half where they cross
crest_mid = [(y, z - 4.5) for y, z in crest_out]
upper_band = prism_yz(crest_out + list(reversed(crest_mid)), -4, 8)
crest_up = crest.intersect(upper_band).clean()
crest_lo = D(crest, crest_up)
arches = {}
for pid_, sh_ in (("P25", P25), ("P26", P26), ("P27", P27)):
    arches[pid_] = D(sh_, crest_up)
    crest = D(crest, sh_.intersect(crest_lo))
P25 = part("P25", "cranial_arch_front", arches["P25"], "frame_dark")
P26 = part("P26", "cranial_arch_mid", arches["P26"], "frame_dark")
P27 = part("P27", "cranial_arch_rear", arches["P27"], "frame_dark")
P28 = part("P28", "sagittal_crest", crest, "frame_steel")

# --- P29 face mask (XZ plane, y -62..-57.5): brow, orbit rims, nasal, cheek bar
my0, my1 = P["mask_y"]; mt = my1 - my0
ow, oh = P["orbit_wh"]
outline = catmull([(-79, 126), (-70, 132), (-52, 143), (-28, 146), (-9, 141), (0, 138), (9, 141), (28, 146), (52, 143),
                   (70, 132), (79, 126), (66, 118), (63, 100), (60, 87), (42, 81), (25, 72), (14, 64), (-14, 64), (-25, 72),
                   (-42, 81), (-60, 87), (-63, 100), (-66, 118)], 6)
mask = prism_xz(outline, my0, mt)


def orbit_pts(cx, cz, w, h, tilt_deg, n=60, e=2.6):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n; c, s_ = math.cos(t), math.sin(t)
        x = (w / 2) * math.copysign(abs(c) ** (2 / e), c); z = (h / 2) * math.copysign(abs(s_) ** (2 / e), s_)
        if z > 0:
            z *= 1.0 + 0.10 * (x / (w / 2)) * (1 if cx > 0 else -1)   # higher towards the nose: slight inward lift
        r = math.radians(tilt_deg)
        pts.append((cx + x * math.cos(r) - z * math.sin(r), cz + x * math.sin(r) + z * math.cos(r)))
    return pts


for sx in (-1, 1):
    op = orbit_pts(sx * EX, EZ, ow, oh, -7 * sx)          # outer corner lower
    mask = D(mask, prism_xz(op, my0 - 1, mt + 2))
    # bevel ring: shallow chamfer step around each orbit for depth (stays inside the mask plane)
    mask = D(mask, D(prism_xz(orbit_pts(sx * EX, EZ, ow + 6, oh + 6, -7 * sx), my0 - 1, 1.6), prism_xz(op, my0 - 2, 4)))
nasal = [(0, 99), (5, 95), (9, 86), (8, 77), (3, 73), (0, 75), (-3, 73), (-8, 77), (-9, 86), (-5, 95)]
mask = D(mask, prism_xz(nasal, my0 - 4, mt + 8))
for sx in (-1, 1):
    mask = D(mask, cyl(1.7, (sx * 74.5, my0 - 6, 125.5), (sx * 74.5, my1 + 1, 125.5)))
    mask = D(mask, prism_xz(ellipse_pts((sx * 47, 88.5), 7.5, 3.2, 28, sx * 0.25), my0 - 1, mt + 2))   # cheek lightening slot
    mask = D(mask, prism_xz(ellipse_pts((sx * 21, 76), 5.0, 3.6, 24, -sx * 0.5), my0 - 1, mt + 2))    # paranasal window
P29 = part("P29", "face_mask", mask, "frame_steel")

# --- P30/P31 zygoma bars (XY plane, z 86..94) mask -> lower wall
zyg = prism_xy([(-52, -60), (-64, -60), (-74, -14), (-68, -12), (-60, -40)], 86, 8)
zyg = D(zyg, lwL, mask)
P30 = part("P30", "zygoma_L", zyg, "frame_dark")
P31 = part("P31", "zygoma_R", mirror_x(zyg), "frame_dark")


# --- dental arch helpers
def arch_pts(R, c_y, a_deg, end_xy, n=24, side=+1):
    pts = [(R * math.sin(math.radians(a)), c_y - R * math.cos(math.radians(a))) for a in
           [-a_deg + 2 * a_deg * i / n for i in range(n + 1)]]
    return pts


def band_poly(R, w, c_y, a_deg, ends):
    """U band: front arc radius R (+-w/2) then straight to ends (+-x, y)"""
    o = [(-ends[0] - w / 2, ends[1])] + arch_pts(R + w / 2, c_y, a_deg, None) + [(ends[0] + w / 2, ends[1])]
    i = [(ends[0] - w / 2, ends[1])] + list(reversed(arch_pts(R - w / 2, c_y, a_deg, None))) + [(-ends[0] + w / 2, ends[1])]
    return o + i


# --- P32 maxilla arch (z 56..64) + struts to walls + upper molar blocks
mx = prism_xy(band_poly(37, 10, -24, 62, (46, -8)), 56, 8)
for sx in (-1, 1):
    mx = U(mx, box((sx * 57.5, -16, 60), (23, 6, 5)))
    mx = U(mx, box((sx * 39.0, -26, 56 - 4.5 / 2), (8, 8, 4.5)))   # upper molar block z 51.5..56
mx = U(mx, box((0, -59.0, 60), (30, 4, 8)))  # nasal floor joint to mask bottom
for a in [-50, -38, -26, 26, 38, 50]:
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    mx = D(mx, box((0, 0, 0), (2.4, 8, 4.4)).rotate(V(0, 0, 0), V(0, 0, 1), -a).translate(V(42.0 * sa, -24 - 42.0 * ca, 60)))
mx = D(mx, lwL, mirror_x(lwL), mask)
P32 = part("P32", "maxilla_arch", mx, "frame_steel")

# --- P33 mandible: U body (z chin..36) + rami at |x| 59.5..64.5 + gonial bridges + lower molar pads
cz = P["chin_z"]
mb = prism_xy(band_poly(36, 10, -24, 60, (53, 0)), cz, 36 - cz)
# chin taper: chamfer-like cut under the front
mb = D(mb, prism_yz([(-80, cz - 1), (-56, cz - 1), (-80, cz + 14)], -70, 140))
# anatomical lower edge: only the chin is deep; behind it the body rises to z26 so the jaw clears the
# base plate and the R4 neck flange through 0..25 deg (found by the motion sweep, see checks/R5a)
mb = D(mb, prism_yz([(-49.5, cz - 1), (-48, 14), (-46.5, 22), (-45, 26.2), (40, 26.2), (40, cz - 1)], -70, 140))
rx0, rx1 = P["ramus_x"]
ram = [(-6, 12), (-6, 38), (3, 50), (5, 62), (13, 67), (21, 62), (22, 50), (16, 28), (8, 12)]
for sx in (-1, 1):
    x0 = rx0 if sx > 0 else -rx1
    r_ = prism_yz(ram, x0, rx1 - rx0)
    r_ = U(r_, cyl(9.0, (x0, jy, jz), (x0 + rx1 - rx0, jy, jz)))
    r_ = D(r_, cyl(1.7, (x0 - 1, jy, jz), (x0 + 7, jy, jz)), prism_yz(ellipse_pts((4, 34), 4.5, 9, 24, 0.5), x0 - 1, 7))
    mb = U(mb, r_)
    mb = U(mb, box((sx * 56, -1, 31.2), (17, 10, 9.6)))
    mb = U(mb, box((sx * 39.5, -26, 36 + (56 - 4.5 - P["molar_gap"] - 36) / 2), (8, 8, 56 - 4.5 - P["molar_gap"] - 36)))
for a in [-45, -33, -22.5, -11.5, 0, 11.5, 22.5, 33, 45]:
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    cx, cy = 41.0 * sa, -24 - 41.0 * ca
    slot = box((0, 0, 0), (2.6, 9, 13)).rotate(V(0, 0, 0), V(0, 0, 1), -a).translate(V(cx, cy, 22.5))
    mb = D(mb, slot)
# horn screw holes on left ramus (OEM horn, radius 8 slots)
for dy, dz in [(8, 0), (-8, 0)]:
    mb = D(mb, cyl(1.15, (-rx1 - 1, jy + dy, jz + dz), (-rx0 + 1, jy + dy, jz + dz)))
P33 = part("P33", "mandible", mb, "frame_steel")


# --- P42/P43 teeth rows (individual tapered teeth on a thin carrier strip), ivory
def tooth(w, d, h, up=True):
    s = cq.Workplane("XY").rect(w, d).extrude(h, taper=7).edges(">Z").chamfer(0.6).val()
    return s if up else s.mirror("XY")


def teeth_row(R, c_y, angles, z_base, up, hs):
    row = None
    for a, h in zip(angles, hs):
        w = 6.0 if abs(a) < 20 else 5.4
        t = tooth(w, 4.6, h, up).rotate(V(0, 0, 0), V(0, 0, 1), -a)
        x, y = R * math.sin(math.radians(a)), c_y - R * math.cos(math.radians(a))
        t = t.translate(V(x, y, z_base))
        row = t if row is None else row.fuse(t)
    return row.clean()


angs = [-50, -39, -28.5, -17.5, -6, 6, 17.5, 28.5, 39, 50]
up_h = [7.6, 8.4, 9.6, 8.6, 9.2, 9.0, 8.8, 9.7, 8.2, 7.8]       # deliberate small irregularity
lo_h = [7.4, 8.0, 8.9, 8.6, 9.0, 9.1, 8.7, 8.8, 8.1, 7.6]
upper = teeth_row(37.6, -24, angs, 56.6, False, up_h)
upper = U(upper, prism_xy(band_poly(37.6, 3, -24, 54, (34, -38)), 56.0, 1.2))
# trim so every upper tip sits >= front gap above lower tips (closed pose)
lower = teeth_row(36.0, -24, angs, 35.4, True, lo_h)
lower = U(lower, prism_xy(band_poly(36.0, 3, -24, 54, (33, -39)), 35.0, 1.0))
low_top = 35.4 + max(lo_h)
upper = D(upper, box((0, -40, low_top + P["teeth_gap_front"] - 25), (200, 120, 50)))
P42 = part("P42", "upper_teeth_row", upper, "teeth")
P43 = part("P43", "lower_teeth_row", lower, "teeth")
P32 = part("P32", "maxilla_arch", D(P32, upper), "frame_steel")           # socket groove for the upper row
P33 = part("P33", "mandible", D(P33, lower), "frame_steel")               # socket groove for the lower row
P23 = part("P23", "upper_cranial_plate_L", D(P23, mask), "frame_steel")
P24 = part("P24", "upper_cranial_plate_R", D(P24, mask), "frame_steel")

# ================================================================ EYES
def globe(xe):
    c = (xe, EY, EZ)
    g = D(sphere(GR, c), sphere(P["globe_cavity_r"], c))
    h = 22.0
    cone = cq.Solid.makeCone(0, h * math.tan(math.radians(P["bottom_cone_half_deg"])), h, V(*c), V(0, 0, -1))
    g = D(g, cone)
    g = D(g, cyl(P["pin_hole_d"] / 2, (xe - 20, EY, EZ), (xe + 20, EY, EZ)))
    g = D(g, cyl(7.1, (xe, EY - GR - 1, EZ), (xe, EY - 13.0, EZ)))              # flat iris recess (rim stays inside the sphere)
    g = D(g, cyl(1.6, (xe, EY - GR - 1, EZ), (xe, EY - 10, EZ)))                 # pupil / LED light path
    c0 = P["C0"]; ball_c = (xe + c0[0], EY + c0[1], EZ + c0[2])
    g = U(g, cyl(2.4, (xe, EY + GR - 1.5, EZ), (xe, EY + GR + 1.0, EZ)),         # rear boss
          cyl(0.8, (xe, EY + GR + 0.5, EZ), ball_c), sphere(P["ball_r"], ball_c))  # M1.6 stud neck + ball
    return g


P34 = part("P34", "eye_globe", globe(-EX), "eye_white", qty=2)
iris = D(cyl(7.0, (-EX, EY - 14.2, EZ), (-EX, EY - 13.0, EZ)), cyl(1.6, (-EX, EY - 20, EZ), (-EX, EY, EZ)))
P35 = part("P35", "iris_insert", iris, "iris", qty=2)

# --- P37 cross block (U-joint): turns on the vertical post screw (yaw), carries the pitch pin
b = P["block"]
blk = box((-EX, EY, EZ), (b, b, b))
blk = D(blk, cyl(1.1, (-EX, EY, EZ - 6), (-EX, EY, EZ - 1.2)), cyl(1.1, (-EX - 6, EY, EZ), (-EX + 6, EY, EZ)))
P37 = part("P37", "eye_cross_block", blk, "frame_dark", qty=2)

# --- P36 eye deck: plate under the eyes + 2 vertical posts + 4 lid prongs, bolts to wall fronts
ez0, ez1 = P["eye_deck_z"]
ed = prism_xy([(-68, -52), (68, -52), (68, -6), (-68, -6)], ez0, ez1 - ez0)
ed = D(ed, prism_xy(rrect_pts((0, -30), 14, 30, 5), ez0 - 1, 6))
for sx in (-1, 1):
    ed = D(ed, prism_xy(rrect_pts((sx * 58, -40), 10, 14, 4), ez0 - 1, 6))
for sx in (-1, 1):
    xe = sx * EX
    post = cyl(P["post_r"], (xe, EY, ez1 - 0.5), (xe, EY, EZ - b / 2 - 0.4))
    post = D(post, cyl(0.85, (xe, EY, EZ - 20), (xe, EY, EZ)))                   # M2 tapping hole for the yaw screw
    ed = U(ed, post, cyl(5.5, (xe, EY, ez1 - 0.5), (xe, EY, ez1 + 3)))            # fillet collar
    for side in (-1, 1):
        px0, px1 = P["prong_x"]
        x0 = xe + px0 if side > 0 else xe - px1
        pr = box((x0 + (px1 - px0) / 2, EY, (ez1 - 0.5 + EZ + 4.5) / 2), (px1 - px0, 8, EZ + 4.5 - ez1 + 0.5))
        pr = D(pr, cyl(1.1, (x0 - 1, EY, EZ), (x0 + 5, EY, EZ)))
        ed = U(ed, pr)
P36 = part("P36", "eye_deck", ed, "frame_dark")

# --- P38 control bar: two ball sockets behind the globes + centre tab carrying the yaw and pitch balls
c0 = P["C0"]; by_, bz_ = EY + c0[1], EZ + c0[2]
bar = box((0, by_, bz_ + 3.4), (2 * EX - 5.0, 4.0, 3.2))
for sx in (-1, 1):
    c = V(sx * EX, by_, bz_)
    sock = D(sphere(3.2, tuple(c)), sphere(P["ball_r"] + 0.15, tuple(c)),
             cq.Solid.makeCone(0, 8 * math.tan(math.radians(60)), 8, c, V(0, -1, 0)))     # wraps >180 deg: ball retained
    bar = U(bar, sock, box((sx * (EX - 3.4), by_, bz_ + 3.0), (2.4, 4.0, 2.6)))
yb, pb = P["yaw_ball"], P["pitch_ball"]
bar = U(bar, box((0, by_, (bz_ + 1.0 + pb[2]) / 2), (5, 4, pb[2] - bz_ - 1.0)))
bar = U(bar, cyl(1.0, (0, yb[1], yb[2]), yb), sphere(1.8, yb), sphere(1.8, pb))
P38 = part("P38", "eye_control_bar", bar, "frame_steel")


# --- P39/P40 upper lids (shell + side arms + lever on the outer arm)
def lid(xe, outer_sign):
    c = (xe, EY, EZ)
    sh = D(sphere(P["lid_r_out"], c), sphere(P["lid_r_in"], c))
    keep_front = box((xe, EY - 30 + 2, EZ), (60, 60, 60))                     # y_rel < 2
    top = box((xe, EY, EZ + 7.9 + 30), (60, 60, 60))                           # z_rel > 7.9
    sides = D(box((xe, EY, EZ - 6 + 30), (60, 60, 60)), box((xe, EY, EZ), (28, 61, 61)))  # |x_rel|>14, z_rel>-6
    sh = sh.intersect(keep_front).intersect(top.fuse(sides)).clean()
    ax0, ax1 = P["lid_arm_x"]
    ly, lz = P["lid_lever"]
    for side in (-1, 1):
        x0 = xe + ax0 if side > 0 else xe - ax1
        arm_pts = [(EY - 6, EZ - 4), (EY - 17.5, EZ + 4), (EY - 12, EZ + 13.5), (EY - 2, EZ + 7.5), (EY + 3.5, EZ + 3.5), (EY + 3.5, EZ - 4)]
        if side == outer_sign:
            arm_pts = [(EY - 6, EZ - 4), (EY - 17.5, EZ + 4), (EY - 12, EZ + 13.5), (EY - 2, EZ + 7.5),
                       (EY + 4, EZ + 3.5), (EY + ly + 3.0, EZ + lz + 3.0), (EY + ly + 3.0, EZ + lz - 3.0), (EY + 2, EZ - 5.5)]
        a = prism_yz(arm_pts, x0, ax1 - ax0)
        a = U(a, cyl(4.0, (x0, EY, EZ), (x0 + ax1 - ax0, EY, EZ)))
        a = D(a, cyl(1.1, (x0 - 1, EY, EZ), (x0 + 3, EY, EZ)))
        if side == outer_sign:
            a = D(a, cyl(1.1, (x0 - 1, EY + ly, EZ + lz), (x0 + 3, EY + ly, EZ + lz)))
        sh = sh.fuse(a)
    sh = D(sh, cyl(1.1, (xe - 25, EY, EZ), (xe + 25, EY, EZ)), cyl(2.2, (xe - 17.6, EY, EZ), (xe + 17.6, EY, EZ)))
    return sh.clean()


P39 = part("P39", "upper_lid_L", lid(-EX, -1), "lid")
P40 = part("P40", "upper_lid_R", lid(EX, +1), "lid")

# --- P41 mechanism deck (z 154..158) with servo mounts
dz0, dz1 = P["deck_z"]; dy0, dy1 = P["deck_y"]
deck = prism_xy([(-74, dy0), (74, dy0), (74, dy1), (-74, dy1)], dz0, dz1 - dz0)
ys = P["yaw_S"]
deck = D(deck, box((ys[0], ys[1] + 6, 156), (13.4, 24.0, 10)))                # yaw servo body pass-through
deck = D(deck, box((0, P["pitch_ball"][1] + 0.75, 156), (36, 15, 10)))      # slot: tab + pitch rod sweep incl. +-28/-21 deg overtravel
for sx in (-1, 1):
    deck = D(deck, prism_xy(rrect_pts((sx * 58, 0), 14, 22, 5), dz0 - 1, 6))
psv = P["pitch_S"]
ptip = psv[0] - 1.0                                                          # pitch spline tip (shaft +X), horn beyond at x=psv[0]
pbx = ptip - 10.0 - 1.2                                                     # far side of the tabs: away from the swinging rod
pbr = box((pbx, (dy0 + 6 + dy1 - 1) / 2, (dz1 + psv[2] + 10) / 2), (2.4, dy1 - dy0 - 7, psv[2] + 10 - dz1))
pbr = D(pbr, box((pbx, psv[1] + 6, psv[2]), (4, 23.6, 12.8)))
deck = U(deck, pbr)
ls = P["lid_S"]
for sx in (-1, 1):
    xb = sx * (EX + ls[0] - 1.0 - 6.8)                                       # tip-side face of the tabs
    ytop, ybot, ztop = ls[1] + 6 + 16.6, ls[1] + 6 - 16.6, ls[2] + 6.6      # spans both tab screws; stays under the mid arch
    brk = box((xb, (ytop + ybot) / 2, (dz1 + ztop) / 2), (2.4, ytop - ybot, ztop - dz1))
    brk = D(brk, box((xb, ls[1] + 6, ls[2]), (4, 23.6, 12.8)))
    deck = U(deck, brk)
deck = D(deck, P26)                                                         # notch where the mid arch passes
P41 = part("P41", "mechanism_deck", deck, "frame_dark")

# --- jaw servo cradle (P44): frame on tip side of tabs + pillar to base plate
tipx = P["jaw_tip_x"]
cr = box((tipx + 6.25, 18.5, jz), (2.5, 35, 20))
cr = D(cr, box((tipx + 6.25, 18.5, jz), (4, 23.8, 13.2)))
cr = U(cr, box((-48, 34, (6 + jz - 10) / 2 + 0.0), (8, 8, jz - 10 - 6 + 0.0)))
cr = U(cr, box((-49.5, 30.0, jz - 9.5), (5, 9, 3)))
P44 = part("P44", "jaw_servo_cradle", cr, "frame_dark")

# ================================================================ R4 neck (unchanged)
r4neck = {}
for pid, fn in [("P03", "P03_skeletal_neck_tenon.step"), ("P01", "P01_torso_spine_socket.step")]:
    r4neck[pid] = cq.importers.importStep(str(R4P / fn)).val()

# ================================================================ PLACEMENT (neutral pose)
for pid in ["P20", "P21", "P22", "P23", "P24", "P25", "P26", "P27", "P28", "P29", "P30", "P31", "P32", "P41", "P44", "P36"]:
    place(pid, pid, parts[pid]["shape"], "fixed", parts[pid]["mat"])
place("P42", "P42", parts["P42"]["shape"], "fixed", "teeth")
place("P33", "P33", parts["P33"]["shape"], "jaw", "frame_steel")
place("P43", "P43", parts["P43"]["shape"], "jaw", "teeth")
for pid, s in r4neck.items():
    place(pid + "_R4", pid, s, "fixed", "frame_dark")
for sx, tag in ((-1, "L"), (1, "R")):
    dx = 2 * EX if sx > 0 else 0.0
    place(f"P34_eye_{tag}", "P34", parts["P34"]["shape"].translate(V(dx, 0, 0)), f"eye_{tag}", "eye_white")
    place(f"P35_iris_{tag}", "P35", parts["P35"]["shape"].translate(V(dx, 0, 0)), f"eye_{tag}", "iris")
    place(f"P37_block_{tag}", "P37", parts["P37"]["shape"].translate(V(dx, 0, 0)), f"block_{tag}", "frame_dark")
place("P39_lid_L", "P39", parts["P39"]["shape"], "lid_L", "lid")
place("P40_lid_R", "P40", parts["P40"]["shape"], "lid_R", "lid")
place("P38_bar", "P38", parts["P38"]["shape"], "bar", "frame_steel")

# purchased / hardware placeholders --------------------------------------------
hw = []


def H(name, shape, group, mat):
    hw.append(dict(name=name, pid="PURCHASED", shape=shape, group=group, mat=mat))


for sx, tag in ((-1, "L"), (1, "R")):
    xe = sx * EX
    H(f"dowel_yaw_2mm_{tag}", cyl(1.0, (xe, EY, EZ - 12.0), (xe, EY, EZ - 1.4)), "fixed", "steel")
    H(f"pin_pitch_M2_{tag}", cyl(1.0, (xe - 16.6, EY, EZ), (xe + 16.6, EY, EZ)), f"block_{tag}", "steel")
    for side in (-1, 1):
        x0 = xe + side * P["lid_arm_x"][0]
        x1 = xe + side * P["prong_x"][1]
        H(f"pin_lid_M2_{tag}{'o' if side == sx else 'i'}", cyl(1.0, (x0, EY, EZ), (x1, EY, EZ)), "fixed", "steel")
for sx, tag in ((-1, "L"), (1, "R")):
    H(f"LED_3mm_{tag}", cyl(1.5, (sx * EX, EY - 12.0, EZ), (sx * EX, EY - 8.0, EZ)), f"eye_{tag}", "led")
# jaw pivots: left outboard pin + right idler pin through walls into rami
H("pin_jaw_M3_L", cyl(1.5, (-75, jy, jz), (-61.5, jy, jz)), "fixed", "steel")
H("pin_jaw_M3_R", cyl(1.5, (61.5, jy, jz), (75, jy, jz)), "fixed", "steel")
# servos
SERVOS = {}
SERVOS["MG90S_jaw"] = dict(tip=(tipx, jy, jz), z=(-1, 0, 0), y=(0, 1, 0), group="fixed")
SERVOS["MG90S_eye_yaw"] = dict(tip=(ys[0], ys[1], ys[2] + 1.0), z=(0, 0, -1), y=(0, 1, 0), group="fixed")
SERVOS["MG90S_eye_pitch"] = dict(tip=(psv[0] - 1.0, psv[1], psv[2]), z=(1, 0, 0), y=(0, 1, 0), group="fixed")
for sx, tag in ((-1, "L"), (1, "R")):
    SERVOS[f"SG90_lid_{tag}"] = dict(tip=(sx * (EX + ls[0] - 1.0), ls[1], ls[2]), z=(sx, 0, 0), y=(0, 1, 0), group="fixed")
for n, sv in SERVOS.items():
    H(n, servo_at(sv["tip"], sv["z"], sv["y"]), "fixed", "servo")
# jaw OEM horn (between spline tip and ramus), moves with jaw
H("OEM_horn_jaw", horn_arm((tipx - 1.0, jy, jz), (tipx - 1.0, jy + 9, jz), (1, 0, 0)), "jaw", "horn")
# yaw / pitch / lid horns and rods are posed by the kinematic solver (scene file)
scene_static = dict(parameters=P)

