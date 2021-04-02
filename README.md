## What is DataAnnotator?

DataAnnotator is an online annotation tool that can be used to transform unstructured documents into structured formats for NLP and ML tasks, such as named-entity recognition. DataAnnotator learns as you annotate in order to predict and suggest complex annotations. DataAnnotator also provides integrated access to existing and custom ontologies, enabling the prediction and suggestion of ontology mappings based on the text you're annotating.

## Usage

A full-feature version of DataAnnotator is available via local installation.

### Local Server

#### Docker

Run `docker run -d -p 80:8000 juezhao/DataAnnotator` and visit <a href="http://127.0.0.1/">http://127.0.0.1/</a>.

#### Manual Installation

1. Clone or download the repository.

2. Run `python setup.py` using 64-bit Python3.

3. Visit <a href="http://127.0.0.1/">http://127.0.0.1/</a>.

For futher sessions, the local server can be started directly by running `python manage.py runserver 0.0.0.0:80`.

## Features

- Ability to navigate between and annotate multiple documents in a single session.
- Predictive annotation suggestions (incl. attributes) using underlying active learning and sequence-to-sequence models.
- Integrated access to pre-loaded and user-defined ontologies, enabling predictive mappings and direct querying.
- Built-in configuration file creator.
- Built-in synthetic data generator and custom model trainer (local version only due to high computational expense).
- Dynamic attribute display.
- Any number of overlaying annotations, enabling the capture of complex data.
- Full-feature tool available via local installation and website.
- Dark mode.

## Known Bugs / Issues
- Annotations may be offset when annotating across newlines in CRLF (Windows) text documents. The offset is purely visual; the exported indicies will be correct.
