import os
import sys

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
os.environ["XDG_RUNTIME_DIR"] = "/tmp/runtime-root"
import logging

import datetime
import pathlib

import imageio

imageio.plugins.ffmpeg.download()
from moviepy.editor import VideoFileClip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


def extract_audio(input_path: pathlib.Path) -> str:
    if input_path.suffix == ".wav":
        return str(input_path)

    video = VideoFileClip(str(input_path))
    audio_path = input_path.with_suffix(".wav")
    video.audio.write_audiofile(str(audio_path), verbose=False)
    return str(audio_path)


def create_srt(
    subtitles_path: pathlib.Path,
    texts: list[str],
    interval_size: int,
):
    if subtitles_path.suffix != ".srt":
        subtitles_path.rename(subtitles_path.with_suffix(".srt"))

    with open(subtitles_path, "w", encoding="utf-8") as f:
        timer = 0
        frame_counter = 0
        for text in texts:
            # if text is None than we need to make a gap in subtitles flow
            if text is not None:
                # if the text too long for a frame
                text = text[:250]

                frame_counter += 1
                start_time = str(datetime.timedelta(seconds=timer)) + ",000"
                end_time = (
                    str(datetime.timedelta(seconds=timer + interval_size)) + ",000"
                )
                frame = f"{frame_counter}\n{start_time} -->  {end_time}\n{text}\n\n"
                f.write(frame)
            timer += interval_size
    if logging:
        logging.info(f"{frame_counter} subtitles frames have been generated")
