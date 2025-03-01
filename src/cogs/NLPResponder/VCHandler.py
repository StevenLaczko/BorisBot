import asyncio
import threading
import time
from typing import Union

import sys
sys.path.insert(0, './discord.py')
import discord


class VCHandler:
    def __init__(self):
        self.vc_task: Union[asyncio.Task, None] = None
        self.audio_retrieve_start = None
        self.vc_con: discord.VoiceClient = None
        self.tts = self.pick_tts()
        self.vc_text_channel = None
        self.play_thread = threading.Thread()

    def pick_tts(self):
        pass


    def is_connected(self):
        return True if self.vc_con else False

    async def vc_disconnect(self):
        if self.vc_task and not self.vc_task.done():
            self.vc_task.cancel()
        if self.vc_con:
            await self.vc_con.voice_disconnect()
            self.vc_con = None
        self.vc_text_channel = None
        self.audio_retrieve_start = None

    def vc_callback(self, data):
        pass
        # self.audio_retrieve_start = datetime.now()
        # # Decode the Opus data to PCM
        # pcm_data, _ = discord.opus.decode(data, 3840)
        #
        # # Process the PCM data as needed
        # # For example, write it to a file using soundfile
        # f = io.BytesIO(pcm_data)
        # from pydub import AudioSegment
        # AudioSegment.from_file(f, format='WAV')
        #
        # # Do something with the WAV data, such as sending it to a speech-to-text API
        # text = GPTHelper.speech_to_text(wav_bytes)
        #

    async def connect_to_vc(self, vc: discord.VoiceChannel, text_channel):
        self.vc_con = await vc.connect()
        self.vc_text_channel = text_channel

    def respond(self, text):
        ffmpegOpusAudio = self.tts.generate(text)
        self.play_thread = threading.Thread(target=self.play_audio_in_vc, args=(ffmpegOpusAudio,))
        self.play_thread.start()

        # with open(f"data/voice_generations/engi_{datetime.now()}.mp3", 'wb+') as f:
        #     audio_file.export(f)
        #play(audio_file)

    def play_audio_in_vc(self, ffmpegOpusAudio):
            self.vc_con.play(source=ffmpegOpusAudio, after=None)
            while self.vc_con.is_playing():
                time.sleep(0.5)

