import uvicorn
import uuid
import secrets
import socket

from typing import Annotated

import mappings.custom_tags as custom_tags

from fastapi import FastAPI, BackgroundTasks
from fastapi import Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from managers.memory_manager import MemoryManager
from managers.dynamodb_manager import DynamoDBManager
from managers.chroma_manager import ChromaManager

from adapters.claude import BedrockClaudeAdapter
from adapters.openai import OpenAIAdapter

from dotenv import load_dotenv

import os
import json

from starlette.middleware.base import BaseHTTPMiddleware

# Set the cookie name to match the one configured in the CDK
COOKIE_NAME = "WATERBOT"

class SetCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        session_value = request.cookies.get(COOKIE_NAME) or str(uuid.uuid4())
        # Set the application cookie in the response headers
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_value,  # You can set any value you want
            max_age=7200,  # Cookie expiration time in seconds (1 hour in this example)
            httponly=True,  # Set to True for better security
            samesite="Strict"  # Strict mode to prevent CSRF attacks
        )

        return response


# Take environment variables from .env
load_dotenv(override=True)  

# FastaAPI startup
app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware management
secret_key=secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.add_middleware(SetCookieMiddleware)

MESSAGES_TABLE=os.getenv("MESSAGES_TABLE")
# adapter choices
ADAPTERS = {
    "claude.haiku":BedrockClaudeAdapter("anthropic.claude-3-haiku-20240307-v1:0"),
    "claude.sonnet":BedrockClaudeAdapter("anthropic.claude-3-sonnet-20240229-v1:0"),
    "openai-gpt3.5":OpenAIAdapter("gpt-3.5-turbo")
}

# Set adapter choice
llm_adapter=ADAPTERS["claude.haiku"]
#llm_adapter=ADAPTERS["openai-gpt3.5"]

embeddings = llm_adapter.get_embeddings()


# Manager classes
memory = MemoryManager()  # Assuming you have a MemoryManager class
datastore = DynamoDBManager(messages_table=MESSAGES_TABLE)
knowledge_base = ChromaManager(persist_directory="docs/chroma/", embedding_function=embeddings)

message_count = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request,):
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    context = {
        "request": request,
        "hostname": hostname,
        "ip_address": ip_address
    }

    return templates.TemplateResponse("index.html", context )

# Route to handle ratings
@app.post('/submit_rating_api')
async def submit_rating_api_post(
        request: Request,
        message_id: str = Form(..., description="The ID of the message"),
        reaction: str = Form(None, description="Optional reaction to the message"),
        userComment: str = Form(None, description="Optional user comment")
    ):

    session = request.session
    session_uuid = request.cookies.get(COOKIE_NAME)


    await datastore.update_rating_fields(
        session_uuid=session_uuid,
        message_id=message_id,
        reaction=reaction,
        userComment=userComment
    )
    

# User wants to see sources of previous message
@app.post('/chat_sources_api')
async def chat_sources_post(request: Request, background_tasks:BackgroundTasks):
    session = request.session
    session_uuid = request.cookies.get(COOKIE_NAME)

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")


    memory_payload={
        "documents":docs,
        "sources":sources
    }

    formatted_source_list=await memory.format_sources_as_html(source_list=sources)


    generated_user_query = f'{custom_tags.tags["SOURCE_REQUEST"][0]}Provide me sources.{custom_tags.tags["SOURCE_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    bot_response=formatted_source_list


    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=memory_payload
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":bot_response},
        source_list=memory_payload
    )
    session["message_count"]+=1

    # We do not include sources as this message is the actual sources; no AI generation involved.
    background_tasks.add_task( datastore.write_msg,
        session_uuid=session_uuid,
        msg_id=session["message_count"], 
        user_query=generated_user_query, 
        response_content=bot_response,
        source=[] 
    )

    return {
        "resp":bot_response,
        "msgID": session["message_count"]
    }
    

