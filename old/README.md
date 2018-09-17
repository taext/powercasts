# PowerCasts User Guide v1.6
March 7th 2018 by d@v1d.dk

(Linux only)

<br>

### How to Use

1. Download files to a USB drive 

2. Export OPML XML file from PocketCasts mobile settings

3. Parse the file as described in Setup

4. Change the GetRandomPodcast.ps1 $pathToMp3File default value to .txt file produced above

<br>

### Syntax

To play a random podcast, simply run the PowerShell script:

    pwsh GetRandomPodcast.ps1

or use any of the following options in combination.

<br>

### Options

define which browser to use:

    pwsh GetRandomPodcast.ps1 -b vivaldi

download only:

    pwsh GetRandomPodcast.ps1 -d

how many MP3s to get:

    pwsh GetRandomPodcast.ps1 -c 3   # or -n

alternative MP3 URL list file:

    pwsh GetRandomPodcast.ps1 -f myUrls.txt

<br>

### Setup

Parse an exported PocketCasts OPML XML file:

    python opml_parser_2.py podcasts_opml.xml

to output `podcasts_opml.json` full-text RSS dictionary and `podcasts_opml.txt` list of every MP3 URL.

<br>

Parse `podcasts_opml.json` with `newest.py`:

    python newest.py podcasts_opml.json > newest_episodes.txt

to get `newest_episodes.txt`, a list of the latest podcast URLs.

