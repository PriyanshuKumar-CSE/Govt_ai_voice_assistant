# Government Policy Voice Assistant

A phone assistant you can call to ask about Indian government schemes and policies. It listens to the caller, looks up the answer in a set of official policy PDFs, and replies out loud in simple Hinglish.

## How it works

```
caller ──▶ Twilio voice call ──▶ /voice (TwiML) ──▶ /media-stream (WebSocket)
                                                        │
                                       audio in ◀──────┼──────▶ OpenAI Realtime API
                                                        │
                              question text ──▶ Chroma vector search over policy PDFs
                                                        │
                                       spoken answer ◀─┘ (2–3 sentences, Hinglish)
```

1. **`ingest.py`** reads every PDF in `./data`, splits it into chunks, embeds them with OpenAI embeddings and saves them to a local Chroma database in `./db`.
2. **`main.py`** is a FastAPI server. Twilio calls `/voice`, which tells it to stream the call audio to `/media-stream`. That WebSocket relays audio to the OpenAI Realtime API, and when the caller stops speaking it retrieves the 3 most relevant policy chunks and asks the model to answer from them.
3. **`call_me.py`** uses the Twilio API to place an outbound call to your phone, so you can try the assistant without dialling in.

## Setup

Requirements: Python 3.10+, an OpenAI API key, a Twilio account with a voice-capable number, and a tunnel (Pinggy, ngrok or similar) so Twilio can reach your local server.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys and numbers
```

## Running it

1. Put your policy PDFs in `./data` and build the index:
   ```bash
   python ingest.py
   ```
2. Start the server on port 8000:
   ```bash
   python main.py
   ```
3. Expose port 8000 with your tunnel and set `PUBLIC_BASE_URL` in `.env` to the tunnel's URL.
4. Place a test call to `MY_PHONE_NUMBER`:
   ```bash
   python call_me.py
   ```

## Configuration

All settings are read from `.env`. See [`.env.example`](.env.example) for the full list.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | `main.py`, `ingest.py` | Embeddings and the Realtime voice model |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | `call_me.py` | Twilio API credentials |
| `TWILIO_PHONE_NUMBER` | `call_me.py` | The Twilio number the call comes from |
| `MY_PHONE_NUMBER` | `call_me.py` | The number to call |
| `PUBLIC_BASE_URL` | `call_me.py` | Public URL of the tunnel forwarding to the server |

## Tech stack

Python · FastAPI · WebSockets · OpenAI Realtime API · LangChain · Chroma · Twilio
