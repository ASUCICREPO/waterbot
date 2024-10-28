from .base import ModelAdapter
import boto3
import json
from langchain_community.embeddings import BedrockEmbeddings
import datetime

class BedrockClaudeAdapter(ModelAdapter):
    def __init__(self, model_id="anthropic.claude-3-sonnet-20240229-v1:0", region='us-east-1', *args, **kwargs):
        self.embeddings = BedrockEmbeddings(region_name=region)
        self.model_id=model_id
        self.client = boto3.client('bedrock-runtime', region)
        super().__init__(*args,**kwargs)

    def get_embeddings( self ):
        return self.embeddings
    
    async def generate_llm_payload(self, system_prompt, max_tokens, messages, temperature, anthropic_version="bedrock-2023-05-31"):       
        return json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "system":system_prompt,
                "max_tokens": max_tokens,
                "messages":messages,
                "temperature": temperature,
            }
        )  

    async def get_llm_nextsteps_body( self, kb_data, user_query,bot_response, max_tokens=512, temperature=.5 ):
        system_prompt=await self.get_action_item_prompt(kb_data)
        
        inject_user_query="<NEXTSTEPS_REQUEST>Provide me the action items<NEXTSTEPS_REQUEST>"
        messages=await self.build_message_chain_for_action(user_query=user_query,bot_response=bot_response,inject_user_query=inject_user_query)

        bedrock_payload=await self.generate_llm_payload(system_prompt=system_prompt, max_tokens=max_tokens, messages=messages, temperature=temperature)

        return bedrock_payload
    
    async def get_llm_detailed_body( self, kb_data, user_query,bot_response, max_tokens=512, temperature=.5 ):
        system_prompt=await self.get_chat_detailed_prompt(kb_data)

        inject_user_query="<MOREDETAIL_REQUEST>Provide me a more detailed response</MOREDETAIL_REQUEST>"
        messages=await self.build_message_chain_for_action(user_query=user_query,bot_response=bot_response,inject_user_query=inject_user_query)

        bedrock_payload=await self.generate_llm_payload(system_prompt=system_prompt, max_tokens=max_tokens, messages=messages, temperature=temperature)


        return bedrock_payload
    
    async def get_llm_body( self, kb_data, chat_history, max_tokens=512, temperature=.5 ):
        system_prompt = """
        You are a helpful assistant named Blue that provides information about water in Arizona.

        You will be provided with Arizona water-related queries.

        The governor of Arizona is Katie Hobbs.

        When asked the name of the governor or current governor, you should respond with the name Katie Hobbs.

        For any other inquiries regarding the names of elected officials excluding the name of the governor, you should respond: 'The most current information on the names of elected officials is available at az.gov.'

        Verify not to include any information that is irrelevant to the current query.

        Use the following knowledge: 
        <knowledge>
        {kb_data}
        </knowledge>

        You should answer in 4-5 sentences in a friendly tone and include details within those 4-5 sentences. You can include more information when available. Avoid lists.

        For longer responses (2 sentences), please separate each paragraph with a line break to improve readability. Additionally, add a line break before the closing line.

        At the end of each message, please include - 

        "I would love to tell you more! Just click the buttons below or ask a follow-up question."
        """

        system_prompt=system_prompt.format(kb_data=kb_data)
        
        messages=[]
        for message in chat_history:
            messages.append(message)
        
        bedrock_payload=await self.generate_llm_payload(system_prompt=system_prompt, max_tokens=max_tokens, messages=messages, temperature=temperature)


        return bedrock_payload

    async def generate_response(self,llm_body):
        accept = 'application/json'
        contentType = 'application/json'

        response = self.client.invoke_model(body=llm_body, modelId=self.model_id, accept=accept, contentType=contentType)
        response_body =  json.loads(response.get('body').read())
        response_content = response_body["content"][0]["text"]
        
        return response_content
    
    async def safety_checks(self, user_query):
        async def UserIntentCheck(user_query,temperature=.5,max_tokens=500):
            system_prompt=await self.get_intent_system_prompt()
            
            messages=[]
            messages.append(
                {
                    'role':'user',
                    'content':user_query
                }
            )
            
            bedrock_payload=await self.generate_llm_payload(system_prompt=system_prompt, max_tokens=max_tokens, messages=messages, temperature=temperature)


            return await self.generate_response(bedrock_payload)
    
        # We skip moderation result as these are baked into
        # bedrock already
        moderation_result=False
        intent_result = await UserIntentCheck(user_query)

        return moderation_result,intent_result