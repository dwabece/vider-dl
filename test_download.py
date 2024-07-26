import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientSession
from aioresponses import aioresponses

from gox import DEFAULT_TIMEOUT, HEADERS, download, fetch_chunk


class TestDownloadFunction(unittest.TestCase):
    @patch("aiofiles.open", new_callable=MagicMock)
    @patch("gox.tqdm", autospec=True)
    @patch("os.path.getsize", return_value=1024 * 1024 * 10)  # 10 MB
    @patch("gox.get_output_path", return_value="test_output.mp4")
    def test_download(
        self, mock_get_output_path, mock_getsize, mock_tqdm, mock_aiofiles_open
    ):
        # an aasync mock for aiofiles.open
        mock_file = MagicMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=False)
        mock_file.write = AsyncMock(return_value=None)
        mock_file.truncate = AsyncMock(return_value=None)
        mock_file.seek = AsyncMock(return_value=None)

        mock_aiofiles_open.return_value = mock_file

        total_length = 10485760
        chunk_size = 1024 * 1024

        with aioresponses() as m:
            m.get(
                "https://so.me/video?link",
                headers={"content-length": "10485760"},
                status=200,
            )
            for start in range(0, total_length, chunk_size):
                end = min(start + chunk_size, total_length) - 1
                m.get(
                    "https://so.me/video?link",
                    headers={"content-range": f"bytes {start}-{end}/10485760"},
                    status=206,
                    body=b"x" * (end - start + 1),
                )

            async def run_download():
                async with ClientSession() as session:
                    await download(
                        title="Test Video",
                        url="https://so.me/video?link",
                        session=session,
                        output_dir=".",
                        file_name="test_output.mp4",
                    )

            asyncio.run(run_download())

            mock_get_output_path.assert_called_once_with(".", "test_output.mp4")
            self.assertTrue(mock_aiofiles_open.called)
            # print(f"mock_tqdm call count: {mock_tqdm.call_count}")
            mock_tqdm.assert_called_once()
            mock_pbar = mock_tqdm.return_value
            # print(f"mock_pbar.update call count: {mock_pbar.update.call_count}")
            self.assertEqual(mock_pbar.update.call_count, (total_length // chunk_size))
            mock_pbar.update.assert_called()
            mock_pbar.close.assert_called()

    @patch("aiofiles.open", new_callable=MagicMock)
    def test_fetch_chunk(self, mock_aiofiles_open):
        async def run_fetch_chunk():
            url = "https://that-video-portal.info/some-random####=-video.mp4"
            start = 0
            end = 1024
            out_file = "bolek&lo.mp4"
            dl_item = b"huiouhfjknasc9824re"

            # mocking aiohttp.ClientSession.get to return a context manager
            mock_response = MagicMock()
            mock_response.read = AsyncMock(return_value=dl_item)
            mock_get = MagicMock()
            mock_get.__aenter__.return_value = mock_response
            mock_get.__aexit__.return_value = AsyncMock()

            mock_session = MagicMock()
            mock_session.get.return_value = mock_get

            # mock aiofiles
            mock_file = mock_aiofiles_open.return_value.__aenter__.return_value
            mock_file.seek = AsyncMock()
            mock_file.write = AsyncMock()

            # progress bar
            mock_pbar = MagicMock()
            mock_pbar.update = MagicMock()

            await fetch_chunk(mock_session, url, start, end, out_file, mock_pbar)

            mock_session.get.assert_called_once_with(
                url,
                headers={**HEADERS, "range": f"bytes={start}-{end}"},
                timeout=DEFAULT_TIMEOUT,
            )
            mock_aiofiles_open.assert_called_once_with(out_file, "r+b")
            mock_file.seek.assert_awaited_once_with(start)
            mock_file.write.assert_awaited_once_with(dl_item)
            mock_pbar.update.assert_called_once_with(len(dl_item))

        asyncio.run(run_fetch_chunk())


if __name__ == "__main__":
    unittest.main()
