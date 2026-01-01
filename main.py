import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# ---------------- SETUP ----------------
load_dotenv()
app = FastAPI()

# ---------------- RAG ----------------
embeddings = OpenAIEmbeddings()
vector_db = Chroma(
    persist_directory="./db",
    embedding_function=embeddings
)

# ---------------- TWILIO VOICE WEBHOOK ----------------
@app.post("/voice")
async def voice(request: Request):
    host = request.url.hostname
    return HTMLResponse(
        content=f"""
<Response>
  <Connect>
    <Stream url="wss://{host}/media-stream"/>
  </Connect>
</Response>
""",
        media_type="application/xml"
    )

# ---------------- MEDIA STREAM ----------------
@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    await ws.accept()
    print("\n🤝 Twilio Connected")

    stream_sid = None
    audio_bytes = 0
    MIN_AUDIO_BYTES = 800  # 100ms
    last_user_text = None
    has_greeted = False

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with websockets.connect(openai_url, extra_headers=headers) as openai_ws:
        print("🧠 OpenAI Realtime Connected")

        # ---------------- SESSION ----------------
        await openai_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": (
                    "You are an Indian Government Policy Voice Assistant.\n"
                    "STRICT RULES (DO NOT BREAK):\n"
                    "1. Speak in simple Hinglish.\n"
                    "2. Answer in ONLY 2 to 3 short sentences.\n"
                    "3. Do NOT give extra details or explanations.\n"
                    "4. Answer ONLY from official policy context.\n"
                    "5. ALWAYS end with exactly: 'Kya aapka koi aur sawal hai?'\n"
                    "6. Do NOT greet again after first message."
                ),
                "voice": "alloy",
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 700
                }
            }
        }))

        # ---------------- GREETING (ONCE) ----------------
        await asyncio.sleep(1)
        greeting = "Namaste! Main sarkari yojna sahayak hoon. Aap apna sawal pooch sakte hain."
        print(f"🤖 AGENT: {greeting}")

        await openai_ws.send(json.dumps({
            "type": "response.create",
            "response": {"instructions": greeting}
        }))
        has_greeted = True

        # ---------------- TWILIO → OPENAI ----------------
        async def twilio_to_openai():
            nonlocal stream_sid, audio_bytes

            async for msg in ws.iter_text():
                data = json.loads(msg)

                if data["event"] == "start":
                    stream_sid = data["start"]["streamSid"]
                    print(f"📡 Stream started: {stream_sid}")

                elif data["event"] == "media":
                    payload = data["media"]["payload"]
                    audio_bytes += len(payload) * 3 // 4

                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": payload
                    }))

        # ---------------- OPENAI → TWILIO + RAG ----------------
        async def openai_to_twilio():
            nonlocal audio_bytes, last_user_text

            async for msg in openai_ws:
                res = json.loads(msg)

                # -------- USER TRANSCRIPT --------
                if res.get("type") == "response.input_text.final":
                    last_user_text = res["text"]
                    print(f"\n🧑 USER: {last_user_text}")

                # -------- AGENT AUDIO --------
                if res.get("type") == "response.audio.delta" and stream_sid:
                    await ws.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": res["delta"]}
                    }))

                # -------- SPEECH END --------
                if res.get("type") == "input_audio_buffer.speech_stopped":

                    if audio_bytes < MIN_AUDIO_BYTES or not last_user_text:
                        audio_bytes = 0
                        continue

                    # ---- RAG SEARCH ----
                    docs = vector_db.similarity_search(last_user_text, k=3)
                    context = "\n\n".join(d.page_content for d in docs)

                    prompt = f"""
Government policy context:
{context}

User question:
{last_user_text}

Answer STRICTLY in 2–3 sentences.
End with: Kya aapka koi aur sawal hai?
"""

                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.commit"
                    }))

                    await openai_ws.send(json.dumps({
                        "type": "response.create",
                        "response": {"instructions": prompt}
                    }))

                    print("🤖 AGENT: (answer spoken)")

                    # ---- KEEP CALL ALIVE ----
                    await openai_ws.send(json.dumps({
                        "type": "response.create",
                        "response": {
                            "instructions": "Main sun raha hoon."
                        }
                    }))

                    audio_bytes = 0
                    last_user_text = None

        await asyncio.gather(
            twilio_to_openai(),
            openai_to_twilio()
        )

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
