from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

class TranscribeManager(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.actions = {
                "tell me more": "ACTION_tell_me_more",
                "next steps": "ACTION_next_steps",
                "sources": "ACTION_chat_sources",
            }


    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                for alt in result.alternatives:
                    print(f"Handling full transcript: {alt.transcript}")
                    action = await self.determine_action(alt.transcript.strip().lower())
                    print(action)


    async def determine_action(self, transcript):
        # Exact matches for specific requests, considering an optional period
        return self.actions.get(transcript.replace(".",""),"ACTION_default")