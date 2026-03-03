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


# Yield-based OPML parser for memory efficiency
def parse_opml_file(file_path):
    text_pattern = re.compile(r'text="([^"]+)"')
    url_pattern = re.compile(r'xmlUrl="([^"]+)"')
    with open(file_path, 'r') as f:
        found_first_text = False
        for line in f:
            if 'xmlUrl=' in line:
                name_match = text_pattern.search(line)
                url_match = url_pattern.search(line)
                if name_match and url_match:
                    if not found_first_text:
                        found_first_text = True
                        continue
                    yield (name_match.group(1), url_match.group(1))


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


async def async_generator(iterable):
    for item in iterable:
        yield item


async def handle_results(results, process_pool, txt_file, json_file, first_json):
    futures = [(r, process_pool.submit(extract_media_urls, r['content'])) for r in results if r['success']]
    for result, future in futures:
        result['media_urls'] = future.result()
        for url in result['media_urls']:
            txt_file.write(f"{url}\n")
        if json_file:
            if not first_json[0]:
                json_file.write(',')
            else:
                first_json[0] = False
            json_name = json.dumps(result['name'])
            json_content = json.dumps(result['content'])
            json_file.write(f'{json_name}:{json_content}')
        result['content'] = None  # free memory

    for result in results:
        if not result['success']:
            if json_file and not first_json[0]:
                json_file.write(',')
            elif json_file:
                first_json[0] = False
            if json_file:
                json_name = json.dumps(result['name'])
                json_file.write(f'{json_name}:null')


async def process_feeds(feed_info_iter, max_concurrent_requests, process_pool_size, txt_path, json_path, batch_size=20):
    semaphore = asyncio.Semaphore(max_concurrent_requests)
    connector = aiohttp.TCPConnector(limit=max_concurrent_requests, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=20)
    process_pool = ProcessPoolExecutor(max_workers=process_pool_size)

    with open(txt_path, 'w') as txt_file, open(json_path, 'w') if json_path else open('/dev/null', 'w') as json_file:
        if json_path:
            json_file.write('{')
        first_json = [True]

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            batch = []
            async for name, url in async_generator(feed_info_iter):
                batch.append(fetch_feed(session, name, url, semaphore))
                if len(batch) >= batch_size:
                    results = await asyncio.gather(*batch)
                    await handle_results(results, process_pool, txt_file, json_file if json_path else None, first_json)
                    batch = []
            if batch:
                results = await asyncio.gather(*batch)
                await handle_results(results, process_pool, txt_file, json_file if json_path else None, first_json)

        if json_path:
            json_file.write('}')

    process_pool.shutdown()


def get_feed_count(file_path):
    return sum(1 for _ in parse_opml_file(file_path))


async def main_async(opml_filename, max_concurrent_requests=20):
    file_path = Path(opml_filename)
    base_name = file_path.stem
    txt_path = file_path.with_suffix('.txt')
    json_path = file_path.with_suffix('.json')

    total_feeds = get_feed_count(file_path)
    print(f"Found {total_feeds} feeds in {opml_filename}")
    cpu_count = multiprocessing.cpu_count()
    process_pool_size = max(1, cpu_count - 1)

    start_time = time.time()
    await process_feeds(
        parse_opml_file(file_path),
        max_concurrent_requests,
        process_pool_size,
        txt_path,
        json_path
    )
    end_time = time.time()

    print(f"\nSummary: Processed {total_feeds} feeds")
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    print(f"Media URLs saved to: {txt_path}")
    print(f"RSS content saved to: {json_path}")


def main(opml_filename, max_concurrent_requests=20):
    asyncio.run(main_async(opml_filename, max_concurrent_requests))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python memory_efficient_parser.py <opml_file> [max_concurrent_requests]")
        sys.exit(1)

    max_concurrent = 20
    if len(sys.argv) >= 3:
        try:
            max_concurrent = int(sys.argv[2])
        except ValueError:
            print(f"Invalid value for max_concurrent_requests: {sys.argv[2]}. Using default: 20")

    main(sys.argv[1], max_concurrent)
