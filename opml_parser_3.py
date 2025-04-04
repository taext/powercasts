#!/usr/bin/env python
import re
import requests
import json
import sys
from pathlib import Path
from tqdm import tqdm


def parse_opml_file(file_path):
    """Parse OPML file incrementally to extract feed names and URLs."""
    feed_info = []

    # Regex patterns
    text_pattern = re.compile(r'text="([^"]+)"')
    url_pattern = re.compile(r'xmlUrl="([^"]+)"')

    # Parse file line by line instead of loading it all at once
    with open(file_path, 'r') as f:
        # Skip the first line with text attribute (OPML header)
        found_first_text = False

        for line in f:
            if 'xmlUrl=' in line:
                name_match = text_pattern.search(line)
                url_match = url_pattern.search(line)

                if name_match and url_match:
                    name = name_match.group(1)
                    url = url_match.group(1)

                    if not found_first_text:
                        found_first_text = True
                        continue

                    feed_info.append((name, url))
                    print(f"{name}: {url}")

    return feed_info


def process_feed(name, url, output_file):
    """Process a single feed and extract media URLs directly to file."""
    try:
        r = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'
            },
            timeout=15
        )
        content = r.text

        # Extract media URLs directly using regex
        media_urls = set(re.findall(r'"(http\S+?\.(?:mp3|mp4))["?]', content, re.IGNORECASE))

        # Write URLs directly to file
        for media_url in media_urls:
            output_file.write(f"{media_url}\n")

        # Return found URLs for optional JSON storage
        return media_urls

    except Exception as e:
        print(f"Failed to process {url}: {e}")
        return set()


def main(opml_filename):
    file_path = Path(opml_filename)
    base_name = file_path.stem

    # Get feed information
    feed_info = parse_opml_file(file_path)

    # Optional: If you still need the JSON output of RSS content
    # Modify this section based on your requirements
    json_path = file_path.with_suffix('.json')
    rss_dict = {}

    # Open output file for writing URLs
    with open(file_path.with_suffix('.txt'), 'w') as output_file:
        # Process each feed and write URLs directly to file
        for name, url in tqdm(feed_info):
            try:
                media_urls = process_feed(name, url, output_file)

                # Optional: Still store RSS content if needed
                # Remove this if you don't need the JSON output
                r = requests.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'
                    },
                    timeout=15
                )
                rss_dict[name] = r.text
                tqdm.write(f'Downloaded {url}\n')

            except Exception as e:
                print(f"Failed to process {name} ({url}): {e}")

    # Optional: Write JSON if you still need it
    # Remove this if you don't need the JSON output
    with open(json_path, 'w') as outfile:
        json.dump(rss_dict, outfile)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python opml_parser.py <opml_file>")
        sys.exit(1)

    main(sys.argv[1])
