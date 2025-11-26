import json
import io

from itertools import cycle

from .client import Subject, network_retry
from .lists import is_list_like


GLYPHS = (
    ("white", "circle"),
    ("red", "square"),
)


def create_subject(lc_json, project, metadata={}):
    subject = Subject()
    subject.links.project = project
    subject.add_location(
        lc_json,
        media_type="application/json",
    )

    subject.metadata.update(metadata)
    network_retry(subject.save)
    return subject


def lightcurve_to_json(lcs, labels="Lightcurve", glyphs=GLYPHS):
    if not is_list_like(lcs):
        lcs = [lcs]

    if not is_list_like(labels):
        labels = [labels] * len(lcs)

    json_data = []

    for lc, label, (color, glyph) in zip(lcs, labels, cycle(glyphs)):
        json_data.append(
            {
                "seriesData": [
                    {"x": x, "y": y}
                    for (x, y) in zip(lc["midpointMjdTai"], lc["psfFlux"])
                ],
                "seriesOptions": {
                    "color": color,
                    "glyph": glyph,
                    "label": label,
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


def lightcurve_to_subject(lcs, project, metadata={}, glyphs=GLYPHS):
    return create_subject(
        lightcurve_to_json_file(lcs, glyphs=glyphs), project, metadata
    )
