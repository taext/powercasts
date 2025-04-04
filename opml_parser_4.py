#!/usr/bin/env python
import re
import requests
import json
import sys
from pathlib import Path
from tqdm import tqdm
import concurrent.futures
from functools import partial


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


def process_feed(name, url, output_file=None):
    """Process a single feed and extract media URLs."""
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

        # Return both RSS content and found URLs
        return {
            'name': name,
            'url': url,
            'content': content,
            'media_urls': media_urls,
            'success': True
        }

    except Exception as e:
        print(f"Failed to process {url}: {e}")
        return {
            'name': name,
            'url': url,
            'content': None,
            'media_urls': set(),
            'success': False,
            'error': str(e)
        }


def write_results(results, txt_path, json_path=None):
    """Write results to output files."""
    # Write media URLs to txt file
    with open(txt_path, 'w') as output_file:
        for result in results:
            if result['success']:
                for media_url in result['media_urls']:
                    output_file.write(f"{media_url}\n")

    # Optionally write RSS content to JSON file
    if json_path:
        rss_dict = {result['name']: result['content'] for result in results if result['success']}
        with open(json_path, 'w') as outfile:
            json.dump(rss_dict, outfile)


def main(opml_filename, max_workers=10):
    file_path = Path(opml_filename)
    base_name = file_path.stem

    # Output paths
    txt_path = file_path.with_suffix('.txt')
    json_path = file_path.with_suffix('.json')

    # Get feed information
    feed_info = parse_opml_file(file_path)

    # Process feeds in parallel
    results = []

    with tqdm(total=len(feed_info), desc="Processing feeds") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Start the processing tasks
            future_to_feed = {
                executor.submit(process_feed, name, url): (name, url)
                for name, url in feed_info
            }

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_feed):
                name, url = future_to_feed[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Update progress bar
                    if result['success']:
                        pbar.write(f'Downloaded {url}')
                    else:
                        pbar.write(f'Failed: {name} - {result["error"]}')
                except Exception as e:
                    pbar.write(f'Exception for {name}: {e}')
                    results.append({
                        'name': name,
                        'url': url,
                        'content': None,
                        'media_urls': set(),
                        'success': False,
                        'error': str(e)
                    })

                pbar.update(1)

    # Write results to files
    write_results(results, txt_path, json_path)

    # Print summary
    successful = sum(1 for r in results if r['success'])
    print(f"\nSummary: Successfully processed {successful} of {len(feed_info)} feeds")
    print(f"Media URLs saved to: {txt_path}")
    print(f"RSS content saved to: {json_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python opml_parser.py <opml_file> [max_workers]")
        sys.exit(1)

    max_workers = 10  # Default number of workers
    if len(sys.argv) >= 3:
        try:
            max_workers = int(sys.argv[2])
        except ValueError:
            print(f"Invalid value for max_workers: {sys.argv[2]}. Using default: 10")

    main(sys.argv[1], max_workers)
