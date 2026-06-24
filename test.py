import asyncio
import httpx

OLLAMA_BASE_URL = "http://localhost:11434"

async def test_generate_without_priming_trick():
    sentence = "The name of the btoy is James."
    prompt = (
        "Fix only the spelling and grammatical errors in this sentence. "
        "Make the smallest possible change. Do not rephrase, restructure, "
        "or change the meaning of any part of the sentence.\n\n"
        "Write your full answer between <answer> and </answer> tags. "
        "Put any notes or comments AFTER the closing tag, never inside it.\n\n"
        "Original: I am so tired, to be hnest.\n<answer>I am so tired, to be honest.</answer>\n\n"
        f"Now do the same for this sentence:\n\n{sentence}"
    )
    payload = {
        "model": "phi3.5:latest",
        "prompt": prompt,
        "options": {"temperature": 0.3, "num_predict": 100},
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30)
    raw = response.json().get("response", "")
    print("RAW:", repr(raw))

asyncio.run(test_generate_without_priming_trick())