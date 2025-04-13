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
    feed_info = []
    text_pattern = re.compile(r'text="([^"]+)"')
    url_pattern = re.compile(r'xmlUrl="([^"]+)"')
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

MEDIA_URL_PATTERN = re.compile(r'"(http\S+?\.(?:mp3|mp4))["?]', re.IGNORECASE)

def extract_media_urls(content):
    if not content:
        return set()
    return set(MEDIA_URL_PATTERN.findall(content))

async def fetch_feed(session, name, url, semaphore):
    async with semaphore:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'
            }
            timeout = aiohttp.ClientTimeout(total=15)
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    return {'name': name, 'url': url, 'content': None, 'media_urls': set(), 'success': False, 'error': f"HTTP error: {response.status}"}
                content = await response.text()
                return {'name': name, 'url': url, 'content': content, 'success': True}
        except Exception as e:
            return {'name': name, 'url': url, 'content': None, 'media_urls': set(), 'success': False, 'error': str(e)}

async def stream_process_feeds(feed_info, max_concurrent_requests, process_pool_size):
    semaphore = asyncio.Semaphore(max_concurrent_requests)
    process_pool = ProcessPoolExecutor(max_workers=process_pool_size)
    connector = aiohttp.TCPConnector(limit=max_concurrent_requests, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_feed(session, name, url, semaphore) for name, url in feed_info]
        for future_result in tqdm_asyncio.as_completed(tasks, desc="Fetching feeds"):
            result = await future_result
            if result['success']:
                future = process_pool.submit(extract_media_urls, result['content'])
                result['media_urls'] = future.result()
            else:
                result['media_urls'] = set()
            yield result
    process_pool.shutdown()

async def write_results_streaming(results_async_gen, txt_path, json_path=None):
    with open(txt_path, 'w') as output_file, open(json_path, 'w') if json_path else open(os.devnull, 'w') as json_file:
        if json_path:
            json_file.write('{')
        first = True
        async for result in results_async_gen:
            if result['success']:
                for media_url in result['media_urls']:
                    output_file.write(f"{media_url}\n")
                if json_path:
                    if not first:
                        json_file.write(',')
                    else:
                        first = False
                    json_name = json.dumps(result['name'])
                    json_content = json.dumps(result['content'])
                    json_file.write(f'{json_name}:{json_content}')
                # Drop full content to release memory
                result['content'] = None
        if json_path:
            json_file.write('}')

def write_results(results, txt_path, json_path=None):
    pass  # Not used anymore

async def main_async(opml_filename, max_concurrent_requests=20):
    file_path = Path(opml_filename)
    base_name = file_path.stem
    txt_path = file_path.with_suffix('.txt')
    json_path = file_path.with_suffix('.json')
    feed_info = parse_opml_file(file_path)
    print(f"Found {len(feed_info)} feeds in {opml_filename}")
    cpu_count = multiprocessing.cpu_count()
    process_pool_size = max(1, cpu_count - 1)
    start_time = time.time()
    results_async_gen = stream_process_feeds(feed_info, max_concurrent_requests, process_pool_size)
    await write_results_streaming(results_async_gen, txt_path, json_path)
    end_time = time.time()
    print(f"\nSummary: Finished processing {len(feed_info)} feeds")
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    print(f"Media URLs saved to: {txt_path}")
    print(f"RSS content saved to: {json_path}")

def main(opml_filename, max_concurrent_requests=20):
    asyncio.run(main_async(opml_filename, max_concurrent_requests))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python opml_parser.py <opml_file> [max_concurrent_requests]")
        sys.exit(1)
    max_concurrent = 20
    if len(sys.argv) >= 3:
        try:
            max_concurrent = int(sys.argv[2])
        except ValueError:
            print(f"Invalid value for max_concurrent_requests: {sys.argv[2]}. Using default: 20")
    main(sys.argv[1], max_concurrent)
