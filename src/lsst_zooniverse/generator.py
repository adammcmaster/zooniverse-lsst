"""Helpers for generating Zooniverse subject media from Lasair sources."""

import json
import io

from collections import defaultdict

from astropy.io import fits

from itertools import cycle

from matplotlib import pyplot
import numpy as np

from panoptes_client import Subject
from lasair import lasair_client

from .lists import is_list_like


class Location(object):
    """Base location wrapper for media that can be uploaded to a subject."""

    def __init__(self, urls, photometry):
        """Store source URLs or payload references used by subclasses."""
        self.urls = urls
        self.photometry = photometry

    def as_file(self):
        """Return a file-like object and MIME type tuple for upload."""
        raise NotImplementedError


class ImageLocation(Location):
    """Base class for image-like locations rendered from FITS data."""

    def as_file(self):
        """Render the image plot to a PNG file-like buffer."""
        fig = self.plot()
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png")
        pyplot.close(fig)
        img_buf.seek(0)
        return img_buf, "image/png"

    def fits_data(self):
        """Extract the first 2D array from the FITS file for this image key."""
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
        """Create a matplotlib figure for this FITS image."""
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
    """Location for the science image FITS asset."""

    IMAGE_KEY = "Science"


class TemplateImageLocation(ImageLocation):
    """Location for the template image FITS asset."""

    IMAGE_KEY = "Template"


class DifferenceImageLocation(ImageLocation):
    """Location for the difference image FITS asset."""

    IMAGE_KEY = "Difference"


class TripletImageLocation(ImageLocation):
    """Render science, template, and difference images side by side."""

    IMAGE_LOCATIONS = (
        ScienceImageLocation,
        TemplateImageLocation,
        DifferenceImageLocation,
    )

    def plot(self):
        """Create a 1x3 figure containing the configured image locations."""
        fig, axes = pyplot.subplots(1, len(self.IMAGE_LOCATIONS))
        if not is_list_like(axes):
            axes = [axes]

        for ax, location_class in zip(axes, self.IMAGE_LOCATIONS):
            image_data = location_class(self.urls, self.photometry).fits_data()
            finite = np.isfinite(image_data)
            if finite.any():
                vmin, vmax = np.nanpercentile(image_data, (1, 99))
            else:
                vmin, vmax = None, None

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


class JSONLocation(Location):
    """Base class for JSON media payload locations."""

    GLYPHS = (
        ("white", "circle"),
        ("red", "square"),
    )

    def as_file(self):
        """Serialize generated JSON payload to a text buffer."""
        d = self.generate()
        str_buf = io.StringIO()
        str_buf.write(d)
        str_buf.seek(0)
        return str_buf, "application/json"

    def generate(self, labels="Lightcurve", glyphs=GLYPHS):
        """Build serialized light curve JSON for one or more series."""
        lcs = defaultdict(lambda: defaultdict(list))

        for p in self.photometry:
            lcs[p["band"]]["midpointMjdTai"].append(p["midpointMjdTai"])
            lcs[p["band"]]["psfFlux"].append(p["psfFlux"])
            lcs[p["band"]]["psfFluxErr"].append(p["psfFluxErr"])

        lcs = list(lcs.values())

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
    """Iterator that yields Panoptes subjects for LSST detections."""

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
        """Initialize the generator with object IDs and media generators."""
        if lasair is None:
            lasair = lasair_client(lasair_token)
        self.lasair = lasair
        self.obj_ids = iter(obj_ids)
        self.obj_image_urls = None
        self.obj_photometry = None
        self.current_obj = None
        self.media_generators = media_generators

    def generate(self, urls, photometry):
        """Build a subject for a single Lasair image URL payload."""
        locations = [g(urls, photometry).as_file() for g in self.media_generators]
        subject = Subject()

        for loc_data, mime_type in locations:
            subject.add_location(loc_data, manual_mimetype=mime_type)

        return subject

    def __iter__(self):
        """Return this generator as an iterator."""
        return self

    def _parse_obj(self, obj_id):
        self.current_obj = self.lasair.object(obj_id, lasair_added=True)
        self.obj_image_urls = iter(self.current_obj["lasairData"]["imageUrls"])

        self.obj_photometry = defaultdict(list)
        for s in self.current_obj["diaSourcesList"]:
            self.obj_photometry[s["diaSourceId"]].append(s)

    def __next__(self):
        """Fetch the next image URL group and build a subject."""
        if self.obj_image_urls is not None:
            try:
                next_urls = next(self.obj_image_urls)
                next_photometry = self.obj_photometry[next_urls["diaSourceId"]]
            except StopIteration:
                self._parse_obj(next(self.obj_ids))
                next_urls = next(self.obj_image_urls)
                next_photometry = self.obj_photometry[next_urls["diaSourceId"]]
        else:
            self._parse_obj(next(self.obj_ids))
            next_urls = next(self.obj_image_urls)
            next_photometry = self.obj_photometry[next_urls["diaSourceId"]]

        return self.generate(next_urls, next_photometry)
