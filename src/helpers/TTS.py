import datetime
import io
import json

import opuslib
import os
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play

import requests

# Setup Encoder
sample_rate = 48000 # Hz
channels = 2 # stereo
bitrate = 64000 # bits per second


class TTS:
    def __init__(self, stability: float = None, similarity: float = None):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self._stability = 0.5
        self._similarity_boost = 0.99
        #self.boris_id = "w7YqYVZGwe0PlR3fH6zQ" #old voice
        self.boris_id = "0GtkdYi9hrybmSLy5Rep"
        self.header = {
            "xi-api-key": self.api_key
        }
        self.encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_AUDIO)
        self.encoder.bitrate = bitrate
        self.decoder = opuslib.Decoder(sample_rate, channels)

    def set_stability(self, f):
        if f > 1 or f < 0:
            raise ValueError("Stability must be a float between 0 and 1")
        self._stability = f

    def set_similarity(self, f):
        if f > 1 or f < 0:
            raise ValueError("Similarity must be a float between 0 and 1")
        self._similarity_boost = f

    def get_voices(self):
        req = requests.get("https://api.elevenlabs.io/v1/voices",
                           headers=self.header)
        return req.text

    def generate(self, input_str: str):
        body = {
            "text": input_str,
            "voice_settings": {
                "stability": self._stability,
                "similarity_boost": self._similarity_boost
            }
        }
        req = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{self.boris_id}",
                            json=body,
                            headers=self.header)

        return req.content

    def convert_bytes_to_mp3(self, audio_bytes):
        s = io.BytesIO(audio_bytes)
        audio_file = AudioSegment.from_file(s, format="mp3", strict=False)
        return audio_file

    def convert_bytes_to_opus(self, audio_bytes):
        opus_bytes = self.encoder.encode(audio_bytes, 960)

    def convert_opus_to_bytes(self, opus_bytes):
        self.decoder.decode(opus_bytes, 960)




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


def get_boris_voice_data():
    load_dotenv()
    tts = TTS()
    data = json.loads(tts.get_voices())
    for v in data["voices"]:
        if "oris" in v["name"]:
            print(v)
