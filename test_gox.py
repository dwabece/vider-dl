import os

import pytest
from aiohttp import ClientSession
from bs4 import BeautifulSoup

from gox import (
    get_output_path,
    lookup_for_captcha,
    title_to_filename,
)


def test_get_output_path():
    assert get_output_path("/tmp", "random_video.mp4") == "/tmp/random_video.mp4"
    assert get_output_path("", "video.mp4") == os.path.join(os.getcwd(), "video.mp4")


def test_title_to_filename():
    assert (
        title_to_filename("You Shouldnt be watching that")
        == "You Shouldnt be watching that"
    )
    assert title_to_filename("No@Elo!Wariacie&2136") == "No-Elo-Wariacie-2136"
    assert title_to_filename("  To pa tera XD  ") == "To pa tera XD"


@pytest.mark.asyncio
async def test_lookup_for_captcha():
    html_with_captcha = """
    <html>
        <body>
            <input name="captcha" placeholder="Wpisz kod z obrazka..."/>
            <img src="/streaming/ca-pt-some-image.png"/>
        </body>
    </html>
    """
    html_without_captcha = """
    <html>
        <body>
        </body>
    </html>
    """
    soup_with_captcha = BeautifulSoup(html_with_captcha, "html.parser")
    soup_without_captcha = BeautifulSoup(html_without_captcha, "html.parser")

    async with ClientSession() as session:
        assert await lookup_for_captcha(soup_with_captcha, session)
        assert not await lookup_for_captcha(soup_without_captcha, session)
