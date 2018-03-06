# PowerCasts v1.0

<br>

### How to Use

1. Download files to a USB drive 

2. Export OPML XML file from PocketCasts mobile settings

3. Parse the file as described in Setup

<br>

### Syntax

use `GetRandomPodcast.ps1` to play a random podcast

    pwsh GetRandomPodcast.ps1

optionally define which browser to use

    pwsh GetRandomPodcast.ps1 -b vivaldi

or download only

    pwsh GetRandomPodcast.ps1 -d

or MP3 file count to download

    pwsh GetRandomPodcast.ps1 -c 3

or alternative MP3 URL list file

    pwsh GetRandomPodcast.ps1 -f myUrls.txt

<br>

### Setup

Parse an exported PocketCasts OPML XML file:

    python opml_parser_2.py podcasts_opml.xml

to output `podcasts_opml.json` full-text RSS dictionary and `podcasts_opml.txt` list of every MP3 URL.

<br>

Parse `podcasts_opml.json` with `newest.py`:

    python newest.py podcasts_opml.json

to get `newest.txt`, a list of the latest podcast URLs.

