import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.models import GenerateRequest, GenerateResponse, ChatRequest, ChatResponse, ChatMessage
from app.engine import get_runner

router = APIRouter()

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

@router.post("/generate")
async def generate(request: GenerateRequest):
    runner = get_runner()
    
    if request.model != runner.get_model_name() and request.model != "mock":
         pass

    # Extract context_id from request input (List[int])
    # We only assume 1 ID for now, as we map ID->Blob.
    input_context_id = None
    if request.context and len(request.context) > 0:
        input_context_id = request.context[0]

    if request.stream:
        async def stream_generator():
            full_response = ""
            final_context_id = None
            
            async for token_or_id in runner.generate_token_stream(request.prompt, context_id=input_context_id):
                if isinstance(token_or_id, int):
                    final_context_id = token_or_id
                    continue
                    
                full_response += token_or_id
                resp = GenerateResponse(
                    model=request.model,
                    created_at=get_utc_now(),
                    response=token_or_id,
                    done=False,
                    context=None
                )
                yield json.dumps(resp.dict()) + "\n"
            
            # Final message
            resp = GenerateResponse(
                model=request.model,
                created_at=get_utc_now(),
                response="",
                done=True,
                context=[final_context_id] if final_context_id else None
            )
            yield json.dumps(resp.dict()) + "\n"
            
        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")
    else:
        full_response = ""
        final_context_id = None
        async for token_or_id in runner.generate_token_stream(request.prompt, context_id=input_context_id):
            if isinstance(token_or_id, int):
                final_context_id = token_or_id
                continue
            full_response += token_or_id
        
        return GenerateResponse(
            model=request.model,
            created_at=get_utc_now(),
            response=full_response,
            done=True,
            context=[final_context_id] if final_context_id else None
        )

@router.post("/chat")
async def chat(request: ChatRequest):
    runner = get_runner()
    
    # Construct prompt from messages
    # IMPORTANT: Since context is stateless, we must ensure we pass ALL history here.
    # The client is responsible for sending full history.
    prompt = ""
    for msg in request.messages:
        prompt += f"{msg.role}: {msg.content}\n"
    prompt += "assistant: "

    if request.stream:
        async def stream_generator():
            async for token in runner.generate_token_stream(prompt):
                resp = ChatResponse(
                    model=request.model,
                    created_at=get_utc_now(),
                    message=ChatMessage(role="assistant", content=token),
                    done=False
                )
                yield json.dumps(resp.dict()) + "\n"
            
            resp = ChatResponse(
                model=request.model,
                created_at=get_utc_now(),
                message=ChatMessage(role="assistant", content=""),
                done=True
            )
            yield json.dumps(resp.dict()) + "\n"

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")
    else:
        full_response = ""
        async for token in runner.generate_token_stream(prompt):
            full_response += token
            
        return ChatResponse(
            model=request.model,
            created_at=get_utc_now(),
            message=ChatMessage(role="assistant", content=full_response),
            done=True
        )
