import logging
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from main import chat_detailed_api_post, chat_api_post, chat_action_items_api_post,chat_sources_post

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream, websocket):
        super().__init__(output_stream)
        self.websocket = websocket
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # Function mapping
        self.function_map = {
            "tell me more": chat_detailed_api_post,
            "next steps": chat_action_items_api_post,
            "sources": chat_sources_post
        }

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                for alt in result.alternatives:
                    logging.info(f"Handling full transcript: {alt.transcript}")
                    function = self.determine_function(alt.transcript.strip().lower())
                    response = await function(alt.transcript)  # Direct function call
                    await self.send_responses(alt.transcript, response)


    def determine_function(self, transcript):
        for key, func in self.function_map.items():
            if transcript == key or transcript == key + '.':
                return func
        return chat_api_post  # Default function if no exact match is found

    async def send_responses(self, user_transcript, api_response):
        await self.websocket.send_json({
            'type': 'user',
            'transcript': user_transcript
        })
        logging.info("Sent user message to client.")
        await self.websocket.send_json({
            'type': 'bot',
            'response': api_response['resp'],
            'messageID': api_response['msgID']
        })
        logging.info("Sent bot response to client.")