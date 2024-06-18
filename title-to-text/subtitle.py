import os
import av
import re
import cv2
import uuid
import logging
import requests
import subprocess
import streamlit as st
from pytube import YouTube
from fastapi import HTTPException
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase, RTCConfiguration
from utils import download_video, extract_audio_from_video, identify_language_from_audio, record_video_and_audio

# Define the backend URL
BACKEND_URL = "http://127.0.0.1:8000/subtitle"


def get_video_duration(video_url):
    video = YouTube(video_url)
    duration = video.length
    logging.info(f"Video duration: {duration} seconds")
    return duration


def is_valid_youtube_url(url):
    youtube_pattern = r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    music_pattern = r"^(?:https?:\/\/)?(?:www\.)?(?:music\.youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|music\.youtu\.be\/)([a-zA-Z0-9_-]{11})"
    short_pattern = r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/|shorts\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    if (
        re.match(youtube_pattern, url)
        or re.match(short_pattern, url)
        or re.match(music_pattern, url)
    ):
        logging.info("YouTube URL is valid")
        return True
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")


def subtitle():
    st.header("Video-to-Subtitle Transformer: Weaving Words into Visual Stories🎥📝 ")

    st.subheader("Step 1: Choose Your video Input Method ")
    selected_method = st.radio(
        "Choose one of the following methods:",
        ["Upload video", "Enter YouTube Link","Record Video"],
        index=None,
        horizontal=True,
    )

    # Define the video processor class
    class VideoProcessor(VideoProcessorBase):
        def __init__(self):
            self.frames = []
            self.recording = False

        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            if self.recording:
                self.frames.append(img)
            return av.VideoFrame.from_ndarray(img, format="bgr24")

        def on_start(self):
            self.recording = True
            self.frames = []

        def on_stop(self):
            self.recording = False
            video_path = "output_video.mp4"

            if self.frames:
                height, width, _ = self.frames[0].shape
                out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 30, (width, height))

                for frame in self.frames:
                    out.write(frame)

                out.release()
                st.success(f"Video saved at {video_path}")
            else:
                st.error("No frames captured")

    # Configure the WebRTC streamer
    RTC_CONFIGURATION = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )
    # Initialize variables for user inputs
    uploaded_file = None
    url = ""
    video_path = None
    recorded_video_path = None

    if selected_method == "Upload video":
        uploaded_file = st.file_uploader(
            "Upload Video File",
            type=["mp4"],
        )
        if uploaded_file:
            logging.info("User selected to upload video")
            if "video_path" not in st.session_state:
                video_path = os.path.join(os.getcwd(), "video", f"{uuid.uuid4()}.mp4")
                with open(video_path, "wb") as buffer:
                    buffer.write(uploaded_file.getvalue())
                st.session_state.video_path = video_path

            video_path = st.session_state.video_path
            st.video(video_path, start_time=0)

    elif selected_method == "Enter YouTube Link":
        logging.info("User selected to enter YouTube link")
        url = st.text_input("Enter YouTube Link")
        if url:
            is_valid_youtube_url(url)
            if "youtube_video_path" not in st.session_state:
                video_path = download_video(url)
                st.session_state.youtube_video_path = video_path
                st.success("Video downloaded successfully.")
            video_path = st.session_state.youtube_video_path
            st.video(video_path, start_time=0)
        else:
            st.error("Please enter a valid YouTube URL")

    
    elif selected_method == "Record Video":
        logging.info("User selected to record a video")
        # Initialize the video processor
        ctx = webrtc_streamer(
            key="example",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_processor_factory=VideoProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True
        )
         

    if video_path or uploaded_file or recorded_video_path:
        st.success("Step 1 Completed!")

        # Step 2: Model Selection
        st.header("Step 2: Select Your Transcription Model 🤖")
        model_selected = st.radio(
            "Select Model", ["base", "medium", "large"], index=None, horizontal=True
        )
        logging.info(f"Model selected: {model_selected}")

        if model_selected in ["base", "medium", "large"]:
            st.success("Step 2 Completed!")

            # Step 3: Select Language
            st.header("Step 3: Select Your Language ✨")

            # Add a spinner to indicate language detection is in progress
            if "detected_lang" not in st.session_state:
                with st.spinner("Detecting language..."):

                    # Extract audio and detect language
                    input_file = extract_audio_from_video(video_path)
                    detected_lang = identify_language_from_audio(str(input_file))
                    st.session_state.detected_lang = detected_lang

            detected_lang = st.session_state.detected_lang

            # Display detected language

            st.markdown(
                f"""
                        <div style='display: flex;
                                    text-align: center; 
                                    justify-content: center; 
                                    align-items: center; 
                                    height: 50px; 
                                    font-weight: bold; 
                                    font-style: italic; 
                                    color: darkblue; 
                                    background-color: lightblue; 
                                    padding: 10px; 
                                    border-radius: 5px;'>
                            <h5 style='margin: 0; padding: 0;'>Your Detected Language: {detected_lang}</h5>
                        </div>
                        """,
                unsafe_allow_html=True,
            )

            st.markdown(
                "<h5 style='text-align: center; margin-top: 10px;'>If You Want to Change Your Language Then Select Below Option</h5>",
                unsafe_allow_html=True,
            )

            if "lang" not in st.session_state:
                st.session_state.lang = None

            if detected_lang == "Unknown":
                selected_option = st.selectbox(
                    placeholder="Select an option",
                    label="Select an option",
                    index=None,
                    options=["Hindi", "English", "Spanish", "German"],
                )
                logging.info(
                    "Detected language is unknown, using user selected language--->",
                    selected_option,
                )

            else:
                col1, col2 = st.columns(2)

                with col1:
                    continue_with_detected_lang = st.button(
                        "Continue with detected language"
                    )

                    if continue_with_detected_lang:

                        st.session_state.lang = detected_lang
                        logging.info(f"Continuing with detected language: {detected_lang}")
                        st.write(
                            f"""
                                <p style='font-family: cursive; 
                                          font-style: italic; 
                                          background-color: #dce9fa;
                                          line-height: 1.5;
                                          color: black;
                                          padding: 10px;
                                          border-radius: 4px;'>
                                    Generating with detected language: {detected_lang}
                                </p>
                                """,
                            unsafe_allow_html=True,
                        )

                with col2:
                    selected_option = st.selectbox(
                        placeholder="Select an option",
                        label="Select an option",
                        index=None,
                        options=["Hindi", "English", "Spanish", "German"],
                    )
                    logging.info(f"User selected language: {selected_option}")

            if selected_option:
                st.session_state.lang = selected_option.lower()

            if (st.session_state.lang == detected_lang) or st.session_state.lang:

                st.success("Step 3 Completed!")

                # Step 4: Transcription
                st.header(
                    "Step 4: Transcript Perfection: Crafting Accurate Subtitles🌟"
                )
                transcribe_button = st.button("Generate", type="primary")
                if transcribe_button:
                    with st.spinner("Transcribing..."):

                        if selected_method == "Upload video" and uploaded_file:

                            data = {
                                "input_file_path": video_path,
                                "output_file_path": "",
                                "model_size": model_selected,
                                "language": st.session_state.lang,
                            }
                            response = requests.post(BACKEND_URL, data=data)

                        elif selected_method == "Enter YouTube Link" and url:

                            data = {
                                "input_file_path": video_path,
                                "output_file_path": "",
                                "model_size": model_selected,
                                "language": st.session_state.lang,
                            }
                            response = requests.post(BACKEND_URL, data=data)

                        elif selected_method == "Record Video" and input_file:

                            data = {
                                "input_file_path": video_path,
                                "output_file_path": "",
                                "model_size": model_selected,
                                "language": st.session_state.lang,
                            }
                        if response.status_code == 200:
                            st.success("Subtitles generated successfully !")
                            result = response.json()["output_file_path"]
                            with open(result, "rb") as file:
                                file_content = file.read()

                            st.download_button(
                                label="Download subtitle file",
                                data=file_content,
                                file_name="subtitles.txt",
                                mime="text/plain",
                            )
                            st.video(video_path, start_time=0, subtitles="")
                            # st.video(video_path, start_time=0, subtitles=file_content)
                            logging.info("Subtitles generated ")
                            
                        else:
                            logging.error("Transcription failed with response status: {response.status_code}")
                            st.error("Transcription Failed  !")
