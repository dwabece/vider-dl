#!/usr/bin/env python3
import os
import re
import sys
import asyncio
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import click
from tqdm import tqdm

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-US,en;q=0.9,pl-PL;q=0.8,pl;q=0.7",
    "cache-control": "max-age=0",
    "referer": "https://vider.info/",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "sec-fetch-dest": "video",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "cross-site",
    "Referer": "https://vider.pl/",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

async def get_output_path(dir_path, file_name):
    if not dir_path:
        dir_path = os.getcwd()
    return os.path.join(dir_path, file_name)

async def solve_captcha_from_img(current_url, session):
    click.echo("-" * 80)
    click.echo("You've been blocked, please solve the captcha.")
    click.echo("The captcha is located in the captcha_image.png file.")
    click.echo("-" * 80)
    solved_captcha = input("Captcha text: ")

    form_payload = {
        "captcha": solved_captcha,
    }
    async with session.post(current_url, headers=HEADERS, data=form_payload) as response:
        content = await response.read()
    return BeautifulSoup(content, "html.parser")

async def get_video_url(entry_url, session):
    video_id = entry_url.split("+")[1]
    current_url = f"https://vider.pl/embed/video/{video_id}"

    async with session.get(current_url, headers=HEADERS) as response:
        content = await response.read()
    soup = BeautifulSoup(content, "html.parser")

    while True:
        if not await lookup_for_captcha(soup, session):
            break
        soup = await solve_captcha_from_img(current_url, session)

    title_tag = soup.find(attrs={"name": "title"})
    if not title_tag:
        raise ValueError("Video 'title' not found")
    title = title_tag["content"]

    video_player_tag = soup.find(id="video_player")
    if not video_player_tag or "data-file-id" not in video_player_tag.attrs:
        raise ValueError("Video 'id' not found")
    video_id = video_player_tag["data-file-id"]

    return title, f"https://stream.vider.info/video/{video_id}/v.mp4"

async def download_captcha(captcha_url, session):
    async with session.get(captcha_url, headers=HEADERS) as response:
        content = await response.read()
    async with aiofiles.open("captcha_image.png", "wb") as file:
        await file.write(content)

async def lookup_for_captcha(body, session):
    captcha = body.find("input", attrs={"name": "captcha", "placeholder": "Wpisz kod z obrazka..."})
    if captcha:
        captcha_img = body.find("img", src=lambda x: x and "/streaming/ca-pt" in x)
        captcha_url = f"https://vider.pl{captcha_img['src']}"
        await download_captcha(captcha_url, session)
        return True
    return False

def title_to_filename(title):
    return re.sub(r"[^A-Za-z0-9 _]+", "-", title).strip()

async def fetch_chunk(session, url, start, end, output_file, pbar):
    headers = {**HEADERS, "range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as response:
        content = await response.read()
        async with aiofiles.open(output_file, "r+b") as f:
            await f.seek(start)
            await f.write(content)
        pbar.update(len(content))

async def download(title, url, output_dir=None, file_name=None):
    download_headers = {
        "cache-control": "no-cache",
        "pragma": "no-cache",
    }
    headers = {**HEADERS, **download_headers}

    fname = file_name or f"{title_to_filename(title)}.mp4"
    out_path = await get_output_path(output_dir, fname)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            total_length = int(response.headers.get("content-length", 0))

        chunk_size = 1024 * 1024
        tasks = []
        pbar = tqdm(total=total_length, unit='B', unit_scale=True, desc=title)

        async with aiofiles.open(out_path, "wb") as f:
            await f.truncate(total_length)

        for start in range(0, total_length, chunk_size):
            end = min(start + chunk_size - 1, total_length - 1)
            task = asyncio.create_task(fetch_chunk(session, url, start, end, out_path, pbar))
            tasks.append(task)

        await asyncio.gather(*tasks)
        pbar.close()

    print(f"\nDownloaded {title} to {out_path}")

@click.command()
@click.argument("video_url")
@click.option(
    "--output-dir",
    default=None,
    help="The directory where the downloaded file will be saved. Default is the current directory.",
)
@click.option(
    "--output-filename",
    default=None,
    help="Overwrite target filename. Default is the one fetched from website.",
)
def download_video(video_url, output_dir, output_filename):
    """
    CLI tool to download a from vider.info.

    Arguments:
    video_url - The URL of the video to download.
    """
    click.echo(f"Downloading video from: {video_url}")
    click.echo(f"Saving under file name: {output_filename}")
    click.echo(f"Saving to directory: {output_dir}")

    async def main():
        async with aiohttp.ClientSession() as session:
            try:
                title, link = await get_video_url(video_url, session)
                await download(title, link, output_dir, output_filename)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)

    asyncio.run(main())

if __name__ == "__main__":
    download_video()