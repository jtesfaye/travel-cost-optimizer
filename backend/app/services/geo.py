import math

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return EARTH_RADIUS_MI * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def interpolate(
    a: tuple[float, float], b: tuple[float, float], fraction: float
) -> tuple[float, float]:
    return (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)


def _encode_value(value: int) -> str:
    value = ~(value << 1) if value < 0 else value << 1
    chars = []
    while value >= 0x20:
        chars.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chars.append(chr(value + 63))
    return "".join(chars)


def encode_polyline(points: list[tuple[float, float]]) -> str:
    """Google encoded polyline algorithm (precision 5)."""
    encoded = []
    prev_lat = prev_lng = 0
    for lat, lng in points:
        lat_e5, lng_e5 = round(lat * 1e5), round(lng * 1e5)
        encoded.append(_encode_value(lat_e5 - prev_lat))
        encoded.append(_encode_value(lng_e5 - prev_lng))
        prev_lat, prev_lng = lat_e5, lng_e5
    return "".join(encoded)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Inverse of encode_polyline (precision 5)."""
    points = []
    index = lat = lng = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lng += deltas[1]
        points.append((lat / 1e5, lng / 1e5))
    return points
