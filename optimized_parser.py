#!/usr/bin/env python
import re
import json
import sys
import time
import asyncio
import aiohttp
from pathlib import Path
from tqdm.asyncio import tqdm_asyncio
import multiprocessing
from functools import partial
from concurrent.futures import ProcessPoolExecutor


def parse_opml_file(file_path):
    """Parse OPML file incrementally to extract feed names and URLs."""
    feed_info = []

    # Compile regex patterns once
    text_pattern = re.compile(r'text="([^"]+)"')
    url_pattern = re.compile(r'xmlUrl="([^"]+)"')

    # Parse file line by line
    with open(file_path, 'r') as f:
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

    return feed_info


# Precompile regex pattern for better performance
MEDIA_URL_PATTERN = re.compile(r'"(http\S+?\.(?:mp3|mp4))["?]', re.IGNORECASE)


def extract_media_urls(content):
    """Extract media URLs using regex - can be run in a separate process."""
    if not content:
        return set()
    return set(MEDIA_URL_PATTERN.findall(content))


async def fetch_feed(session, name, url, semaphore):
    """Fetch a single feed asynchronously."""
    async with semaphore:  # Limit concurrent requests
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'
            }

            # Set timeouts and retry policy
            timeout = aiohttp.ClientTimeout(total=15)

            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        'name': name,
                        'url': url,
                        'content': None,
                        'media_urls': set(),
                        'success': False,
                        'error': f"HTTP error: {response.status}"
                    }

                content = await response.text()
                return {
                    'name': name,
                    'url': url,
                    'content': content,
                    'success': True
                }

        except Exception as e:
            return {
                'name': name,
                'url': url,
                'content': None,
                'media_urls': set(),
                'success': False,
                'error': str(e)
            }


async def process_feeds(feed_info, max_concurrent_requests, process_pool_size):
    """Process all feeds asynchronously with a process pool for regex extraction."""
    # Limit concurrent HTTP requests to avoid overwhelming servers
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    # Process pool for CPU-bound regex operations
    process_pool = ProcessPoolExecutor(max_workers=process_pool_size)

    # Connection pooling with aiohttp session
    connector = aiohttp.TCPConnector(limit=max_concurrent_requests, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create tasks for all feeds
        tasks = [
            fetch_feed(session, name, url, semaphore)
            for name, url in feed_info
        ]

        # Use tqdm to show progress
        results = await tqdm_asyncio.gather(*tasks, desc="Fetching feeds")

        # Process results in batches to extract media URLs using process pool
        final_results = []

        # Process in smaller batches to manage memory better
        batch_size = 20
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]

            # Extract media URLs in parallel for successful fetches
            futures = []
            for result in batch:
                if result['success']:
                    future = process_pool.submit(extract_media_urls, result['content'])
                    futures.append((result, future))

            # Wait for this batch to complete
            for result, future in futures:
                media_urls = future.result()
                result['media_urls'] = media_urls
                final_results.append(result)

            # Add failed results
            for result in batch:
                if not result['success']:
                    result['media_urls'] = set()
                    final_results.append(result)

    # Shutdown process pool
    process_pool.shutdown()

    return final_results


def write_results(results, txt_path, json_path=None):
    """Write results to output files efficiently."""
    # Write media URLs to txt file
    with open(txt_path, 'w') as output_file:
        for result in results:
            if result['success']:
                for media_url in result['media_urls']:
                    output_file.write(f"{media_url}\n")

    # Optionally write RSS content to JSON file
    if json_path:
        # Create streamable JSON to minimize memory usage
        with open(json_path, 'w') as outfile:
            outfile.write('{')
            first = True
            for result in results:
                if result['success']:
                    if not first:
                        outfile.write(',')
                    else:
                        first = False
                    # Manually escape JSON to avoid loading entire structure in memory
                    json_name = json.dumps(result['name'])
                    json_content = json.dumps(result['content'])
                    outfile.write(f'{json_name}:{json_content}')
            outfile.write('}')


async def main_async(opml_filename, max_concurrent_requests=20):
    file_path = Path(opml_filename)
    base_name = file_path.stem

    # Output paths
    txt_path = file_path.with_suffix('.txt')
    json_path = file_path.with_suffix('.json')

    # Get feed information (still synchronous but fast)
    feed_info = parse_opml_file(file_path)
    print(f"Found {len(feed_info)} feeds in {opml_filename}")

    # Calculate optimal process pool size (for CPU-bound regex operations)
    cpu_count = multiprocessing.cpu_count()
    process_pool_size = max(1, cpu_count - 1)  # Leave one CPU free for system

    # Process feeds using async with process pool for regex
    start_time = time.time()
    results = await process_feeds(feed_info, max_concurrent_requests, process_pool_size)
    end_time = time.time()

    # Write results to files
    write_results(results, txt_path, json_path)

    # Print summary
    successful = sum(1 for r in results if r['success'])
    print(f"\nSummary: Successfully processed {successful} of {len(feed_info)} feeds")
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    print(f"Media URLs saved to: {txt_path}")
    print(f"RSS content saved to: {json_path}")


def main(opml_filename, max_concurrent_requests=20):
    """Entry point that runs the async main function."""
    asyncio.run(main_async(opml_filename, max_concurrent_requests))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python opml_parser.py <opml_file> [max_concurrent_requests]")
        sys.exit(1)

    max_concurrent = 20  # Default number of concurrent requests
    if len(sys.argv) >= 3:
        try:
            max_concurrent = int(sys.argv[2])
        except ValueError:
            print(f"Invalid value for max_concurrent_requests: {sys.argv[2]}. Using default: 20")

    main(sys.argv[1], max_concurrent)
