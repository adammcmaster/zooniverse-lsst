import json
import io

from itertools import cycle

from .client import Subject, network_retry
from .lists import is_list_like


GLYPHS = (
    ("white", "circle"),
    ("red", "square"),
)


def lightcurve_to_json(lcs, glyphs=GLYPHS):
    if not is_list_like(lcs):
        lcs = [lcs]

    json_data = []

    for lc, (color, glyph) in zip(lcs, cycle(glyphs)):
        if lc.mask is not None:
            ts_rows = lc[~lc.mask["flux"]]
        else:
            ts_rows = lc

        json_data.append(
            {
                "seriesData": [
                    {"x": row["time"].jd, "y": float(row["flux"].value)}
                    for row in ts_rows
                    if not numpy.isnan(row["flux"].value)
                ],
                "seriesOptions": {
                    "color": color,
                    "glyph": glyph,
                    "label": "Lightcurve",
                },
            }
        )

    return json.dumps({"data": json_data})


def lightcurve_to_json_file(*args, **kwargs):
    lc = lightcurve_to_json(*args, **kwargs)
    f = io.StringIO()
    f.write(lc)
    f.seek(0)
    return f


def subject_creator(lc_json, metadata, project):
    subject = Subject()
    subject.links.project = project
    subject.add_location(
        lc_json,
        media_type="application/json",
    )

    subject.metadata.update(metadata)
    network_retry(subject.save)
    return subject
