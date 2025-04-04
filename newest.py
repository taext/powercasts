import json
import re
import sys

def extract_media_urls(json_file):
    """
    Extract MP3/MP4 URLs from a JSON file containing RSS content.

    Args:
        json_file (str): Path to the JSON file

    Returns:
        list: List of extracted media URLs
    """
    # Load JSON data
    with open(json_file) as infile:
        rss_dict = json.load(infile)

    # Compile regex pattern for efficiency (only needs to be done once)
    url_pattern = re.compile(r'\"(http\S+?\.(?:mp3|mp4))[\"\?]', re.IGNORECASE)

    # Extract URLs
    media_urls = []
    for content in rss_dict.values():
        match = url_pattern.search(content)
        if match:
            media_urls.append(match.group(1))  # Extract the actual URL from the match group

    return media_urls

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <json_file>")
        sys.exit(1)

    # Extract and print the media URLs
    media_urls = extract_media_urls(sys.argv[1])

    if media_urls:
#        print(f"Found {len(media_urls)} media URLs:")
        for url in media_urls:
            print(url)
    else:
        print("No media URLs found in the JSON file.")
