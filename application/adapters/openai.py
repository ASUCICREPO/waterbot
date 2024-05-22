from .base import ModelAdapter
import json
from openai import OpenAI
import re
from langchain_openai import OpenAIEmbeddings
from datetime import datetime
import asyncio


class OpenAIAdapter(ModelAdapter):
    def __init__(self, model_id="gpt-3.5-turbo", region=None, *args, **kwargs):
        self.embeddings = OpenAIEmbeddings()
        self.model_id=model_id
        self.client = OpenAI()
        super().__init__(*args,**kwargs)
    
    def get_embeddings( self ):
        return self.embeddings
    
    async def get_llm_body( self, kb_data, chat_history, max_tokens=512, temperature=.5 ):
        system_prompt = """

        You are a helpful assistant named Blue that provides information about water in Arizona.

        You will be provided with Arizona water related queries. 

        Your not to include any information that is irrelevant to the current query. Use the following information to 
        answer the queries briefly in 3 to 4 sentences in a friendly tone {kb_data}"""

        system_prompt=system_prompt.format(kb_data=kb_data)

        messages=[
            {
                "role":"system",
                "content":system_prompt
            }
        ]
        for message in chat_history:
            messages.append(message)
        
        openai_payload = json.dumps(
            {
                "messages":messages,
                "temperature": temperature,
            }
        )  


        return openai_payload

    async def generate_response(self,llm_body):
        llm_body = json.loads(llm_body)

        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=llm_body["messages"],
            temperature=llm_body["temperature"],
            stream=False  # we set stream=True
        )

        response_body = response.choices[0].message.content
        print(response_body)
        response_content = re.sub(r'\n', '<br>', response_body)

        return response_content
    
    async def safety_checks(self, user_query):
        async def ModerationCheck(user_query):
            print('timestamp starting moderation check: ',datetime.now().strftime(' %H:%M:%S'))
            response = self.client.moderations.create(input=user_query)
            moderation_output = response.results[0].flagged
            print('timestamp exiting moderation check: ',datetime.now().strftime(' %H:%M:%S'))
            print(moderation_output)
            return moderation_output
        async def UserIntentCheck(user_query,temperature=.5,max_tokens=500):
            system_prompt=await self.get_intent_system_prompt()

            messages=[
                {
                    "role":"system",
                    "content":system_prompt
                }
            ]
            messages.append(
                {
                    'role':'user',
                    'content':user_query
                }
            )
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False  # we set stream=True
            )

            return response.choices[0].message.content
    
        # Run both coroutines concurrently
        moderation_result, intent_result = await asyncio.gather(
            ModerationCheck(user_query),
            UserIntentCheck(user_query)
        )

        return moderation_result,intent_result