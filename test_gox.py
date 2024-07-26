import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession
from bs4 import BeautifulSoup

from gox import (
    DEFAULT_TIMEOUT,
    HEADERS,
    download_captcha,
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


@pytest.mark.asyncio
async def test_download_captcha(mocker):
    captcha_url = "https://vider.pl/captcha_url"
    captcha_content = b"qi9ewufihadsbjkvnsioouhregyhadJKSOIFHU"

    mock_response = MagicMock()
    mock_response.read = AsyncMock(return_value=captcha_content)
    mock_get = MagicMock()
    mock_get.__aenter__.return_value = mock_response
    # mock_get.__aenter__.return_value
    mock_get.__aexit__.return_value = AsyncMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_get

    # moching aiofiles to return an async context manager
    mock_open = mocker.patch("aiofiles.open", new_callable=MagicMock)
    mock_file = mock_open.return_value.__aenter__.return_value
    mock_file.write = AsyncMock()

    await download_captcha(captcha_url, mock_session)

    mock_session.get.assert_called_once_with(
        captcha_url, headers=HEADERS, timeout=DEFAULT_TIMEOUT
    )
    mock_open.assert_called_once_with("captcha_image.png", "wb")
    mock_file.write.assert_awaited_once_with(captcha_content)
