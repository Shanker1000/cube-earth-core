"""
features.py — Assemble S1+S2 features matching training pipeline exactly
Training used: 32 dekads (d00-d31), P10D from Jan 1 to Nov 21
Metric order per dekad: VHVV, VV, VH, RVI, NDVI, NDRE, EVI, NDWI, NDII
"""
import numpy as np
from statistics import get_s2_statistics
from sar import get_s1_statistics

S2_METRICS = ['NDVI', 'NDRE', 'EVI', 'NDWI', 'NDII']
S1_METRICS = ['VV', 'VH', 'RVI', 'VHVV']
YEARS = [2022, 2023, 2024, 2025]
DEKADS_PER_YEAR = 32  # training used d00-d31

def get_bbox(lat: float, lng: float, buffer: float = 0.003) -> list:
    return [lng-buffer, lat-buffer, lng+buffer, lat+buffer]

def get_polygon_bbox(coords: list) -> list:
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [min(lngs), min(lats), max(lngs), max(lats)]

def year_dates(year: int):
    return f"{year}-01-01T00:00:00Z", f"{year}-11-21T23:59:59Z"

def interpolate(values: list, target_n: int = 32) -> list:
    if not values:
        return [0.0] * target_n
    valid_idx = [i for i,v in enumerate(values) if v is not None]
    valid_val = [values[i] for i in valid_idx]
    if len(valid_idx) < 2:
        fill = valid_val[0] if valid_val else 0.0
        return [fill] * target_n
    x_old = np.linspace(0, 1, len(values))
    x_new = np.linspace(0, 1, target_n)
    interp = np.interp(x_new,
                       [x_old[i] for i in valid_idx],
                       valid_val)
    return [round(float(v), 4) for v in interp]

def extract_features(lat: float = None, lng: float = None,
                     polygon: list = None,
                     years: list = None,
                     feat_cols: list = None) -> dict:
    """
    Extract features matching training pipeline exactly.
    Use polygon if available, otherwise lat/lng centroid.
    """
    if years is None:
        years = YEARS

    # Get bounding box
    if polygon:
        bbox = get_polygon_bbox(polygon)
    elif lat and lng:
        bbox = get_bbox(lat, lng)
    else:
        raise ValueError("Provide lat/lng or polygon")

    features = {}

    for year in years:
        start, end = year_dates(year)
        print(f"  Extracting {year}...")

        # S2
        s2_data = get_s2_statistics(bbox, start, end)
        s2_by_metric = {m: [obs.get(m) for obs in s2_data]
                        for m in S2_METRICS}

        # S1
        s1_data = get_s1_statistics(bbox, start, end)
        s1_by_metric = {m: [obs.get(m) for obs in s1_data]
                        for m in S1_METRICS}

        # Interpolate to 32 dekads
        s2_interp = {m: interpolate(s2_by_metric[m], DEKADS_PER_YEAR)
                     for m in S2_METRICS}
        s1_interp = {m: interpolate(s1_by_metric[m], DEKADS_PER_YEAR)
                     for m in S1_METRICS}

        # Store features
        for d in range(DEKADS_PER_YEAR):
            for m in S1_METRICS:
                features[f'y{year}_d{d:02d}_{m}'] = s1_interp[m][d]
            for m in S2_METRICS:
                features[f'y{year}_d{d:02d}_{m}'] = s2_interp[m][d]

    # Align to feat_cols order if provided
    if feat_cols:
        return {col: features.get(col, 0.0) for col in feat_cols}

    return features

if __name__ == '__main__':
    import json
    with open('models/feature_columns_v2.json') as f:
        feat_cols = json.load(f)

    with open('lpis_2024_unique.json') as f:
        parcels = json.load(f)

    # Test Spring Barley parcel with polygon
    p = next(x for x in parcels if x['crop'] == 'Spring Barley')
    print(f"Testing: {p['crop']} ({p['area_ha']} ha)")

    polygon = p['geometry']['coordinates'][0]
    feats = extract_features(polygon=polygon,
                             years=[2022,2023,2024,2025],
                             feat_cols=feat_cols)

    print(f"Features: {len(feats)}")
    missing = [c for c in feat_cols if c not in feats]
    print(f"Missing:  {len(missing)}")

    # Check alignment
    print(f"\nFirst 5 feat_cols vs extracted:")
    for c in feat_cols[:5]:
        print(f"  {c}: {feats.get(c, 'MISSING')}")
