#!/usr/bin/env python3
"""Mathematical watch dial displacement map generator (CLI + Tkinter GUI).

Dependencies: numpy, Pillow; Tkinter is part of most desktop Python distributions.
Height is stored as pixel brightness, never as simulated lighting.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageTk

__version__ = '1.1.1'

PATTERNS = {
    'hobnail': 'Clous de Paris / Hobnail',
    'barleycorn': 'Barleycorn (stylized guilloché)',
    'sunburst': 'Sunburst (radial grooves)',
    'basketweave': 'Basket Weave',
    'tapisserie': 'Tapisserie (square relief)',
    'fishscales': 'Fish Scales',
    'flinque': 'Flinqué (radiating waves)',
    'wave': 'Wave (parallel sinusoidal ridges)',
    'annularwave': 'Annular Wave (concentric ripples)',
    'graindorge': 'Grain d’Orge (interlaced grains)',
    'flamme': 'Flamme (radial flames)',
    'panier': 'Panier (curved woven ribbons)',
    'escargot': 'Escargot (spiral grooves)',
    'moire': 'Moiré (interference waves)',
    'chevron': 'Chevron / Herringbone',
    'rosette': 'Rosette (radial petals)',
    'sectorrings': 'Sector Rings (segmented annuli)',
    'honeycomb': 'Honeycomb (hexagonal cells)',
    'perlage': 'Perlage (circular graining)',
    'diamondlattice': 'Diamond Lattice',
    'isometriccubes': 'Isometric Cubes',
    'fanscallop': 'Fan / Scallop',
    'asanoha': 'Asanoha (hemp leaf geometry)',
    'brick': 'Brick / Running Bond',
    'dimples': 'Dimples (golf ball texture)',

}

ENUM_FIELDS = {
    'asanoha_style': ('faceted', 'rounded', 'engraved'),
    'fishscales_style': ('rounded', 'faceted', 'engraved'),
    'brick_style': ('faceted', 'engraved', 'rounded'),
}


def _hex_cell_coordinates(u, v):
    """Closest pointy-hex centers on a triangular lattice (pitch = X spacing).

    Returns physical-size-independent local coordinates in units of pitch.
    The mesh is regular, with cell circumradius = pitch / sqrt(3).
    """
    xx, yy = np.broadcast_arrays(u, v)
    best = np.full(xx.shape, np.inf, dtype=np.float32)
    local_x = np.zeros(xx.shape, dtype=np.float32)
    local_y = np.zeros(xx.shape, dtype=np.float32)
    row0 = np.floor(yy / (np.sqrt(3) / 2) + .5).astype(np.int32)
    for dr in (-1, 0, 1):
        row = row0 + dr
        shift = .5 * np.mod(row, 2)
        col0 = np.floor(xx - shift + .5)
        for dc in (-1, 0, 1):
            cx = col0 + dc + shift
            cy = row * (np.sqrt(3) / 2)
            dx, dy = xx - cx, yy - cy
            dist2 = dx * dx + dy * dy
            mask = dist2 < best
            best = np.where(mask, dist2, best)
            local_x = np.where(mask, dx, local_x)
            local_y = np.where(mask, dy, local_y)
    return local_x, local_y


def _segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dimple_height(u, v, pitch_mm, diameter_mm):
    """Round recessed bowls on staggered rows; flat land between dimples.

    A shallow spherical-cap profile is normalized from 0 at the bowl center
    to 1 at its rim. The target depth sets the vertical relief span separately.
    """
    xx, yy = _hex_cell_coordinates(u, v)
    radius = diameter_mm / (2 * pitch_mm)
    radial = np.clip(np.hypot(xx, yy) / radius, 0, 1)
    return (1 - np.sqrt(1 - .64 * radial**2)) / .4


def _hex_vertices():
    radius = 1 / math.sqrt(3)
    angles = np.pi / 2 + np.arange(6) * np.pi / 3
    return np.stack((radius * np.cos(angles), radius * np.sin(angles)), axis=1)


def _asanoha_height(u, v, pitch_mm, line_width_mm, style='faceted'):
    """Asanoha relief styles.

    engraved: flat surface with recessed hemp-leaf grooves.
    faceted: sculpted wedge-like facets between grooves.
    rounded: softer domed relief between grooves.
    """
    xx, yy = _hex_cell_coordinates(u, v)
    vertices = _hex_vertices()
    radius = 1 / math.sqrt(3)

    distance = np.full(xx.shape, np.inf, dtype=np.float32)
    for i in range(6):
        a = vertices[i]
        b = vertices[(i + 1) % 6]
        segments = ((0, 0, a[0], a[1]),
                    (a[0] * 0.38, a[1] * 0.38, b[0] * 0.78, b[1] * 0.78),
                    (a[0] * 0.78, a[1] * 0.78, b[0] * 0.38, b[1] * 0.38),
                    (a[0], a[1], b[0], b[1]))
        for x1, y1, x2, y2 in segments:
            distance = np.minimum(distance, _segment_distance(xx, yy, x1, y1, x2, y2))

    half_width = line_width_mm / (2 * pitch_mm)
    groove_mask = np.clip((distance - half_width * 0.45) / max(half_width * 0.95, 1e-6), 0, 1)

    if style == 'engraved':
        return groove_mask

    theta = np.mod(np.arctan2(yy, xx) - np.pi / 2, 2 * np.pi)
    wedge_angle = np.pi / 3
    local_ang = np.abs(np.mod(theta + wedge_angle / 2, wedge_angle) - wedge_angle / 2) / (wedge_angle / 2)
    r = np.sqrt(xx * xx + yy * yy)
    rnorm = np.clip(r / radius, 0, 1)

    g1 = 1 - 2 * np.abs(np.mod(xx + 0.5, 1.0) - 0.5)
    g2 = 1 - 2 * np.abs(np.mod(0.5 * xx + 0.8660254 * yy + 0.5, 1.0) - 0.5)
    g3 = 1 - 2 * np.abs(np.mod(-0.5 * xx + 0.8660254 * yy + 0.5, 1.0) - 0.5)
    support = np.clip((g1 + g2 + g3) / 3.0, 0, 1)

    if style == 'faceted':
        radial_peak = np.clip(1 - np.abs(rnorm - 0.64) / 0.34, 0, 1)
        wedge_profile = np.clip(1 - local_ang**1.15, 0, 1)
        petal = wedge_profile * radial_peak
        relief = np.clip(0.18 + 0.62 * support + 0.42 * petal, 0, 1)
    elif style == 'rounded':
        petal = np.exp(-((rnorm - 0.62) / 0.23) ** 2) * np.clip(np.cos(local_ang * np.pi / 2), 0, 1) ** 1.8
        support_round = np.sqrt(np.clip(support, 0, 1))
        relief = np.clip(0.10 + 0.52 * support_round + 0.55 * petal, 0, 1)
    else:
        raise ValueError("Asanoha style must be one of: faceted, rounded, engraved")

    h = np.clip(groove_mask * relief, 0, 1)
    peak = np.max(h)
    if peak > 1e-6:
        h = h / peak
    return h


def _cube_height(u, v, pitch_mm, cube_gap_mm, cube_step_fraction):
    """Rhombille tiling: three flat rhombi per hexagon, at real Z terraces."""
    xx, yy = _hex_cell_coordinates(u, v)
    vertices = _hex_vertices()
    # Each face occupies a 120-degree sector; its edges run from the
    # cell center to alternating vertices. These are 3 true rhombi.
    theta = np.mod(np.arctan2(yy, xx) - np.pi / 2, 2 * np.pi)
    sector = np.floor(theta / (2 * np.pi / 3)).astype(np.int32) % 3
    heights = np.array([1.0, 1.0 - cube_step_fraction, 1.0 - 2 * cube_step_fraction], dtype=np.float32)
    face = heights[sector]
    distance = np.full(xx.shape, np.inf, dtype=np.float32)
    for i in (0, 2, 4):
        vx, vy = vertices[i]
        distance = np.minimum(distance, _segment_distance(xx, yy, 0, 0, vx, vy))
    for i in range(6):
        a, b = vertices[i], vertices[(i + 1) % 6]
        distance = np.minimum(distance, _segment_distance(xx, yy, a[0], a[1], b[0], b[1]))
    half_gap = cube_gap_mm / (2 * pitch_mm)
    groove_transition = np.clip((distance - half_gap * .6) / max(half_gap * .8, 1e-6), 0, 1)
    return face * groove_transition



def _woven_height(u, v, base):
    """Alternating ribbon bodies with smooth, shared boundary heights."""
    fu, fv = np.mod(u, 1.), np.mod(v, 1.)
    def end_taper(t):
        t = np.clip(np.minimum(t, 1-t)/.15, 0, 1)
        return t*t*(3-2*t)
    vertical = np.sin(np.pi*fu)**4 * end_taper(fv)
    horizontal = end_taper(fu) * np.sin(np.pi*fv)**4
    over = (np.floor(u).astype(np.int32)+np.floor(v).astype(np.int32)) % 2 == 0
    return base + (1-base)*np.where(over, vertical, horizontal)


def _scallop_coordinates(u, v):
    """Cells bounded by consecutive staggered arcs, with no horizontal row reset."""
    row = np.floor(v).astype(np.int32)
    def local_x(r):
        return np.mod(u + .5 * (r % 2), 1.) - .5
    x = local_x(row)
    arc = lambda xx: 1 - np.sqrt(.95**2 - xx**2)
    row = row - ((v - row) < arc(x))
    x = local_x(row)
    lower = row + arc(x)
    upper = row + 1 + arc(local_x(row + 1))
    t = np.clip((v - lower) / (upper - lower), 0, 1)
    # Vertical arc distance converted to approximate normal distance.
    slope = x / np.sqrt(.95**2 - x*x)
    next_x = local_x(row + 1)
    next_slope = next_x / np.sqrt(.95**2 - next_x*next_x)
    distance = np.minimum((v-lower)/np.sqrt(1+slope*slope),
                          (upper-v)/np.sqrt(1+next_slope*next_slope))
    return x, t, distance


def _fishscales_height(u, v, style='rounded', softness=0.0):
    """Continuous staggered arc cells; all styles meet at recessed boundaries."""
    x, t, distance = _scallop_coordinates(u, v)
    width = .018 + .08 * softness
    groove = np.clip((distance - width*.55) / (width*.95), 0, 1)
    side = np.clip(1 - 2*np.abs(x), 0, 1)
    if style == 'engraved':
        return groove
    if style == 'faceted':
        body = np.minimum(side, 1 - np.abs(2*t-1))
    elif style == 'rounded':
        body = np.sin(np.pi*t) * np.cos(np.pi*x)**2
    else:
        raise ValueError('Invalid fish scales style')
    return groove * (.18 + .82 * body)


def _perlage_height(u, v, pitch_mm, ring_pitch_mm, overlap):
    """Overlapping circular graining strokes with feathered rims.

    Each later stroke replaces the preceding shallow ring texture locally.
    Cosine feathering avoids hard depth jumps at circular stroke boundaries.
    """
    radius = .5 / (1-overlap)
    row0 = np.floor(v).astype(np.int32)
    h = np.ones(np.broadcast_shapes(u.shape, v.shape), dtype=np.float32)
    for dr in (-2, -1, 0, 1, 2):
        row = row0 + dr
        col0 = np.floor(u - .5*(row % 2)).astype(np.int32)
        for dc in (-2, -1, 0, 1, 2):
            cx = col0 + dc + .5*(row % 2)
            r = np.hypot(u-cx, v-row)
            blend = np.clip((radius-r)/(radius*.18), 0, 1)
            blend = .5 - .5*np.cos(np.pi*blend)
            rings = .5 + .5*np.cos(2*np.pi*r*pitch_mm/ring_pitch_mm)
            stroke = .78 + .18*rings  # shallow circular graining, not deep bowls
            h = h*(1-blend) + stroke*blend
    return h


def _brick_height(u_mm, v_mm, width_mm, height_mm, joint_mm, bevel_mm, stagger, style):
    """Repeatable running-bond rectangular displacement geometry, no illumination.

    u_mm/v_mm are physically rotated coordinates. 50% offset means successive
    rows alternate by half a brick. Joint thickness is shared between bricks.
    """
    row = np.floor(v_mm / height_mm).astype(np.int64)
    # Alternating stagger; a full cycle every two courses.
    shift = (row % 2) * stagger * width_mm
    local_x = np.mod(u_mm - shift, width_mm)
    local_y = np.mod(v_mm, height_mm)
    edge_x = np.minimum(local_x, width_mm - local_x)
    edge_y = np.minimum(local_y, height_mm - local_y)
    # Distance from closest edge, in real physical millimeters.
    edge = np.minimum(edge_x, edge_y)
    d = edge - joint_mm / 2
    if style == 'engraved':
        return (d >= 0).astype(np.float32)
    if style == 'faceted':
        if bevel_mm == 0:
            return (d >= 0).astype(np.float32)
        return np.clip(d / bevel_mm, 0, 1).astype(np.float32)
    if style == 'rounded':
        # Smoothly curved pillowed interior: no flat plateau except at the apex.
        rx = np.clip((edge_x - joint_mm / 2) / ((width_mm - joint_mm) / 2), 0, 1)
        ry = np.clip((edge_y - joint_mm / 2) / ((height_mm - joint_mm) / 2), 0, 1)
        return np.clip(np.sin(np.pi * rx / 2) * np.sin(np.pi * ry / 2), 0, 1).astype(np.float32)
    raise ValueError('Unknown brick style')


PATTERN_PITCH_DEFAULTS = {'hobnail': 1.0}


def default_pitch(pattern):
    return PATTERN_PITCH_DEFAULTS.get(pattern, .75)


def render(pattern='hobnail', size_mm=28.5, pixels=2048, pitch_mm=None,
           depth_mm=0.15, rotation=0.0, phase=0.0, softness=0.0,
           invert=False, circular=False, background=0.0, grooves=96,
           groove_width_mm=0.20, bevel_width_mm=0.08, top_width_mm=0.0, wave_meander_mm=0.0,
           ridge_height_fraction=1.0, grain_aspect=2.0, flame_taper=0.5,
           ribbon_curvature=0.35, rosette_harmonics=0.0, amplitude=0.35,
           secondary_pitch_mm=1.2, angle_deg=60.0, segments=12,
           line_width_mm=0.055, cube_gap_mm=0.04, cube_step_fraction=0.28, asanoha_style='faceted', fishscales_style='rounded', brick_width_mm=1.20, brick_height_mm=0.60,
           brick_joint_mm=0.10, brick_bevel_mm=0.08, brick_row_offset=0.50, brick_style='faceted',
           perlage_ring_pitch_mm=0.1, perlage_overlap=0.5, dimple_diameter_mm=0.65):
    """Return uint16 height map and metadata. White = high, black = low.

    depth_mm is intended Z-range metadata, not a promise of laser engraving depth.
    """
    if pattern not in PATTERNS:
        raise ValueError('Unknown pattern: ' + pattern)
    if pitch_mm is None:
        pitch_mm = default_pitch(pattern)
    if not 128 <= pixels <= 8192:
        raise ValueError('pixels must be between 128 and 8192')
    if size_mm <= 0 or pitch_mm <= 0 or depth_mm <= 0:
        raise ValueError('size, pitch and depth must be positive')
    if not 0 <= softness <= 1:
        raise ValueError('softness must be between 0 and 1')
    if secondary_pitch_mm <= 0 or not 0 <= amplitude <= 2 or segments < 2:
        raise ValueError('secondary pitch must be positive, amplitude 0–2, segments >= 2')
    if grooves < 4:
        raise ValueError('grooves must be >= 4')
    if pattern == 'tapisserie':
        if not 0 <= groove_width_mm < pitch_mm:
            raise ValueError('Tapisserie groove width must be >= 0 and less than pitch')
        if bevel_width_mm < 0 or 2 * bevel_width_mm > pitch_mm - groove_width_mm:
            raise ValueError('Bevel width must be >= 0 and <= half the raised square width')
    if not 0 <= top_width_mm < pitch_mm:
        raise ValueError('top width must be >= 0 and smaller than pitch')
    if wave_meander_mm < 0 or not 0 <= ridge_height_fraction <= 1:
        raise ValueError('wave meander must be nonnegative; ridge height fraction must be 0–1')
    if grain_aspect < 1 or not 0 <= flame_taper <= 1 or not 0 <= ribbon_curvature <= 2 or not 0 <= rosette_harmonics <= 1:
        raise ValueError('grain aspect >= 1; flame taper and rosette harmonics 0–1; ribbon curvature 0–2')
    if pattern == 'asanoha' and (line_width_mm <= 0 or line_width_mm >= pitch_mm / 2):
        raise ValueError("Asanoha line width must be > 0 and < pitch / 2")
    if pattern == 'isometriccubes' and (cube_gap_mm <= 0 or cube_gap_mm >= pitch_mm / 2):
        raise ValueError("Cube gap must be > 0 and < pitch / 2")
    if not 0 < cube_step_fraction < .5:
        raise ValueError("Cube step fraction must be > 0 and < 0.5")
    if asanoha_style not in ENUM_FIELDS['asanoha_style']:
        raise ValueError('Asanoha style must be one of: ' + ', '.join(ENUM_FIELDS['asanoha_style']))
    if fishscales_style not in ENUM_FIELDS['fishscales_style']:
        raise ValueError('Fish scales style must be one of: ' + ', '.join(ENUM_FIELDS['fishscales_style']))
    if pattern == 'brick':
        if brick_width_mm <= 0 or brick_height_mm <= 0:
            raise ValueError('Brick width and height must be positive')
        if not 0 <= brick_row_offset <= 1:
            raise ValueError('Brick row offset must be between 0 and 1')
        if brick_joint_mm < 0 or brick_joint_mm >= min(brick_width_mm, brick_height_mm):
            raise ValueError('Brick joint must be nonnegative and smaller than both brick dimensions')
        if brick_bevel_mm < 0 or 2 * brick_bevel_mm > min(brick_width_mm, brick_height_mm) - brick_joint_mm:
            raise ValueError('Brick bevel must fit within the raised brick dimensions')
        if brick_style not in ENUM_FIELDS['brick_style']:
            raise ValueError('Invalid brick style')
    if pattern == 'dimples':
        if not math.isfinite(pitch_mm) or not 0 < dimple_diameter_mm <= pitch_mm:
            raise ValueError('Dimple diameter must be positive and no larger than the pattern pitch')
    if perlage_ring_pitch_mm <= 0 or not 0 <= perlage_overlap <= .5:
        raise ValueError('Perlage ring pitch must be positive; overlap must be 0–0.5')
    # Pixel-center coordinates; no illumination, only geometry.
    coord = (np.arange(pixels, dtype=np.float32) + 0.5) * (size_mm / pixels) - size_mm / 2
    x = coord[None, :]
    y = coord[:, None]
    ang = math.radians(rotation)
    u = (x * math.cos(ang) + y * math.sin(ang)) / pitch_mm
    v = (-x * math.sin(ang) + y * math.cos(ang)) / pitch_mm
    tau = 2 * math.pi
    frac = lambda a: np.mod(a, 1.0)
    tri = lambda a: 1.0 - 2.0 * np.abs(frac(a) - 0.5)
    rr = np.sqrt(x*x + y*y)
    theta = np.arctan2(y, x)

    if pattern == 'dimples':
        h = _dimple_height(u + phase, v + phase, pitch_mm, dimple_diameter_mm)
    elif pattern == 'brick':
        h = _brick_height(u * pitch_mm + phase * brick_width_mm,
                          v * pitch_mm, brick_width_mm, brick_height_mm,
                          brick_joint_mm, brick_bevel_mm, brick_row_offset, brick_style)
    elif pattern == 'hobnail':
        h = 1 - 2 * np.maximum(np.abs(frac(u + phase) - .5), np.abs(frac(v + phase) - .5))
        # A true truncated pyramid: fixed top plateau width in physical mm.
        # softness retained as a backwards-compatible optional slope adjustment.
        local = np.maximum(np.abs(frac(u + phase) - .5), np.abs(frac(v + phase) - .5))
        half_top = top_width_mm / (2 * pitch_mm)
        h = np.clip((.5 - local) / (.5 - half_top), 0, 1)
        if softness:
            h = np.clip(h / max(.05, 1 - .85 * softness), 0, 1)
    elif pattern == 'tapisserie':
        # Stepped raised square blocks with bevelled boundaries.
        d = np.maximum(np.abs(frac(u + phase) - .5), np.abs(frac(v + phase) - .5))
        # Distance from the cell boundary toward the square center, in mm.
        # The recessed channel is centered on each grid line; the bevel
        # begins at the inner channel edge and rises linearly to the top.
        inward_mm = (.5 - d) * pitch_mm
        channel_half = groove_width_mm / 2.0
        if bevel_width_mm == 0:
            h = (inward_mm >= channel_half).astype(np.float32)
        else:
            h = np.clip((inward_mm - channel_half) / bevel_width_mm, 0, 1)
    elif pattern == 'sunburst':
        # Radial, periodic groove field; finer grooves toward center.
        h = .5 + .5 * np.cos(grooves * theta + tau * phase)
        h = .5 + (h - .5) * (1 - .65 * softness)
        # Single center pixel should not have an arbitrary angular value.
        h = np.where(rr < size_mm / pixels, 0.5, h)
    elif pattern == 'basketweave':
        h = _woven_height(u + phase, v + phase, .22)
    elif pattern == 'barleycorn':
        # Stylized interlaced, elongated grain-shaped lobes (not a historic toolpath).
        row = np.floor(v + phase).astype(np.int32)
        shift = .5 * (row % 2)
        fu = frac(u + shift + phase)
        fv = frac(v + phase)
        du = (fu - .5) / .48
        dv = (fv - .5) / .46
        grain = np.maximum(0, 1 - du*du - dv*dv)
        ridge = .5 + .5 * np.cos(tau * (u - .28 * np.sin(tau * v) + phase))
        h = .08 + .82 * grain + .10 * ridge
        h = np.clip(h, 0, 1)
    elif pattern == 'fishscales':
        h = _fishscales_height(u + phase, v + phase, fishscales_style, softness)
    elif pattern == 'wave':
        # Independent physical lateral meander and vertical ridge height.
        lateral = wave_meander_mm / pitch_mm + .45 * softness
        wave = .5 + .5 * np.cos(tau * (v + phase + lateral * np.sin(tau * u / 6)))
        h = 1 - ridge_height_fraction * (1 - wave)
    elif pattern == 'annularwave':
        # Concentric circular ridges centered on the dial, with periodic Z-height.
        # Rotation does not affect concentric geometry.
        wave = .5 + .5 * np.cos(tau * (rr / pitch_mm + phase))
        h = 1 - ridge_height_fraction * (1 - wave)
        # Radial height depends only on radius; no directional lighting.
    elif pattern == 'flinque':
        # Radially organized intersecting sinusoidal guilloché waves.
        radial = rr / pitch_mm
        wave = radial + (.22 + .35 * softness) * np.sin(12 * theta + tau * phase)
        h = .5 + .25 * np.cos(tau * wave) + .25 * np.cos(tau * (radial - .22 * np.sin(12*theta + tau*phase)))
        h = np.clip(h, 0, 1)

    elif pattern == 'graindorge':
        # Staggered curved elongated grain lobes; grain_aspect sets length/width.
        # Independent pitch along x, staggered rows along y.
        rows = np.floor(v + phase).astype(np.int32)
        a = frac(u / grain_aspect + .5 * (rows % 2) + phase) - .5
        b = frac(v + phase) - .5
        warp = a + amplitude * .25 * np.sin(tau * b)
        ellipse = (warp / .48)**2 + (b / .46)**2
        grain = np.clip(1 - ellipse, 0, 1)
        # Fine central grain vein; pure height, not optical shading.
        vein = np.exp(-((warp + .06 * np.sin(tau*b)) / .055)**2)
        h = np.clip(.90 * grain**.65 + .10 * vein * (grain > 0), 0, 1)
    elif pattern == 'flamme':
        # Curved radial flames with radius-dependent taper of angular width.
        # Flame taper controls narrowing of ridges toward the outer radius.
        radius_fraction = np.clip(rr / (size_mm / 2), 0, 1)
        swept = grooves * theta / tau + amplitude * np.sin(tau * rr / secondary_pitch_mm)
        ridge = .5 + .5 * np.cos(tau * (swept + phase))
        power = 1 + 5 * flame_taper * radius_fraction
        h = ridge ** power
        h = np.where(rr < size_mm / pixels, 0.5, h)
    elif pattern == 'panier':
        # Interlaced curved bands with independently adjustable bowing.
        ua = u + ribbon_curvature * np.sin(tau * v / 4) + phase
        va = v + ribbon_curvature * np.sin(tau * u / 4) + phase
        h = _woven_height(ua, va, .15)
    elif pattern == 'escargot':
        # Archimedean spiral: phase advances with radius and azimuth.
        h = .5 + .5 * np.cos(tau * (rr / pitch_mm - grooves * theta / tau + phase))
    elif pattern == 'moire':
        t = math.radians(angle_deg)
        wave_a = np.cos(tau * (x / pitch_mm + phase))
        wave_b = np.cos(tau * ((x*np.cos(t) + y*np.sin(t)) / secondary_pitch_mm + phase))
        h = np.clip(.5 + .25 * (wave_a + wave_b), 0, 1)
    elif pattern == 'chevron':
        # Mirrored diagonal ridges, alternating direction by row.
        row = np.floor(v + phase).astype(np.int32)
        zig = np.abs(frac(u + phase) - .5)
        h = .5 + .5 * np.cos(tau * (v + phase + amplitude * np.where(row % 2 == 0, zig, -zig)))
    elif pattern == 'rosette':
        petals = np.cos(grooves * theta + tau * phase)
        secondary = np.cos(2 * grooves * theta + tau * phase)
        modulation = (1 - rosette_harmonics) * petals + rosette_harmonics * secondary
        h = .5 + .5 * np.cos(tau * (rr / pitch_mm + amplitude * modulation))
        h = np.where(rr < size_mm / pixels, 0.5, h)
    elif pattern == 'sectorrings':
        rings = .5 + .5 * np.cos(tau * (rr / pitch_mm + phase))
        sector = .5 + .5 * np.cos(segments * theta)
        h = np.clip(rings * (.5 + .5 * sector), 0, 1)
    elif pattern == 'honeycomb':
        # Signed distance to the six flat edges of the nearest hexagonal cell.
        xx, yy = _hex_cell_coordinates(u, v)
        edge = .5 - np.maximum.reduce([np.abs(xx),
            np.abs(.5*xx + np.sqrt(3)/2*yy),
            np.abs(-.5*xx + np.sqrt(3)/2*yy)])
        # Recessed hexagonal joints, bevel, then a flat cell interior.
        joint_half = .025
        bevel = .10 + .30*softness
        h = np.clip((edge-joint_half)/bevel, 0, 1)
    elif pattern == 'perlage':
        h = _perlage_height(u + phase, v + phase, pitch_mm,
                            perlage_ring_pitch_mm, perlage_overlap)
    elif pattern == 'diamondlattice':
        t = math.radians(angle_deg)
        a = (x*np.cos(t) + y*np.sin(t))/pitch_mm
        b = (x*np.cos(t) - y*np.sin(t))/pitch_mm
        da = np.abs(frac(a + phase)-.5)*2
        db = np.abs(frac(b + phase)-.5)*2
        h = np.clip((1-da)*(1-db), 0, 1)
    elif pattern == 'isometriccubes':
        h = _cube_height(u + phase, v + phase, pitch_mm, cube_gap_mm, cube_step_fraction)
    elif pattern == 'fanscallop':
        xx, t, distance = _scallop_coordinates(u + phase, v + phase)
        radial = np.hypot(xx, t)
        ribs = .5 + .5*np.cos(tau*radial*(1+amplitude))
        envelope = np.sin(np.pi*t)**2 * np.cos(np.pi*xx)**2
        h = np.clip(distance/.035, 0, 1) * (.15 + .85*envelope*ribs)
    elif pattern == 'asanoha':
        h = _asanoha_height(u + phase, v + phase, pitch_mm, line_width_mm, asanoha_style)

    h = np.asarray(h, dtype=np.float32)
    if invert:
        h = 1 - h
    if circular:
        h = np.where(rr <= size_mm / 2, h, np.clip(background, 0, 1))
    out = np.uint16(np.round(np.clip(h, 0, 1) * 65535))
    meta = dict(pattern=pattern, pattern_name=PATTERNS[pattern], size_mm=size_mm,
                pixels=pixels, pitch_mm=pitch_mm, depth_mm=depth_mm,
                rotation=rotation, phase=phase, softness=softness,
                invert=invert, circular=circular, background=background,
                grooves=grooves, groove_width_mm=groove_width_mm,
                bevel_width_mm=bevel_width_mm, top_width_mm=top_width_mm,
                wave_meander_mm=wave_meander_mm, ridge_height_fraction=ridge_height_fraction,
                grain_aspect=grain_aspect, flame_taper=flame_taper,
                ribbon_curvature=ribbon_curvature, rosette_harmonics=rosette_harmonics,
                amplitude=amplitude,
                secondary_pitch_mm=secondary_pitch_mm, angle_deg=angle_deg, segments=segments,
                line_width_mm=line_width_mm, cube_gap_mm=cube_gap_mm, cube_step_fraction=cube_step_fraction, asanoha_style=asanoha_style, fishscales_style=fishscales_style, brick_width_mm=brick_width_mm,
                brick_height_mm=brick_height_mm, brick_joint_mm=brick_joint_mm,
                brick_bevel_mm=brick_bevel_mm, brick_row_offset=brick_row_offset,
                brick_style=brick_style, perlage_ring_pitch_mm=perlage_ring_pitch_mm,
                perlage_overlap=perlage_overlap, dimple_diameter_mm=dimple_diameter_mm,
                grayscale='white=highest; black=deepest',
                pixel_pitch_mm=size_mm/pixels,
                note='Depth is design metadata; calibrate laser material removal experimentally.')
    return out, meta


def render_preview(**params):
    """Filter a denser height map so narrow grooves survive the small preview."""
    params['pixels'] = min(params.get('pixels', 2048), 1920)
    array, meta = render(**params)
    image = Image.fromarray((array / 257).astype(np.uint8))
    image.thumbnail((480, 480), Image.Resampling.LANCZOS)
    return image, meta


def save_map(array, meta, output):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(array, dtype=np.uint16)).save(path)
    Image.fromarray((array / 257).astype(np.uint8)).save(path.with_name(path.stem + '_8bit.png'))
    path.with_suffix('.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return path


# Visible controls by pattern. Shared controls are always available.
COMMON_FIELDS = ('size_mm', 'pixels', 'depth_mm')
PATTERN_FIELDS = {
    'hobnail': ('pitch_mm', 'rotation', 'phase', 'top_width_mm', 'softness'),
    'tapisserie': ('pitch_mm', 'rotation', 'phase', 'groove_width_mm', 'bevel_width_mm'),
    'barleycorn': ('pitch_mm', 'rotation', 'phase'),
    'sunburst': ('grooves', 'phase', 'softness'),
    'basketweave': ('pitch_mm', 'rotation', 'phase'),
    'fishscales': ('pitch_mm', 'rotation', 'phase', 'softness', 'fishscales_style'),
    'flinque': ('pitch_mm', 'phase', 'softness'),
    'wave': ('pitch_mm', 'rotation', 'phase', 'wave_meander_mm', 'ridge_height_fraction'),
    'annularwave': ('pitch_mm', 'phase', 'ridge_height_fraction'),
    'graindorge': ('pitch_mm', 'rotation', 'phase', 'amplitude', 'grain_aspect'),
    'flamme': ('grooves', 'secondary_pitch_mm', 'phase', 'amplitude', 'flame_taper'),
    'panier': ('pitch_mm', 'rotation', 'phase', 'ribbon_curvature'),
    'escargot': ('pitch_mm', 'grooves', 'phase'),
    'moire': ('pitch_mm', 'secondary_pitch_mm', 'angle_deg', 'phase'),
    'chevron': ('pitch_mm', 'rotation', 'phase', 'amplitude'),
    'rosette': ('pitch_mm', 'grooves', 'phase', 'amplitude', 'rosette_harmonics'),
    'sectorrings': ('pitch_mm', 'segments', 'phase'),
    'honeycomb': ('pitch_mm', 'rotation', 'softness'),
    'perlage': ('pitch_mm', 'rotation', 'phase', 'perlage_ring_pitch_mm', 'perlage_overlap'),
    'diamondlattice': ('pitch_mm', 'angle_deg', 'phase'),
    'isometriccubes': ('pitch_mm', 'rotation', 'phase', 'cube_gap_mm', 'cube_step_fraction'),
    'fanscallop': ('pitch_mm', 'rotation', 'phase', 'amplitude'),
    'asanoha': ('pitch_mm', 'rotation', 'phase', 'line_width_mm', 'asanoha_style'),
    'brick': ('brick_width_mm', 'brick_height_mm', 'brick_joint_mm', 'brick_bevel_mm', 'brick_row_offset', 'brick_style', 'rotation', 'phase'),
    'dimples': ('pitch_mm', 'dimple_diameter_mm', 'rotation', 'phase'),

}
FIELD_SPECS = {
    'perlage_ring_pitch_mm': ('Perlage ring spacing (mm)', '0.1'),
    'perlage_overlap': ('Perlage overlap (0–0.5)', '0.5'),
    'size_mm': ('Area width (mm)', '28.5'),
    'pixels': ('Output pixels / side', '2048'),
    'depth_mm': ('Target depth (mm)', '0.15'),
    'pitch_mm': ('Pattern pitch (mm)', '0.75'),
    'rotation': ('Rotation (degrees)', '0'),
    'phase': ('Pattern offset (cycles)', '0'),
    'softness': ('Softness / meander (0–1)', '0'),
    'grooves': ('Radial groove count', '96'),
    'groove_width_mm': ('Groove width (mm)', '0.20'),
    'bevel_width_mm': ('Bevel width (mm)', '0.08'),
    'background': ('Outside-circle level (0–1)', '0'),
    'top_width_mm': ('Hobnail plateau width (mm)', '0'),
    'wave_meander_mm': ('Wave lateral meander (mm)', '0'),
    'ridge_height_fraction': ('Wave ridge height fraction (0–1)', '1'),
    'grain_aspect': ('Grain length / width ratio', '2'),
    'flame_taper': ('Flame outward taper (0–1)', '0.5'),
    'ribbon_curvature': ('Panier ribbon curvature (0–2)', '0.35'),
    'rosette_harmonics': ('Rosette second harmonic (0–1)', '0'),
    'amplitude': ('Pattern modulation (0–2)', '0.35'),
    'secondary_pitch_mm': ('Secondary pitch (mm)', '1.2'),
    'angle_deg': ('Crossing angle (degrees)', '60'),
    'segments': ('Sector count', '12'),
    'line_width_mm': ('Asanoha line width (mm)', '0.055'),
    'asanoha_style': ('Asanoha relief style', 'faceted'),
    'fishscales_style': ('Fish scales relief style', 'rounded'),
    'cube_gap_mm': ('Cube border groove (mm)', '0.04'),
    'cube_step_fraction': ('Cube face height step (0–0.5)', '0.28'),
    'brick_width_mm': ('Brick width (mm)', '1.20'),
    'brick_height_mm': ('Brick height (mm)', '0.60'),
    'brick_joint_mm': ('Brick joint width (mm)', '0.10'),
    'brick_bevel_mm': ('Brick bevel width (mm)', '0.08'),
    'brick_row_offset': ('Brick row offset (0–1)', '0.50'),
    'brick_style': ('Brick relief style', 'faceted'),
    'dimple_diameter_mm': ('Dimple diameter (mm)', '0.65'),
}


FIELD_TOOLTIPS = {
    'size_mm': 'Enter the width of the square design area in millimeters. With a circular mask, this is the circle diameter.',
    'pixels': 'Enter a whole number from 128 to 8192 for each side of the saved image. More pixels preserve finer details but take longer.',
    'depth_mm': 'Enter the intended surface depth in millimeters, greater than 0. Used for the 3D view and saved settings; actual engraving depth depends on your laser setup.',
    'pitch_mm': 'Enter the spacing between repeating pattern features in millimeters, greater than 0. Smaller values make a finer pattern.',
    'rotation': 'Enter an angle in degrees to turn the pattern. Use 0 for its original direction.',
    'phase': 'Shift where the pattern starts. Enter a number in pattern repeats; try 0.5 for a half-repeat shift.',
    'softness': 'Enter 0 to 1 to adjust the pattern shape. Higher values soften relief or add waviness, depending on the pattern.',
    'grooves': 'Enter a whole number of radial grooves or repeating features around the center, at least 4.',
    'groove_width_mm': 'Enter the width of the recessed channels between squares in millimeters. Use 0 or more, less than the pattern pitch.',
    'bevel_width_mm': 'Enter the width of each sloped square edge in millimeters. Use 0 for sharp edges; slopes must fit within half the raised square width.',
    'background': 'Set the height outside the circle: 0 is deepest (black), 1 is highest (white), and values between give intermediate heights.',
    'top_width_mm': 'Enter the flat top width of each hobnail in millimeters. Use 0 for pointed tops, or a value smaller than the pattern pitch.',
    'wave_meander_mm': 'Enter how far the waves bend sideways in millimeters. Use 0 for straight waves or a larger value for more bending.',
    'ridge_height_fraction': 'Enter 0 to 1 for the wave relief strength. Use 0 for a flat surface or 1 for the full height range.',
    'grain_aspect': 'Enter the grain length compared with its width, at least 1. For example, 2 makes grains twice as long as they are wide.',
    'flame_taper': 'Enter 0 to 1 to narrow flames toward the outside of the dial. Higher values make the outer tips narrower.',
    'ribbon_curvature': 'Enter 0 to 2 to bend the woven ribbons. Use 0 for straight ribbons or a larger value for more curve.',
    'rosette_harmonics': 'Enter 0 to 1 to blend extra petals into the rosette. Use 0 for the original petal count or 1 for twice as many.',
    'amplitude': 'Enter 0 to 2 to adjust the strength of the pattern variation, such as bending, zigzags, petals, or scallop ribs.',
    'secondary_pitch_mm': 'Enter the spacing of the second wave pattern in millimeters, greater than 0. For flames, this sets how often they bend outward.',
    'angle_deg': 'Enter an angle in degrees to change how the lines cross and shape the diamonds or overlapping waves.',
    'segments': 'Enter a whole number, at least 2, for the number of sections around the rings.',
    'line_width_mm': 'Enter the hemp-leaf groove width in millimeters, greater than 0 and less than half the pattern pitch.',
    'asanoha_style': 'Choose flat, angled faces (faceted), soft domes (rounded), or grooves cut into a flat surface (engraved).',
    'fishscales_style': 'Choose soft curved scales (rounded), angled scales (faceted), or scale outlines cut into a flat surface (engraved).',
    'cube_gap_mm': 'Enter the groove width between cubes in millimeters, greater than 0 and less than half the pattern pitch.',
    'cube_step_fraction': 'Enter a value greater than 0 and less than 0.5 for the height difference between cube faces. Larger values make the steps deeper.',
    'brick_width_mm': 'Enter the horizontal size of each repeating brick in millimeters, greater than 0.',
    'brick_height_mm': 'Enter the vertical size of each brick row in millimeters, greater than 0.',
    'brick_joint_mm': 'Enter the gap between bricks in millimeters. Use 0 or more, smaller than both the brick width and height.',
    'brick_bevel_mm': 'Enter the sloped edge width of each brick in millimeters. Use 0 for sharp edges; slopes must fit within half the raised brick width and height.',
    'brick_row_offset': 'Enter 0 to 1 to shift alternate brick rows. Use 0 for aligned joints or 0.5 for a half-brick shift.',
    'brick_style': 'Choose bricks with sloped edges (faceted), soft tops (rounded), or joints cut into a flat surface (engraved).',
    'dimple_diameter_mm': 'Enter the diameter of each round recess in millimeters, greater than 0 and no larger than the pattern pitch. Set diameter equal to pitch for touching edges. Pitch sets center-to-center spacing; target depth sets the bowl depth.',
    'perlage_ring_pitch_mm': 'Enter the spacing between fine rings within each circular mark in millimeters, greater than 0.',
    'perlage_overlap': 'Enter 0 to 0.5 for how much neighboring circular marks overlap. Use 0 for touching marks or 0.5 for the most overlap.',
}


def run_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError as e:
        raise SystemExit('Tkinter is unavailable. Install python3-tk or use --cli.') from e
    from gui_tooltips import add_tooltip

    root = tk.Tk()
    root.title(f'Watch Dial Pattern Generator v{__version__}')
    root.geometry('980x760')
    root.minsize(800, 580)
    outer = ttk.Frame(root, padding=14)
    outer.pack(fill='both', expand=True)
    left = ttk.Frame(outer)
    left.pack(side='left', fill='y', padx=(0, 18))
    right = ttk.Frame(outer)
    right.pack(side='left', fill='both', expand=True)
    ttk.Label(left, text='Pattern parameters', font=('TkDefaultFont', 13, 'bold')).pack(anchor='w', pady=(0, 12))
    ttk.Label(left, text='Pattern').pack(anchor='w')
    pattern_choice = tk.StringVar()
    pattern_combo = ttk.Combobox(left, textvariable=pattern_choice, state='readonly', width=33, values=list(PATTERNS.values()))
    startup_pattern_index = 0
    pattern_combo.current(startup_pattern_index)
    pattern_combo.pack(fill='x', pady=(2, 10))
    add_tooltip(pattern_combo, 'Choose a dial pattern. The fields below change to show the settings for that pattern.')
    # Scroll the parameter column: small macOS screens can still access every control.
    scroll_holder = ttk.Frame(left)
    scroll_holder.pack(fill='x')
    field_canvas = tk.Canvas(scroll_holder, width=290, height=300, highlightthickness=0,
                             yscrollincrement=16)
    field_scroll = ttk.Scrollbar(scroll_holder, orient='vertical', command=field_canvas.yview)
    field_canvas.configure(yscrollcommand=field_scroll.set)
    field_canvas.pack(side='left', fill='y')
    field_scroll.pack(side='left', fill='y')
    field_frame = ttk.Frame(field_canvas)
    field_canvas.create_window((0,0), window=field_frame, anchor='nw')
    field_frame.bind('<Configure>', lambda e: field_canvas.configure(scrollregion=field_canvas.bbox('all')))
    values = {key: tk.StringVar(value=default) for key, (_, default) in FIELD_SPECS.items()}
    field_rows = {}
    field_inputs = {}
    for key, (label, _) in FIELD_SPECS.items():
        row = ttk.Frame(field_frame)
        ttk.Label(row, text=label).pack(anchor='w')
        if key in ENUM_FIELDS:
            widget = ttk.Combobox(row, textvariable=values[key], state='readonly', width=31, values=list(ENUM_FIELDS[key]))
            widget.set(values[key].get())
        else:
            widget = ttk.Entry(row, textvariable=values[key], width=34)
        widget.pack(fill='x', pady=(1, 7))
        add_tooltip(widget, FIELD_TOOLTIPS[key])
        field_rows[key] = row
        field_inputs[key] = widget

    scroll_remainder = 0.0
    windowing_system = root.tk.call('tk', 'windowingsystem')

    def scroll_parameters(event, precise=False):
        nonlocal scroll_remainder
        if precise:
            # Tk 9 packs signed 16-bit X/Y pixel deltas into a single value.
            # Only the low (vertical) half scrolls this parameter column.
            delta_y = event.delta & 0xffff
            if delta_y >= 0x8000:
                delta_y -= 0x10000
            movement = -delta_y / int(field_canvas.cget('yscrollincrement'))
        elif getattr(event, 'num', None) in (4, 5):
            movement = -3 if event.num == 4 else 3
        else:
            # Aqua reports small trackpad deltas; Windows uses 120 per notch.
            movement = -event.delta if windowing_system == 'aqua' else -event.delta / 120 * 3
        scroll_remainder += movement
        steps = math.trunc(scroll_remainder)
        scroll_remainder -= steps
        if steps:
            field_canvas.yview_scroll(steps, 'units')
        if hasattr(event.widget, 'tooltip'):
            event.widget.tooltip.hide()
        return 'break'

    # Run before entry/combobox class bindings so wheel gestures scroll the
    # panel without changing parameter values. Other GUI areas keep their bindings.
    scroll_tag = 'ParameterScroll:' + str(field_canvas)
    root.bind_class(scroll_tag, '<MouseWheel>', scroll_parameters)
    if root.tk.call('info', 'commands', 'tk::PreciseScrollDeltas'):
        root.bind_class(scroll_tag, '<TouchpadScroll>',
                        lambda event: scroll_parameters(event, precise=True))
    if windowing_system == 'x11':
        root.bind_class(scroll_tag, '<Button-4>', scroll_parameters)
        root.bind_class(scroll_tag, '<Button-5>', scroll_parameters)

    def bind_parameter_scroll(widget):
        widget.bindtags((scroll_tag, *widget.bindtags()))
        for child in widget.winfo_children():
            bind_parameter_scroll(child)

    bind_parameter_scroll(scroll_holder)
    invert = tk.BooleanVar(value=False)
    circular = tk.BooleanVar(value=False)
    add_tooltip(ttk.Checkbutton(left, text='Invert height map', variable=invert),
                'Swap high and low areas: raised features become recessed, and recessed features become raised.').pack(anchor='w')
    add_tooltip(ttk.Checkbutton(left, text='Circular mask', variable=circular),
                'Keep the pattern inside a circle. Use Outside-circle level to set the height of the surrounding area.').pack(anchor='w')
    ttk.Label(right, text='Grayscale height map preview', font=('TkDefaultFont', 13, 'bold')).pack(anchor='w')
    preview_label = ttk.Label(right)
    preview_label.pack(fill='both', expand=True, pady=10)
    status = tk.StringVar(value='Preview is a reduced-resolution sample.')
    ttk.Label(right, textvariable=status, wraplength=480).pack(anchor='w', pady=8)
    right._preview_image = None
    pitch_values = {}
    pitch_pattern = None
    preview_params = None

    def selected_pattern():
        return list(PATTERNS)[pattern_combo.current()]

    def refresh_fields(event=None):
        nonlocal pitch_pattern
        pattern = selected_pattern()
        if pattern != pitch_pattern:
            if pitch_pattern is not None:
                pitch_values[pitch_pattern] = values['pitch_mm'].get()
            values['pitch_mm'].set(pitch_values.get(pattern, str(default_pitch(pattern))))
            pitch_pattern = pattern
        for row in field_rows.values():
            row.pack_forget()
        active = COMMON_FIELDS + PATTERN_FIELDS[selected_pattern()]
        if circular.get():
            active += ('background',)
        for key in active:
            field_rows[key].pack(fill='x')
        update_preview()

    def params():
        active = set(COMMON_FIELDS + PATTERN_FIELDS[selected_pattern()])
        if circular.get():
            active.add('background')
        kw = {}
        for k in active:
            if k in ENUM_FIELDS:
                kw[k] = values[k].get()
            elif k in ('pixels', 'grooves', 'segments'):
                kw[k] = int(values[k].get())
            else:
                kw[k] = float(values[k].get())
        kw.update(pattern=selected_pattern(), invert=invert.get(), circular=circular.get())
        return kw

    def update_preview():
        nonlocal preview_params
        try:
            current_params = params()
            im, meta = render_preview(**current_params)
            photo = ImageTk.PhotoImage(im)
            preview_label.configure(image=photo)
            right._preview_image = photo
            preview_params = current_params
            status.set(f"{meta['pattern_name']} | preview {im.width} px | white = high")
        except Exception as e:
            status.set('Preview error: ' + str(e))

    def preview_on_focus_out(event):
        try:
            if params() == preview_params and not status.get().startswith('Preview error:'):
                return
        except (ValueError, TypeError):
            pass  # Let update_preview report invalid input and retain the image.
        update_preview()

    def export():
        try:
            kw = params()
            filename = filedialog.asksaveasfilename(defaultextension='.png',
                filetypes=[('PNG image', '*.png')], initialfile=kw['pattern'] + '_heightmap.png')
            if not filename:
                return
            root.config(cursor='watch')
            root.update_idletasks()
            arr, meta = render(**kw)
            save_map(arr, meta, filename)
            status.set('Saved 16-bit PNG, 8-bit PNG, and JSON: ' + filename)
            messagebox.showinfo('Export complete', 'Saved 16-bit PNG, 8-bit PNG and JSON settings.')
        except Exception as e:
            messagebox.showerror('Export failed', str(e))
        finally:
            root.config(cursor='')

    def reset_all():
        nonlocal pitch_pattern
        # Reset hidden fields as well as currently visible fields, then re-render.
        for key, (_, default) in FIELD_SPECS.items():
            values[key].set(default)
        invert.set(False)
        circular.set(False)
        pitch_values.clear()
        pitch_pattern = None
        pattern_combo.current(startup_pattern_index)
        field_canvas.yview_moveto(0)
        refresh_fields()
        status.set('All values reset to startup defaults. ' + status.get())

    pattern_combo.bind('<<ComboboxSelected>>', refresh_fields)
    for key, widget in field_inputs.items():
        widget.bind('<FocusOut>', preview_on_focus_out, add='+')
        if key in ENUM_FIELDS:
            widget.bind('<<ComboboxSelected>>', lambda event: update_preview())
    circular.trace_add('write', lambda *_: refresh_fields())
    invert.trace_add('write', lambda *_: update_preview())
    add_tooltip(ttk.Button(left, text='Update preview', command=update_preview),
                'Redraw the small preview using your current settings. White areas are high and black areas are deep.').pack(fill='x', pady=(12, 5))
    def inspect_relief():
        previous_cursor = root.cget('cursor')

        def finish_launch():
            root.config(cursor=previous_cursor)
            inspect_button.state(['!disabled'])

        try:
            cursor = 'spinning' if root.tk.call('tk', 'windowingsystem') == 'aqua' else 'watch'
            root.config(cursor=cursor)
            inspect_button.state(['disabled'])
            root.update_idletasks()
            from inspection import open_inspection
            kw = params()
            arr, meta = render(**kw)
            session = open_inspection(root, arr, meta, on_ready=finish_launch)
            inspection_updates.sessions.append(session)
        except Exception as e:
            finish_launch()
            messagebox.showerror('Inspection failed', str(e))

    inspect_button = ttk.Button(left, text='Inspect enlarged / 3D', command=inspect_relief)
    add_tooltip(inspect_button,
                'Open a larger view to zoom in and explore the surface in 3D. It updates as you change settings.').pack(fill='x', pady=(0, 5))
    add_tooltip(ttk.Button(left, text='Reset to defaults', command=reset_all),
                'Restore the starting pattern and all original settings, including settings for other patterns.').pack(fill='x', pady=(0, 5))
    add_tooltip(ttk.Button(left, text='Export PNG + settings', command=export),
                'Choose where to save the full-size height map, an 8-bit image copy, and a settings file.').pack(fill='x')
    ttk.Label(left, text=('White = highest surface; black = deepest.\nExports contain height only.\n\n'
        'Only relevant pattern controls are shown.\nTapisserie groove and bevel widths are independent.\n'
        'Asanoha supports engraved, faceted, and rounded relief styles.\nFish Scales supports engraved, faceted, and rounded relief styles.'), wraplength=270).pack(anchor='w', pady=14)
    from inspection import InspectionUpdates
    inspection_updates = InspectionUpdates(root, params, render, status.set)
    for variable in (*values.values(), pattern_choice, invert, circular):
        variable.trace_add('write', inspection_updates.schedule)
    refresh_fields()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--gui', action='store_true', help='Launch Tkinter interface (default without args)')
    parser.add_argument('--cli', action='store_true', help='Generate using command-line arguments')
    parser.add_argument('--pattern', choices=list(PATTERNS), default='hobnail')
    parser.add_argument('--size-mm', type=float, default=28.5)
    parser.add_argument('--pixels', type=int, default=2048)
    parser.add_argument('--pitch-mm', type=float, default=None,
                        help='Pattern pitch in mm (default: 1.0 for Hobnail, 0.75 otherwise)')
    parser.add_argument('--depth-mm', type=float, default=.15)
    parser.add_argument('--rotation', type=float, default=0)
    parser.add_argument('--phase', type=float, default=0)
    parser.add_argument('--softness', type=float, default=0)
    parser.add_argument('--grooves', type=int, default=96)
    parser.add_argument('--invert', action='store_true')
    parser.add_argument('--circular', action='store_true')
    parser.add_argument('--background', type=float, default=0)
    parser.add_argument('--groove-width-mm', type=float, default=0.20, help='Tapisserie recessed channel width')
    parser.add_argument('--bevel-width-mm', type=float, default=0.08, help='Tapisserie slope width on each square edge')
    parser.add_argument('--top-width-mm', type=float, default=0)
    parser.add_argument('--wave-meander-mm', type=float, default=0)
    parser.add_argument('--ridge-height-fraction', type=float, default=1)
    parser.add_argument('--grain-aspect', type=float, default=2)
    parser.add_argument('--flame-taper', type=float, default=.5)
    parser.add_argument('--ribbon-curvature', type=float, default=.35)
    parser.add_argument('--rosette-harmonics', type=float, default=0)
    parser.add_argument('--amplitude', type=float, default=.35)
    parser.add_argument('--secondary-pitch-mm', type=float, default=1.2)
    parser.add_argument('--angle-deg', type=float, default=60)
    parser.add_argument('--segments', type=int, default=12)
    parser.add_argument('--line-width-mm', type=float, default=.055)
    parser.add_argument('--cube-gap-mm', type=float, default=.04)
    parser.add_argument('--cube-step-fraction', type=float, default=.28)
    parser.add_argument('--asanoha-style', choices=ENUM_FIELDS['asanoha_style'], default='faceted')
    parser.add_argument('--fishscales-style', choices=ENUM_FIELDS['fishscales_style'], default='rounded')
    parser.add_argument('--brick-width-mm', type=float, default=1.2)
    parser.add_argument('--brick-height-mm', type=float, default=.6)
    parser.add_argument('--brick-joint-mm', type=float, default=.1)
    parser.add_argument('--brick-bevel-mm', type=float, default=.08)
    parser.add_argument('--brick-row-offset', type=float, default=.5)
    parser.add_argument('--brick-style', choices=ENUM_FIELDS['brick_style'], default='faceted')
    parser.add_argument('--perlage-ring-pitch-mm', type=float, default=.1)
    parser.add_argument('--perlage-overlap', type=float, default=.5)
    parser.add_argument('--dimple-diameter-mm', type=float, default=.65,
                        help='Dimple diameter in mm, positive and no larger than pattern pitch')
    parser.add_argument('--output', default='watch_dial_heightmap.png')
    args = parser.parse_args()
    if args.gui or (not args.cli and len(__import__('sys').argv) == 1):
        run_gui()
        return
    options = vars(args)
    options.pop('gui')
    options.pop('cli')
    output = options.pop('output')
    array, meta = render(**options)
    save_map(array, meta, output)
    print('Saved:', output, '| 8-bit copy and JSON metadata saved alongside')


if __name__ == '__main__':
    main()
