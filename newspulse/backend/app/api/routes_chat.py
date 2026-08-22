"""Chat endpoints: /chat, /chat/stream, and /chat/{session_id}/history."""

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession
from app.db.session import get_sync_session, get_sync_session_factory
from app.rag.llm_client import ask, _get_client
from app.rag.prompt_builder import build_prompt, CitationSource
from app.retrieval.reranker import retrieve
from app.config import settings
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    category_filter: str | None = None
    top_k: int = 10


class CitationOut(BaseModel):
    index: int
    source: str
    url: str
    published_at: str | None = None
    title: str | None = None
    image_url: str | None = None
    summary: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[CitationOut]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_sync_session)):
    # Get or create chat session
    if request.session_id:
        chat_session = session.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        ).scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        chat_session = ChatSession()
        session.add(chat_session)
        session.flush()

    # Store user message
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=request.query,
    )
    session.add(user_msg)

    # Retrieve relevant chunks
    results = []
    try:
        results = retrieve(
            query=request.query,
            final_top_k=request.top_k,
            category_filter=request.category_filter,
        )
    except Exception as e:
        logger.warning("Retrieval failed: %s", e)

    if not results:
        answer_text = "I couldn't find any relevant articles to answer your question. Try rephrasing or broadening your query."
        citations_out = []
    else:
        # Generate RAG answer
        try:
            response = ask(request.query, results)
            answer_text = response.answer
            citations_out = [
                CitationOut(
                    index=c.index,
                    source=c.source,
                    url=c.url,
                    published_at=c.published_at,
                    title=getattr(c, "title", None) or f"{c.source} Report",
                    image_url=getattr(c, "image_url", None),
                    summary=getattr(c, "summary", None),
                )
                for c in response.citations_used
            ]
        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            answer_text = "I found relevant articles but couldn't generate an answer right now. Please try again later."
            citations_out = []

    # Store assistant message
    assistant_msg = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=answer_text,
        citations_json=json.dumps([c.model_dump() for c in citations_out]) if citations_out else None,
    )
    session.add(assistant_msg)
    session.commit()

    return ChatResponse(
        session_id=str(chat_session.id),
        answer=answer_text,
        citations=citations_out,
    )


