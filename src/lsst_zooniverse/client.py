import logging
import time

from requests.exceptions import ProxyError, JSONDecodeError, ConnectionError
from panoptes_client.panoptes import PanoptesAPIException

# from panoptes_client import *

MAX_ATTEMPTS = 5

# for attempt in range(MAX_ATTEMPTS):
#     try:
#         if (
#             settings.ZOONIVERSE_CLIENT_ID
#             and settings.ZOONIVERSE_CLIENT_SECRET
#             and not Panoptes.client().logged_in
#         ):
#             Panoptes.connect(
#                 client_id=settings.ZOONIVERSE_CLIENT_ID,
#                 client_secret=settings.ZOONIVERSE_CLIENT_SECRET,
#             )

#         project = Project(settings.ZOONIVERSE_PROJECT_ID)
#         workflow = Workflow(settings.ZOONIVERSE_WORKFLOW_ID)
#         break
#     except (PanoptesAPIException, JSONDecodeError, ProxyError, ConnectionError):
#         if attempt == MAX_ATTEMPTS - 1:
#             raise
#         time.sleep(attempt * 10)


def network_retry(f, *args, **kwargs):
    final_e = None
    for _ in range(10):
        try:
            return f(*args, **kwargs)
        except (ProxyError, ConnectionError, PanoptesAPIException) as e:
            final_e = e
            time.sleep(5)
    if final_e is not None:
        raise final_e


# Copied from my PR linked below, to avoid incorrect MIME type for JSON files
# https://github.com/zooniverse/panoptes-python-client/pull/233

from panoptes_client.subject import (
    _OLD_STR_TYPES,
    Subject as UpstreamSubject,
    UnknownMediaException,
)

try:
    import magic

    MEDIA_TYPE_DETECTION = "magic"
except ImportError:
    import pkg_resources

    try:
        pkg_resources.require("python-magic")
        logging.getLogger("panoptes_client").warn(
            "Broken libmagic installation detected. The python-magic module is"
            " installed but can't be imported. Please check that both "
            "python-magic and the libmagic shared library are installed "
            "correctly. Uploading media other than images may not work."
        )
    except pkg_resources.DistributionNotFound:
        pass
    import imghdr

    MEDIA_TYPE_DETECTION = "imghdr"


class Subject(UpstreamSubject):
    def add_location(self, location, media_type=None):
        """
        Add a media location to this subject.

        - **location** can be an open :py:class:`file` object, a path to a
          local file, or a :py:class:`dict` containing MIME types and URLs for
          remote media.
        - **media_type** is a string specifying the MIME type of the file. Ignored
          if location is a dict. Defaults to None, in which case the type is
          auto-detected.

        Examples::

            subject.add_location(my_file)
            subject.add_location('/data/image.jpg')
            subject.add_location({'image/png': 'https://example.com/image.png'})
        """
        if type(location) is dict:
            self.locations.append(location)
            self._media_files.append(None)
            self.modified_attributes.add("locations")
            return
        elif type(location) in (str,) + _OLD_STR_TYPES:
            f = open(location, "rb")
        else:
            f = location

        try:
            media_data = f.read()
            if not media_type:
                if MEDIA_TYPE_DETECTION == "magic":
                    media_type = magic.from_buffer(media_data, mime=True)
                else:
                    media_type = imghdr.what(None, media_data)
                    if not media_type:
                        raise UnknownMediaException(
                            "Could not detect file type. Please try installing "
                            "libmagic: https://panoptes-python-client.readthedocs."
                            "io/en/latest/user_guide.html#uploading-non-image-"
                            "media-types"
                        )
                    media_type = "image/{}".format(media_type)
            self.locations.append(media_type)
            self._media_files.append(media_data)
            self.modified_attributes.add("locations")
        finally:
            f.close()
