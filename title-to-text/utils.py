import os
import cv2
import wave
import uuid
import urllib
import pyaudio
import logging
import threading
import subprocess
import numpy as np
from pathlib import Path
from pytube import YouTube
from langdetect import detect
import speech_recognition as sr
from hydra import compose, initialize
from moviepy.editor import VideoFileClip
from subtitles_generator.core import Model
from subtitles_generator.utils import create_srt, extract_audio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

VIDEO_SAVE_DIRECTORY = "./video"

def download_video(video_url):
    try:
        video = YouTube(video_url)
        video_stream = video.streams.get_highest_resolution()
        video_path = video_stream.download(
            output_path=VIDEO_SAVE_DIRECTORY, filename=f"{uuid.uuid4()}.mp4"
        )
        logging.info(f"Video was downloaded successfully : {video_path}")
        return video_path
    except Exception as e:
        logging.info(f"Failed to download video: {e}")
        return None


def identify_language_from_audio(audio_file):
    recognizer = sr.Recognizer()

    # Load audio file
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)

    try:
        # Convert speech to text
        transcribed_text = recognizer.recognize_google(audio_data)

        # Detect language from transcribed text
        language_code = detect(transcribed_text)
        logging.info(f"Detected Languge Code : {language_code}")

        # Map language code to the expected format
        language_mapping = {
            "en": "English",
            "hi": "Hindi",
            "it": "Spanish",
            "pt": "Portuguese",
        }

        if language_code in language_mapping:
            return language_mapping[language_code]
        else:
            return "Unknown"  
    except Exception as e:
        logging.info("Error:", e)
        return "Unknown"


def extract_audio_from_video(video_file):

    video_file = str(video_file)

    # Load the video file
    video_clip = VideoFileClip(video_file)

    # Extract audio
    audio_clip = video_clip.audio

    # Define the output audio file path
    output_audio_file = Path(video_file).with_suffix(".wav")

    # Save the audio file
    audio_clip.write_audiofile(str(output_audio_file))

    # Close the video clip
    video_clip.close()

    return output_audio_file

def is_url(input_file):
    try:
        result = urllib.parse.urlparse(input_file)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def generate_subtitles_from_file(
    model_size: str, input_file: str, output_file_path: str = None, lang: str = None
):

    with initialize(version_base=None, config_path="subtitles_generator/conf"):
        cfg = compose(config_name="config")
    input_file_path = Path(input_file)

    if not input_file_path.is_file():
        raise FileNotFoundError(f"Input file {input_file} does not exist")

    output_file_path = Path("output") / (Path(input_file).stem + ".srt")
    # output_file_path = Path("output") / (Path(input_file))

    if lang not in cfg.supported_languages:
        raise ValueError(
            f"Language {lang} is not supported. Supported languages are {cfg.supported_languages}"
        )

    if model_size not in cfg.model_names.keys():
        raise ValueError(
            f"Model size {model_size} is not supported. Supported model sizes are {list(cfg.model_names.keys())}"
        )

    # Extract audio if input is a video
    if input_file_path.suffix in cfg.supported_media_formats.video:
        logging.info("Extracting audio ...")
        input_file_path = extract_audio(input_file_path)

    # Initialize model
    model = Model(cfg.model_names[model_size], lang)

    # Transcribe audio and generate subtitles
    logging.info("Generating subtitles ...")
    predicted_texts = model.transcribe(
        audio_path=input_file_path,
        sampling_rate=cfg.processing.sampling_rate,
        chunk_size=cfg.processing.chunk_size,
    )

    # Write subtitles to output file
    logging.info(f"Writing subtitles into {output_file_path} ...")
    create_srt(output_file_path, predicted_texts, cfg.processing.chunk_size)

    # Remove temporary audio file if extracted

    if os.path.exists(input_file_path):
        os.remove(input_file_path)
        # ----> os.remove(input_file)

    return output_file_path


def record_video_and_audio():
    # Parameters for audio recording
    FORMAT = pyaudio.paInt16
    CHANNELS = 1  # Change to 1 channel (mono)
    RATE = 44100
    CHUNK = 1024
    WAVE_OUTPUT_FILENAME = "output_audio.wav"

    # Parameters for video recording
    VIDEO_OUTPUT_FILENAME = "output_video.avi"
    FRAME_RATE = 20.0
    FRAME_SIZE = (640, 480)

    # Output combined video file
    COMBINED_OUTPUT_FILENAME = os.path.join(os.getcwd(), "video", f"{uuid.uuid4()}.mp4")
        

    # Initialize video capture
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(VIDEO_OUTPUT_FILENAME, fourcc, FRAME_RATE, FRAME_SIZE)

    # Initialize audio recording
    audio = pyaudio.PyAudio()

    def record_audio():
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK)
        frames = []

        while recording:
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

    # Start audio recording in a separate thread
    recording = True
    audio_thread = threading.Thread(target=record_audio)
    audio_thread.start()

    # print("Press 'q' to stop recording")

    # Record video and audio
    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret:
            out.write(frame)
            cv2.imshow('frame', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break

    # Stop recording
    recording = False
    audio_thread.join()

    # Release everything
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    audio.terminate()

    # Combine audio and video using FFmpeg
    ffmpeg_command = f"ffmpeg -i {VIDEO_OUTPUT_FILENAME} -i {WAVE_OUTPUT_FILENAME} -c:v copy -c:a aac -strict experimental {COMBINED_OUTPUT_FILENAME}"
    subprocess.call(ffmpeg_command, shell=True)

    os.remove(WAVE_OUTPUT_FILENAME)
    os.remove(VIDEO_OUTPUT_FILENAME)

    logging.info("Combined video saved as:", COMBINED_OUTPUT_FILENAME)

    return COMBINED_OUTPUT_FILENAME