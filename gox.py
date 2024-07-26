#!/usr/bin/env python3
import asyncio
import os
import re
from typing import Tuple

import aiofiles
import aiohttp
import click
from bs4 import BeautifulSoup
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
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=120)


def get_output_path(dir_path: str, file_name: str) -> str:
    """
    Helper function to get the output path for the downloaded file.

    Args:
        dir_path: directory path where the file will be saved.
        file_name: name of the file.

    Returns:
        The output path for the downloaded file.
    """
    if not dir_path:
        dir_path = os.getcwd()
    return os.path.join(dir_path, file_name)


async def solve_captcha_from_img(
    current_url: str, session: aiohttp.ClientSession
) -> BeautifulSoup:
    """
    Solve the captcha by prompting the user for the captcha text
    and sending a POST request with the solved captcha.

    Args:
        current_url: URL of the current page.
        session: aiohttp ClientSession object.

    Returns:
        The BeautifulSoup object containing website after solving cptcha.
    """
    click.echo("-" * 80)
    click.echo("You've been blocked, please solve the captcha.")
    click.echo("The captcha is located in the captcha_image.png file.")
    click.echo("-" * 80)
    solved_captcha = input("Captcha text: ")

    form_payload = {
        "captcha": solved_captcha,
    }
    async with session.post(
        current_url,
        headers=HEADERS,
        data=form_payload,
        timeout=DEFAULT_TIMEOUT,
    ) as response:
        content = await response.read()
    return BeautifulSoup(content, "html.parser")


async def get_video_url(entry_url: str, session: aiohttp.ClientSession) -> Tuple:
    """
    Get the video title and URL from the given entry URL.

    Args:
        entry_url: URL of the video entry.
        session: aiohttp ClientSession object.

    Returns:
        A tuple containing the video title and URL.
    """
    video_id = entry_url.split("+")[1]
    current_url = f"https://vider.pl/embed/video/{video_id}"

    async with session.get(
        current_url, headers=HEADERS, timeout=DEFAULT_TIMEOUT
    ) as response:
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


async def download_captcha(captcha_url: str, session: aiohttp.ClientSession) -> None:
    """
    Download the captcha image from website and save it as "captcha_image.png".

    Args:
        captcha_url: URL of the captcha image.
        session: aiohttp ClientSession object.

    Returns:
        None
    """
    async with session.get(
        captcha_url, headers=HEADERS, timeout=DEFAULT_TIMEOUT
    ) as response:
        content = await response.read()
    async with aiofiles.open("captcha_image.png", "wb") as file:
        await file.write(content)


async def lookup_for_captcha(
    body: BeautifulSoup, session: aiohttp.ClientSession
) -> bool:
    """
    Look for captcha in the HTML body and download it if found.

    Args:
        body: BeautifulSoup object representing the HTML body.
        session: aiohttp ClientSession object.

    Returns:
        True if captcha is found and downloaded, False otherwise.
    """
    captcha = body.find(
        "input", attrs={"name": "captcha", "placeholder": "Wpisz kod z obrazka..."}
    )
    if captcha:
        captcha_img = body.find("img", src=lambda x: x and "/streaming/ca-pt" in x)
        captcha_url = f"https://vider.pl{captcha_img['src']}"
        await download_captcha(captcha_url, session)
        return True
    return False


def title_to_filename(title: str) -> str:
    """
    Convert a title to a valid filename by replacing special characters with hyphens.

    Args:
        title: title to convert.

    Returns:
        The converted filename.
    """
    return re.sub(r"[^A-Za-z0-9 _]+", "-", title).strip()


async def fetch_chunk(
    session: aiohttp.ClientSession,
    url: str,
    start: int,
    end: int,
    output_file: str,
    pbar: tqdm,
) -> None:
    """
    Fetch a chunk of data from the given URL and write it to the output file.

    Args:
        session: aiohttp ClientSession object.
        url: URL to fetch the data from.
        start: starting byte position of the chunk.
        end: ending byte position of the chunk.
        output_file: path to the output file.
        pbar: tqdm progress bar.

    Returns:
        None
    """
    headers = {**HEADERS, "range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
        content = await response.read()
        async with aiofiles.open(output_file, "r+b") as f:
            await f.seek(start)
            await f.write(content)
        pbar.update(len(content))


async def download(
    title: str,
    url: str,
    session: aiohttp.ClientSession,
    output_dir: str = None,
    file_name: str = None,
) -> None:
    """
    Download the video from the given url and save it
    to the specified output directory with the specified file name.

    args:
        title: title of the video.
        url: url of the video.
        session: aiohttp clientsession object.
        output_dir: directory where the downloaded file will be saved. default is none.
        file_name: name of the downloaded file. default is none.

    returns:
        none
    """
    download_headers = {
        "cache-control": "no-cache",
        "pragma": "no-cache",
    }
    headers = {**HEADERS, **download_headers}

    fname = file_name or f"{title_to_filename(title)}.mp4"
    out_path = get_output_path(output_dir, fname)

    async with session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
        total_length = int(response.headers.get("content-length", 0))

    chunk_size = 1024 * 1024
    tasks = []
    pbar = tqdm(
        total=total_length, unit="B", unit_scale=True, desc=title, mininterval=0.1
    )

    async with aiofiles.open(out_path, "wb") as f:
        await f.truncate(total_length)

    for start in range(0, total_length, chunk_size):
        end = min(start + chunk_size - 1, total_length - 1)
        task = asyncio.create_task(
            fetch_chunk(session, url, start, end, out_path, pbar)
        )
        tasks.append(task)

    await asyncio.gather(*tasks)
    pbar.close()

    click.echo(f"\nDownloaded {title} to {out_path}")


@click.command()
@click.argument("video_url", required=False)
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
@click.option(
    "--queue-file",
    default=None,
    help="File containing URLs to download. One URL per line. If provided all other arguments are ignored.",
)
def download_video(video_url, output_dir, output_filename, queue_file):
    """
    CLI tool to download a from vider.info.

    Arguments:
    video_url - The URL of the video to download.
    """
    if not video_url and not queue_file:
        click.echo("You must provide either a video URL or a queue file.")
        return

    if video_url:
        click.echo(f"Downloading video from: {video_url}")
    if output_filename:
        click.echo(f"Saving under file name: {output_filename}")
    if output_dir:
        click.echo(f"Saving to directory: {output_dir}")

    async def main():
        queue = []
        if queue_file:
            with open(queue_file, "r") as file:
                queue = [line.strip() for line in file.readlines()]
        else:
            queue.append(video_url)

        async with aiohttp.ClientSession() as session:
            for index, entry in enumerate(queue, start=1):
                try:
                    click.echo(f"Processing [{index}/{len(queue)}]: {entry}")
                    title, link = await get_video_url(entry, session)
                    await download(title, link, session, output_dir, output_filename)
                except Exception as e:
                    # import ipdb; ipdb.set_trace()
                    click.echo(f"Error: {e.__class__}")

    asyncio.run(main())


if __name__ == "__main__":
    download_video()
