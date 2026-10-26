"""
Natural mouse movement trajectory generator.
Uses Cubic Bezier curves with randomized control points and organic speed profiles.
"""

import math
import random
from typing import List, Tuple


def _bezier_point(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    t: float,
) -> Tuple[float, float]:
    """Calculates a point along a cubic Bezier curve at parameter t in [0, 1]."""
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


def _ease_in_out(t: float) -> float:
    """Smooth S-curve easing (ease-in, ease-out) for organic human acceleration."""
    if t < 0.5:
        return 4.0 * t * t * t
    p = 2.0 * t - 2.0
    return 0.5 * p * p * p + 1.0


def generate_bezier_trajectory(
    start: Tuple[int, int],
    end: Tuple[int, int],
    duration: float = 0.6,
    steps: int = 50,
    deviation: float = 0.25,
) -> List[Tuple[int, int, float]]:
    """
    Generates a list of (x, y, sleep_delay) points forming a realistic human mouse stroke.
    
    Args:
        start: Starting screen coordinate (x, y).
        end: Target screen coordinate (x, y).
        duration: Total movement duration in seconds.
        steps: Number of intermediate interpolation steps.
        deviation: Degree of lateral deviation from straight line.
    
    Returns:
        List of tuples: (integer x, integer y, sleep delay until this point).
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)

    if dist < 2:
        return [(end[0], end[1], duration)]

    # Compute perpendicular vector for organic curving
    norm_x = -dy / dist
    norm_y = dx / dist

    # Generate two randomized control points with human-like lateral drift
    side = random.choice([-1.0, 1.0])
    curviness1 = random.uniform(0.1, deviation) * dist * side
    curviness2 = random.uniform(0.05, deviation * 0.8) * dist * side * random.choice([1.0, -0.5])

    # Control point 1 placed roughly 1/3 along trajectory
    p0 = (float(start[0]), float(start[1]))
    p1 = (
        p0[0] + dx * 0.3 + norm_x * curviness1 + random.uniform(-10, 10),
        p0[1] + dy * 0.3 + norm_y * curviness1 + random.uniform(-10, 10),
    )
    # Control point 2 placed roughly 2/3 along trajectory
    p2 = (
        p0[0] + dx * 0.7 + norm_x * curviness2 + random.uniform(-10, 10),
        p0[1] + dy * 0.7 + norm_y * curviness2 + random.uniform(-10, 10),
    )
    p3 = (float(end[0]), float(end[1]))

    points: List[Tuple[int, int, float]] = []
    base_step_time = duration / max(steps, 1)

    for i in range(1, steps + 1):
        raw_t = i / steps
        eased_t = _ease_in_out(raw_t)

        bx, by = _bezier_point(p0, p1, p2, p3, eased_t)

        # Subtle physiological tremor (hand micro-jitter)
        tremor_x = random.uniform(-0.6, 0.6) if i < steps else 0.0
        tremor_y = random.uniform(-0.6, 0.6) if i < steps else 0.0

        ix = int(round(bx + tremor_x))
        iy = int(round(by + tremor_y))

        # Dynamic variable micro-sleeps to replicate human motor variability
        dt = base_step_time * random.uniform(0.85, 1.15)
        points.append((ix, iy, dt))

    return points
