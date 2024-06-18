import os
import uvicorn
import logging
from fastapi import FastAPI, Form
from utils import generate_subtitles_from_file
from utils import extract_audio_from_video, identify_language_from_audio

app = FastAPI()

# Define the folder where you want to save the video files
VIDEO_FOLDER = "./video"

# Ensure the video folder exists
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


@app.post("/subtitle")
async def read_root(
    input_file_path: str = Form(None),
    output_file_path: str = Form(None),
    model_size: str = Form(),
    language: str = Form(None),
):

    try:
        # Determine input file path
        input_file = input_file_path

        # Extract audio from video
        logging.info(f"Extracting audio from {input_file}")
        input_file = extract_audio_from_video(input_file)

        # Identify language from audio
        detected_lang = identify_language_from_audio(str(input_file))
        logging.info(f"Detected language: {detected_lang}")

        user_lang = language.lower() if language else None

        if detected_lang == "Unknown" and user_lang:
            lang = user_lang
            logging.info(
                f"Detected language is unknown. Hence, using user selected language : {lang}"
            )
        else:
            lang = detected_lang

        if user_lang and user_lang != detected_lang:
            lang = user_lang
            logging.info(f"User Selected Language : {user_lang}")

        # Generate subtitles
        output_file_path = generate_subtitles_from_file(
            model_size=model_size,
            input_file=input_file,
            output_file_path=output_file_path,
            lang=lang,
        )
        logging.info(f"Subtitles generated at {output_file_path}")

        return {"output_file_path": output_file_path}

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
