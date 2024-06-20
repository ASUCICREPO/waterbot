
import httpx
import logging
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream, websocket):
        super().__init__(output_stream)
        self.websocket = websocket
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # Mapping of specific phrases to API endpoints
        self.api_endpoints = {
            "tell me more": "http://localhost:8000/chat_detailed_api",
            "next steps": "http://localhost:8000/chat_actionItems_api",
            "sources": "http://localhost:8000/chat_sources_api",
        }

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                for alt in result.alternatives:
                    logging.info(f"Handling full transcript: {alt.transcript}")
                    api_url = self.determine_api_url(alt.transcript.strip().lower())
                    form_data = {'user_query': alt.transcript}
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.post(api_url, data=form_data)
                            response.raise_for_status()  # This will raise an exception for HTTP error responses
                            await self.send_responses(alt.transcript, response)
                    except (httpx.HTTPError, httpx.RequestError) as e:
                        logging.error(f"Failed to post to chat API: {e}")
                        await self.websocket.send_json({'type': 'error', 'details': str(e)})

    def determine_api_url(self, transcript):
        # Exact matches for specific requests, considering an optional period
        for key, url in self.api_endpoints.items():
            if transcript == key or transcript == key + '.':
                return url
        return "http://localhost:8000/chat_api"  # Default API if no exact match is found

    async def send_responses(self, user_transcript, api_response):
        await self.websocket.send_json({
            'type': 'user',
            'transcript': user_transcript
        })
        logging.info("Sent user message to client.")
        api_response_data = api_response.json()
        await self.websocket.send_json({
            'type': 'bot',
            'response': api_response_data['resp'],
            'messageID': api_response_data['msgID']
        })
        logging.info("Sent bot response to client.")