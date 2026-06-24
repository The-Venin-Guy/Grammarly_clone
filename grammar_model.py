import re
import httpx

BASE_URL = "http://localhost:11434"

def estimate_tokens(text: str) -> int:
    """Scales the output budget to input length, so complex sentences aren't truncated mid-generation."""
    return max(80, int(len(text.split()) * 3) + 30)

async def ollama_generate(prompt: str, max_tokens: int = 150) -> str:
    payload = {
        "model": "phi3.5:latest",
        "prompt": prompt,
        "options": {"temperature": 0.3, "num_predict": max_tokens},
        "stream": False
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("response", "")
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        return ""
    except httpx.HTTPStatusError as e:
        print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        return ""

def extract_tag(raw: str) -> str | None:
    """
    The prompt ends with the literal text '<answer>', so the model's raw
    completion should just be the content, then a closing tag. No closing
    tag = generation was cut off or malformed — a clean, detectable failure.
    """
    if raw.strip().startswith("<answer>"):
        raw = raw.strip()[len("<answer>"):]
    if "</answer>" in raw:
        return raw.split("</answer>")[0].strip()
    return None

def sanity_check(original: str, candidate: str) -> str:
    """Secondary safety net on whatever was successfully extracted."""
    if candidate.count('(') != candidate.count(')'):
        return original.strip()
    if len(candidate) > len(original.strip()) * 1.8 + 20:
        return original.strip()
    return candidate

async def tag_prompt(instruction: str, example: str, sentence: str) -> str:
    """Shared by every rewrite task — grammar, formality, passive, clarity."""
    prompt = (
        f"{instruction}\n\n"
        f"Write ONLY the result between <answer> and </answer> tags. "
        f"Put any notes or comments AFTER the closing tag, never inside it.\n\n"
        f"{example}\n\n"
        f"Now do the same for this sentence:\n\n{sentence}\n\n<answer>"
    )
    raw = await ollama_generate(prompt, max_tokens=estimate_tokens(sentence))
    extracted = extract_tag(raw)
    if extracted is None:
        return sentence.strip()  # closing tag never appeared — fall back safely
    return sanity_check(sentence, extracted)

async def correct(sentence: str) -> str:
    instruction = (
        "Fix only the spelling and grammatical errors in this sentence. "
        "Make the smallest possible change. Do not rephrase, restructure, "
        "or change the meaning of any part of the sentence."
    )
    example = "Original: I am so tired, to be hnest.\n<answer>I am so tired, to be honest.</answer>"
    return await tag_prompt(instruction, example, sentence)