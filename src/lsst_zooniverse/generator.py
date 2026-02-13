import json
import io

from astropy.io import fits

from itertools import cycle

from matplotlib import pyplot
import numpy as np

from panoptes_client import Subject
from lasair import lasair_client

from .lists import is_list_like


class Location(object):
    def __init__(self, urls):
        self.urls = urls

    def as_file(self):
        raise NotImplementedError


class ImageLocation(Location):
    def as_file(self):
        fig = self.plot()
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png")
        pyplot.close(fig)
        img_buf.seek(0)
        return img_buf, "image/png"

    def fits_data(self):
        with fits.open(self.urls[self.IMAGE_KEY], memmap=False) as hdul:
            for hdu in hdul:
                data = getattr(hdu, "data", None)
                if data is None:
                    continue
                if getattr(data, "ndim", 0) < 2:
                    continue
                data = np.squeeze(data)
                if data.ndim == 2:
                    return data
        raise ValueError(
            f"No 2D image data found in FITS file for key {self.IMAGE_KEY}"
        )

    def plot(self):
        image_data = self.fits_data()
        finite = np.isfinite(image_data)
        if finite.any():
            vmin, vmax = np.nanpercentile(image_data, (1, 99))
        else:
            vmin, vmax = None, None

        fig, ax = pyplot.subplots()
        ax.imshow(
            image_data,
            origin="lower",
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            interpolation="nearest",
        )
        ax.set_axis_off()
        fig.tight_layout(pad=0)
        return fig


class ScienceImageLocation(ImageLocation):
    IMAGE_KEY = "Science"


class TemplateImageLocation(ImageLocation):
    IMAGE_KEY = "Template"


class DifferenceImageLocation(ImageLocation):
    IMAGE_KEY = "Difference"


class JSONLocation(Location):
    GLYPHS = (
        ("white", "circle"),
        ("red", "square"),
    )

    def as_file(self):
        d = self.generate()
        str_buf = io.StringIO()
        str_buf.write(d)
        str_buf.seek(0)
        return str_buf, "application/json"

    def generate(self, labels="Lightcurve", glyphs=GLYPHS):
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


class LSSTSubjectGenerator(object):
    DEFAULT_MEDIA_GENERATORS = [
        ScienceImageLocation,
        TemplateImageLocation,
        DifferenceImageLocation,
    ]

    def __init__(
        self,
        obj_ids,
        media_generators=DEFAULT_MEDIA_GENERATORS,
        lasair=None,
        lasair_token=None,
    ):
        if lasair is None:
            lasair = lasair_client(lasair_token)
        self.lasair = lasair
        self.obj_ids = iter(obj_ids)
        self.obj_image_urls = None
        self.media_generators = media_generators

    def generate(self, obj):
        locations = [g(obj).as_file() for g in self.media_generators]
        subject = Subject()

        for loc_data, mime_type in locations:
            subject.add_location(loc_data, manual_mimetype=mime_type)

        return subject

    def __iter__(self):
        return self

    def __next__(self):
        if self.obj_image_urls is not None:
            try:
                next_urls = next(self.obj_image_urls)
            except StopIteration:
                self.obj_image_urls = iter(
                    self.lasair.object(next(self.obj_ids))["lasairData"]["imageUrls"]
                )
                next_urls = next(self.obj_image_urls)
        else:
            self.obj_image_urls = iter(
                self.lasair.object(
                    next(self.obj_ids),
                    lasair_added=True,
                )[
                    "lasairData"
                ]["imageUrls"],
            )
            next_urls = next(self.obj_image_urls)

        return self.generate(next_urls)
