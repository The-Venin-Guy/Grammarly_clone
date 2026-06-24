import httpx

BASE_URL = "http://localhost:11434"

SYSTEM_MESSAGE = (
    "You are a precise text-editing tool. You only ever respond with the exact text requested, "
    "wrapped in <answer></answer> tags, and nothing else. You never add explanations, notes, "
    "greetings, or commentary of any kind, inside or outside the tags."
)

def estimate_tokens(text: str) -> int:
    return max(80, int(len(text.split()) * 3) + 30)

async def ollama_generate(prompt: str, max_tokens: int = 150) -> str:
    payload = {
        "model": "phi3.5:latest",
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt}
        ],
        "options": {"temperature": 0.2, "num_predict": max_tokens, "num_ctx": 1024, "top_p": 0.1, "top_k": 10, "repeat_penalty": 1.1},
        "stream": False
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        return ""
    except httpx.HTTPStatusError as e:
        print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        return ""

def extract_primed_answer(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("<answer>"):
        raw = raw[len("<answer>"):]
    if "</answer>" in raw:
        return raw.split("</answer>")[0].strip()
    return None

def sanity_check(original: str, candidate: str) -> str:
    if candidate.count('(') != candidate.count(')'):
        return original.strip()
    if len(candidate) > len(original.strip()) * 1.8 + 20:
        return original.strip()
    return candidate

async def run_tagged_prompt(instruction: str, example: str, sentence: str) -> str:
    prompt = f"{instruction}\n\n{example}\n\nNow do the same for this sentence:\n\n{sentence}"
    raw = await ollama_generate(prompt, max_tokens=estimate_tokens(sentence))
    extracted = extract_primed_answer(raw)
    if extracted is None:
        return sentence.strip()
    return sanity_check(sentence, extracted)

async def correct(sentence: str) -> str:
    instruction = (
        "Fix only the spelling and grammatical errors in this sentence. "
        "Make the smallest possible change. Do not rephrase, restructure, "
        "or change the meaning of any part of the sentence."
    )
    example = "Original: I am so tired, to be hnest.\n<answer>I am so tired, to be honest.</answer>"
    return await run_tagged_prompt(instruction, example, sentence)