# Route to handle next steps interactions
@app.post('/chat_actionItems_api')
async def chat_action_items_api_post(request: Request, background_tasks:BackgroundTasks):
    session = request.session
    session_uuid = request.cookies.get(COOKIE_NAME)

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }


    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")

    doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})


    llm_body=await llm_adapter.get_llm_nextsteps_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["NEXTSTEPS_REQUEST"][0]}Provide me the action items{custom_tags.tags["NEXTSTEPS_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    session["message_count"]+=1

    
    background_tasks.add_task( datastore.write_msg,
        session_uuid=session_uuid,
        msg_id=session["message_count"], 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )


    return {
        "resp":response_content,
        "msgID": session["message_count"] 
    }

# Route to handle next steps interactions
@app.post('/chat_detailed_api')
async def chat_detailed_api_post(request: Request, background_tasks:BackgroundTasks):
    session = request.session
    session_uuid = request.cookies.get(COOKIE_NAME)

    docs=await memory.get_latest_memory( session_id=session_uuid, read="documents")
    sources=await memory.get_latest_memory( session_id=session_uuid, read="sources")

    memory_payload={
        "documents":docs,
        "sources":sources
    }

    user_query=await memory.get_latest_memory( session_id=session_uuid, read="content",travel=-2)
    bot_response=await memory.get_latest_memory( session_id=session_uuid, read="content")

    doc_content_str = await knowledge_base.knowledge_to_string({"documents":docs})


    llm_body=await llm_adapter.get_llm_detailed_body( kb_data=doc_content_str,user_query=user_query,bot_response=bot_response )
    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    generated_user_query = f'{custom_tags.tags["MOREDETAIL_REQUEST"][0]}Provide me a more detailed response.{custom_tags.tags["MOREDETAIL_REQUEST"][1]}'
    generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":generated_user_query},
        source_list=[]
    )
    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=memory_payload
    )
    session["message_count"]+=1


    background_tasks.add_task( datastore.write_msg,
        session_uuid=session_uuid,
        msg_id=session["message_count"], 
        user_query=generated_user_query, 
        response_content=response_content,
        source=sources
    )


    return {
        "resp":response_content,
        "msgID": session["message_count"] 
    }



# Route to handle chat interactions
@app.post('/chat_api')
async def chat_api_post(request: Request, user_query: Annotated[str, Form()], background_tasks:BackgroundTasks ):
    user_query=user_query

    session = request.session
    session_uuid = request.cookies.get(COOKIE_NAME)
    if session.get("message_count") is None:
        session["message_count"] = 0
        await memory.create_session(session_uuid)
        
    moderation_result,intent_result = await llm_adapter.safety_checks(user_query)

    user_intent=1
    prompt_injection=1
    unrelated_topic=1
    not_handled="I am sorry, your request cannot be handled."
    try:
        data = json.loads(intent_result)
        user_intent=data["user_intent"]
        prompt_injection=data["prompt_injection"]
        unrelated_topic=data["unrelated_topic"]
    except Exception as e:
        print(intent_result)
        print("ERROR", str(e))


    if( moderation_result or (prompt_injection or unrelated_topic)):
        response_content= "I am sorry, your request is inappropriate and I cannot answer it." if moderation_result else not_handled

        session["message_count"] += 1

        generated_user_query = f'{custom_tags.tags["SECURITY_CHECK"][0]}{data}{custom_tags.tags["SECURITY_CHECK"][1]}'
        generated_user_query += f'{custom_tags.tags["OG_QUERY"][0]}{user_query}{custom_tags.tags["OG_QUERY"][1]}'

        background_tasks.add_task( datastore.write_msg,
            session_uuid=session_uuid,
            msg_id=session["message_count"], 
            user_query=generated_user_query, 
            response_content=response_content,
            source=[]
        )

        return {
            "resp":response_content,
            "msgID": session["message_count"]
        }

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"user","content":user_query},
        source_list=[]
    )
    

    docs = await knowledge_base.ann_search(user_query)
    doc_content_str = await knowledge_base.knowledge_to_string(docs)
    
    llm_body = await llm_adapter.get_llm_body( 
        chat_history=await memory.get_session_history_all(session_uuid), 
        kb_data=doc_content_str,
        temperature=.5,
        max_tokens=500 )

    response_content = await llm_adapter.generate_response(llm_body=llm_body)

    await memory.add_message_to_session( 
        session_id=session_uuid, 
        message={"role":"assistant","content":response_content},
        source_list=docs
    )


    session["message_count"]+=1

    background_tasks.add_task( datastore.write_msg,
        session_uuid=session_uuid,
        msg_id=session["message_count"], 
        user_query=user_query, 
        response_content=response_content,
        source=docs["sources"]
    )

    return {
        "resp":response_content,
        "msgID": session["message_count"] 
    }

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)