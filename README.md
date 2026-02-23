# Zooniverse LSST Subject Generator

This module allows creation of Zooniverse subjects using LSST data from Lasair. 

## Installation

```shell
pip install zooniverse-lsst
```

## Usage

You will need both a Zooniverse account and a Lasair API key. See [demo.ipynb](demo.ipynb) for a worked example. The short version:

```python
from zooniverse_lsst.generator import LSSTSubjectGenerator, TripletImageLocation, JSONLocation

lasair_results = ... # Perform a query using the Lasair API client
object_ids = [row['objectId'] for row in lasair_results]

subjects = []
for _subject_index_, subject in enumerate(LSSTSubjectGenerator(objectIds, lasair=L, media_generators=[TripletImageLocation, JSONLocation]), start=1):
    subject.save() # Subjects are generated but still need to be saved to upload media
    subjects.append(subject)

subject_set.add(subjects) # Add subjects to a subject set using the panoptes_client
```

The `zooniverse_lsst.generator` module defines several media generator classes: `JSONLocation`, `TripletImageLocation`, `ScienceImageLocation`, `TemplateImageLocation`, and `DifferenceImageLocation`. `JSONLocation` will produce a JSON lightcurve, while the image generators will produce PNG images. You can mix and match whichever media generators you want for your subjects, or create your own subclasses to customise formatting.