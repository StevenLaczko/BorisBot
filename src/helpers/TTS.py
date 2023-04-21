import datetime
import io
import json
import os
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play

import requests


class TTS:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.stability = 0.50
        self.similarity_boost = 0.7
        self.boris_id = "w7YqYVZGwe0PlR3fH6zQ"
        self.header = {
            "xi-api-key": self.api_key
        }

    # returns an mp3 file in bytes
    def get_voices(self):
        req = requests.get("https://api.elevenlabs.io/v1/voices",
                           headers=self.header)
        return io.BytesIO(req.text)

    def generate(self, input_str: str):
        body = {
            "text": input_str,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        req = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{self.boris_id}",
                            json=body,
                            headers=self.header)
        return req.content


def demo():
    load_dotenv()
    tts = TTS()
    audio_bytes = tts.generate("""Hey look, buddy. I'm an engineer, that means I solve problems.
Not problems like "What is beauty?", 'cause that would fall within the purview of your conundrums of philosophy.""")

    # Assume that the byte string is stored in a variable called `audio_bytes`
    s = io.BytesIO(audio_bytes)
    audio_file = AudioSegment.from_file(s, format="mp3", strict=False)
    with open(f"data/voice_generations/engi_{datetime.datetime.now()}.mp3", 'wb+') as f:
        audio_file.export(f)
    play(audio_file)

