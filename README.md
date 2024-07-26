# Video Downloader

A CLI tool to download videos from vider.info.

_I was really bored and needed few clips ;)_

## Installing
You can install the required libraries using pip:

```bash
git clone git@github.com:dwabece/vider-dl.git
```
and 
```bash
pip install -r requirements.txt requirements-dev.txt
```

## Usage
First, just run it and check the help:
```bash
python3 gox.py --help
```
The script has a shebang at the beginning so after setting correct permissions `chmod +x gox.py` you can use it as every other bash script: `./gox.py https://video-u.rl`. It's because I'm lazy and perfer typing `./` over `python3`.

### Download single video
To download a single video just run:
```bash
./gox.py https://some-video/+url
```

### Download videos from a queue file
To download multiple videos from a file containing URLs (one URL per line), run:
```bash
./gox.py --queue-file=list-of-videos.txt
```

### Solving captchas
Every now and then you you will get banned. In that case, calm down, I got your back. The script will prompt you and it will look like this:
```
╰─$ ./gox.py https://XD/11m8
Downloading video from: https:/XD/11m8
Processing [1/1]: https://XD/11m8
--------------------------------------------------------------------------------
You've been blocked, please solve the captcha.
The captcha is located in the captcha_image.png file.
--------------------------------------------------------------------------------
Captcha text:
```
What you need to do is open file named `captcha_image.png` that's located in the script directory and type what you see on the image. No worries, the script will do it's work.

If you'll fail to solve the captcha, no worries, you'll get prompted again and the image will be overwritten so just open it and pass the new captcha.