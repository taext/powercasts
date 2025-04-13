import re
import json
import sys
import time
import asyncio
import aiohttp
from pathlib import Path
from tqdm.asyncio import tqdm_asyncio
import multiprocessing
import os
from functools import partial
from concurrent.futures import ProcessPoolExecutor

CHUNK_SIZE = 50


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

async def write_results_streaming(results_async_gen, txt_path, chunk_dir):
    os.makedirs(chunk_dir, exist_ok=True)
    chunk_index = 0
    current_chunk = {}
    with open(txt_path, 'w') as output_file:
        async for result in results_async_gen:
            if result['success']:
                for media_url in result['media_urls']:
                    output_file.write(f"{media_url}\n")
                current_chunk[result['name']] = result['content']
                if len(current_chunk) >= CHUNK_SIZE:
                    chunk_path = os.path.join(chunk_dir, f"feeds_chunk_{chunk_index:03}.json")
                    with open(chunk_path, 'w') as chunk_file:
                        json.dump(current_chunk, chunk_file)
                    current_chunk.clear()
                    chunk_index += 1
            result['content'] = None
        if current_chunk:
            chunk_path = os.path.join(chunk_dir, f"feeds_chunk_{chunk_index:03}.json")
            with open(chunk_path, 'w') as chunk_file:
                json.dump(current_chunk, chunk_file)

async def combine_json_chunks(chunk_dir, combined_path):
    chunk_files = sorted(Path(chunk_dir).glob("feeds_chunk_*.json"))
    with open(combined_path, 'w') as outfile:
        outfile.write('{')
        first = True
        for chunk_file in chunk_files:
            with open(chunk_file, 'r') as infile:
                chunk_data = json.load(infile)
                for k, v in chunk_data.items():
                    if not first:
                        outfile.write(',')
                    else:
                        first = False
                    outfile.write(f"{json.dumps(k)}:{json.dumps(v)}")
        outfile.write('}')

async def main_async(opml_filename, max_concurrent_requests=20):
    file_path = Path(opml_filename)
    base_name = file_path.stem
    txt_path = file_path.with_suffix('.txt')
    chunk_dir = file_path.parent / f"{base_name}_chunks"
    json_path = file_path.with_suffix('.json')

    feed_info = parse_opml_file(file_path)
    print(f"Found {len(feed_info)} feeds in {opml_filename}")
    cpu_count = multiprocessing.cpu_count()
    process_pool_size = max(1, cpu_count - 1)
    start_time = time.time()
    results_async_gen = stream_process_feeds(feed_info, max_concurrent_requests, process_pool_size)
    await write_results_streaming(results_async_gen, txt_path, chunk_dir)
    await combine_json_chunks(chunk_dir, json_path)
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
