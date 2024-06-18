import cv2
import pyaudio
import wave
import threading
import subprocess
import numpy as np
import os

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
COMBINED_OUTPUT_FILENAME = "output_combined.mp4"

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

print("Press 'q' to stop recording")

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
ffmpeg_command = f"F:/Bit_Coding/video_record/env/Lib/site-packages/ffmpeg/bin/ffmpeg.exe -i {VIDEO_OUTPUT_FILENAME} -i {WAVE_OUTPUT_FILENAME} -c:v copy -c:a aac -strict experimental {COMBINED_OUTPUT_FILENAME}"
subprocess.call(ffmpeg_command, shell=True)

os.remove(WAVE_OUTPUT_FILENAME)
os.remove(VIDEO_OUTPUT_FILENAME)

print("Combined video saved as:", COMBINED_OUTPUT_FILENAME)