from fastapi import FastAPI, Request
import httpx, uvicorn, asyncio

app = FastAPI()
BACKEND = "http://127.0.0.1:8082/v1/messages?beta=true"

async def call_backend(payload):
    async with httpx.AsyncClient() as client:
        return await client.post(BACKEND, json=payload, timeout=60)

@app.post("/v1/models/{model_id:path}/generate")
async def translate(model_id: str, req: Request):
    body = await req.json()
    if "messages" in body:
        payload = {"model": model_id, "messages": body["messages"]}
    elif "input" in body or "prompt" in body:
        text = body.get("input") or body.get("prompt")
        payload = {"model": model_id, "messages": [{"role":"user","content": text}]}
    else:
        payload = {"model": model_id, **body}
    for attempt in range(5):
        r = await call_backend(payload)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 503:
            await asyncio.sleep(min(2**attempt, 30))
            continue
        return r.json()
    return {"error":"upstream overloaded after retries"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8083)
