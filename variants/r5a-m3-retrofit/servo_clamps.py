"""Single-screw tab clamp candidates for the five R5a servo locations."""

from dataclasses import dataclass

import cadquery as cq

from build_structural import cylinder
from check_structural import bounding_boxes_overlap


def box(x, y, z, dx, dy, dz):
    return cq.Workplane("XY").box(dx, dy, dz).val().translate((x, y, z))


@dataclass(frozen=True)
class Clamp:
    support: cq.Shape
    clip: cq.Shape
    screw: cq.Shape
    nut: cq.Shape
    clip_print: cq.Shape
    group: str
    length: int


def frame(servo):
    z = cq.Vector(*servo["z"])
    y = cq.Vector(*servo["y"])
    return cq.Location(cq.Plane(cq.Vector(*servo["tip"]), y.cross(z), z))


def candidate(servo, support, tab_y, side, bolt_x, backing, screw_length, longitudinal=False):
    """Build the clamp around the 2 mm nominal flange without using its hole.

    Backing determines which side of the flange the original bracket seats on.
    The clip heel contacts the new boss and the nose contacts the servo flange.
    """
    loc = frame(servo)
    if longitudinal:
        # Turn the front yaw clamp so its extra hardware sits ahead of
        # the servo and away from the inner eyelid supports.
        loc = loc * cq.Location(cq.Vector(0, tab_y, 0), cq.Vector(0, 0, 1), 90)
        tab_y = 0
    mount_side = -1 if backing < -9 else 1
    clip_side = -mount_side
    tab_face = -9 + clip_side
    bolt_x *= side
    # Build the pad across the outer portion of the original bracket.
    support_face = -9 + mount_side
    support_far = backing + mount_side * 3
    inner = 0.5 if longitudinal else 3.5
    outer = abs(bolt_x) + 3.5
    pad = box(side * (outer + inner) / 2, tab_y,
              (support_face + support_far) / 2,
              outer - inner, 5, abs(support_far - support_face))
    pad = pad.moved(loc)
    widened = support.fuse(pad).clean()
    if len(widened.Solids()) != 1:
        return None

    clip_thickness = 2.4
    nose = 0.9 if longitudinal else 2.2
    rim = abs(bolt_x) + 3
    clip = box(side * (rim + nose) / 2, tab_y, tab_face + clip_side * clip_thickness / 2,
               rim - nose, 5, clip_thickness)
    heel = box(bolt_x + side * 2.2, tab_y, -9 + clip_side * 0.5,
               2.0, 5, 3.0)
    clip = clip.fuse(heel).clean()
    bore = cylinder(1.7, (bolt_x, tab_y, -22), (0, 0, 1), 32)
    clip = clip.cut(bore).clean()
    widened = widened.cut(bore.moved(loc)).clean()
    if len(clip.Solids()) != 1 or len(widened.Solids()) != 1:
        return None

    z_head = tab_face + clip_side * clip_thickness
    shank = cylinder(1.5, (bolt_x, tab_y, z_head), (0, 0, mount_side), screw_length)
    head = cylinder(2.75, (bolt_x, tab_y, z_head), (0, 0, clip_side), 3)
    nut_start = support_far if mount_side > 0 else support_far - 2.4
    nut = (cq.Workplane("XY", origin=(bolt_x, tab_y, nut_start))
           .polygon(6, 5.5, circumscribed=True).extrude(2.4).val())
    clip_print = clip.translate((-bolt_x, -tab_y, 0))
    if abs(support_far - z_head) + 2.9 > screw_length:
        return None
    return Clamp(widened, clip.moved(loc), shank.fuse(head).moved(loc), nut.moved(loc),
                 clip_print, servo["group"], screw_length)


def overlaps(shape, others):
    box = shape.BoundingBox()
    return [(name, volume) for name, other in others
            if bounding_boxes_overlap(box, other.BoundingBox())
            and (volume := shape.intersect(other).Volume()) > 0.05]