@router.post("/stream")
def chat_stream(request: ChatRequest):
    """Stream RAG response token by token via Server-Sent Events (SSE)."""
    session_factory = get_sync_session_factory()
    with session_factory() as session:
        # Get or create chat session
        if request.session_id:
            chat_session = session.execute(
                select(ChatSession).where(ChatSession.id == request.session_id)
            ).scalar_one_or_none()
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            chat_session = ChatSession()
            session.add(chat_session)
            session.flush()

        session_id_str = str(chat_session.id)

        # Store user message
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=request.query,
        )
        session.add(user_msg)
        session.commit()

    def event_generator():
        # First send session_id immediately so client is connected in < 10ms
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id_str})}\n\n"

        # Retrieve relevant chunks inside stream
        results = []
        try:
            results = retrieve(
                query=request.query,
                final_top_k=request.top_k,
                category_filter=request.category_filter,
            )
        except Exception as e:
            logger.warning("Retrieval failed in stream: %s", e)

        if not results:
            no_info_msg = "I couldn't find any relevant articles to answer your question. Try rephrasing or broadening your query."
            yield f"data: {json.dumps({'type': 'token', 'token': no_info_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'citations': []})}\n\n"
            
            # Save assistant message
            session_factory = get_sync_session_factory()
            with session_factory() as s:
                s.add(ChatMessage(session_id=session_id_str, role="assistant", content=no_info_msg, citations_json=None))
                s.commit()
            return

        system_prompt, user_message, citations = build_prompt(request.query, results)
        
        full_tokens = []
        candidate_models = [
            "models/gemini-3.5-flash-lite",
            "models/gemini-flash-lite-latest",
            settings.llm_model,
            "models/gemini-flash-latest",
        ]
        # Deduplicate
        candidate_models = [m for i, m in enumerate(candidate_models) if m and m not in candidate_models[:i]]

        streamed_successfully = False
        for model_name in candidate_models:
            try:
                client = _get_client()
                stream = client.models.generate_content_stream(
                    model=model_name,
                    contents=f"{system_prompt}\n\n{user_message}",
                    config=GenerateContentConfig(
                        max_output_tokens=2048,
                        temperature=0.3,
                    ),
                )
                for chunk in stream:
                    token = chunk.text or ""
                    if token:
                        full_tokens.append(token)
                        yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                streamed_successfully = True
                break
            except Exception as e:
                logger.warning("Streaming with model '%s' failed (%s), attempting fallback...", model_name, e)
                full_tokens.clear()

        if not streamed_successfully:
            from app.rag.llm_client import synthesize_extractive_briefing
            logger.info("All LLM streaming models busy/rate-limited, streaming real-time extractive briefing...")
            briefing_text, ext_citations = synthesize_extractive_briefing(request.query, results)
            # Stream words with small natural cadence
            words = briefing_text.split(" ")
            for i, w in enumerate(words):
                sep = " " if i < len(words) - 1 else ""
                piece = w + sep
                full_tokens.append(piece)
                yield f"data: {json.dumps({'type': 'token', 'token': piece})}\n\n"
            citations_used = ext_citations
            used_indices = set(range(1, len(ext_citations) + 1))
        else:
            accumulated_text = "".join(full_tokens)
            used_indices = set(int(m) for m in re.findall(r"\[(\d+)\]", accumulated_text))
            citations_used = [c for c in citations if c.index in used_indices]

        accumulated_text = "".join(full_tokens)
        citations_out = [
            CitationOut(
                index=c.index,
                source=c.source,
                url=c.url,
                published_at=c.published_at,
                title=getattr(c, "title", None) or f"{c.source} Report",
                image_url=getattr(c, "image_url", None),
                summary=getattr(c, "summary", None),
            ).model_dump()
            for c in citations_used
        ]

        yield f"data: {json.dumps({'type': 'done', 'citations': citations_out})}\n\n"

        # Save assistant message to database
        session_factory = get_sync_session_factory()
        with session_factory() as s:
            s.add(ChatMessage(
                session_id=session_id_str,
                role="assistant",
                content=accumulated_text,
                citations_json=json.dumps(citations_out) if citations_out else None,
            ))
            s.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class SessionOut(BaseModel):
    id: str
    created_at: datetime
    first_query: str | None = None
    message_count: int = 0


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(session: Session = Depends(get_sync_session)):
    """List recent chat sessions with first query preview."""
    sessions = session.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).limit(30)
    ).scalars().all()

    result = []
    for s in sessions:
        msgs = session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at)
        ).scalars().all()
        first_q = None
        for m in msgs:
            if m.role == "user":
                first_q = m.content[:60]
                break
        result.append(SessionOut(
            id=str(s.id),
            created_at=s.created_at,
            first_query=first_q or "New Conversation",
            message_count=len(msgs),
        ))
    return result


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str, session: Session = Depends(get_sync_session)):
    # First delete all messages associated with this session
    session.execute(
        delete(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    # Then delete the session itself
    result = session.execute(
        delete(ChatSession).where(ChatSession.id == session_id)
    )
    session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[CitationOut] | None = None
    created_at: datetime


@router.get("/{session_id}/history", response_model=list[MessageOut])
def get_history(session_id: str, session: Session = Depends(get_sync_session)):
    messages = session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")

    result = []
    for msg in messages:
        citations = None
        if msg.citations_json:
            citations = [CitationOut(**c) for c in json.loads(msg.citations_json)]
        result.append(MessageOut(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            citations=citations,
            created_at=msg.created_at,
        ))
    return result
