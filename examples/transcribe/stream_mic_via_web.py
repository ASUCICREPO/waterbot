#works

import secrets
import asyncio 

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
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results

        if len(results) > 0:
            if len(results[0].alternatives) > 0:
                transcript = results[0].alternatives[0].transcript
                print(transcript)


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
        media_encoding="pcm",
    )

    async def receive_audio():
        try:
            while True:
                data = await websocket.receive_text()
                if data == '{ "event": "close" }':
                    # Client wants to close the connection
                    await websocket.close()
                    break
                # ... (handle audio data)
        except Exception as e:
            print("WebSocket disconnected unexpectedly", str(e))
        finally:
            await stream.input_stream.end_stream()

    handler=MyEventHandler(stream.output_stream)

    try:
        await asyncio.gather(receive_audio(), handler.handle_events())
    except Exception as e:
            print("WebSocket disconnected unexpectedly:", str(e))
    finally:
        await websocket.close()