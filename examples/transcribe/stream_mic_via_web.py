#works

import secrets
import asyncio 
import json

from fastapi import FastAPI, WebSocket
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware management
secret_key=secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=secret_key)

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                print(alt.transcript)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    client = TranscribeStreamingClient(region="us-east-1")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="ogg-opus",
    )

    async def receive_audio():
        try:
            while True:
                data = await websocket.receive()
                #print(data)
                if data.get("text") == '{"event":"close"}':
                    print("Closing WebSocket connection")
                    await stream.input_stream.end_stream()
                    break
                elif data.get("bytes"):
                    # Send the audio data to the Amazon Transcribe service
                    await stream.input_stream.send_audio_event(audio_chunk=data.get("bytes"))
        except Exception as e:
            print("WebSocket disconnected unexpectedly (receive audio after while)", str(e))
            await stream.input_stream.end_stream()

    handler = MyEventHandler(stream.output_stream)

    try:
        await asyncio.gather(receive_audio(), handler.handle_events())
    except Exception as e:
        print("WebSocket disconnected unexpectedly (receive audio after handler):", str(e))
    finally:
        print("Closing WebSocket connection")
        await websocket.close()