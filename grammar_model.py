import httpx
import re

BASE_URL = "http://localhost:11434"

async def ollama_generate(prompt: str) -> str:
    payload = {
        "model": "phi3.5:latest",
        "prompt": prompt,
        "options": {"temperature": 0.2, "num_predict": 60, "num_ctx": 1024, "top_p": 0.1, "repeat_penalty": 1.1},
        "stream": False,
        "keep_alive": "30m"
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

async def correct(sentence: str) -> str:
    prompt = (
        "Fix only the spelling and grammatical errors in this sentence. "
        "Make the smallest possible change — fix a misspelled word by replacing it with the correctly spelled word only. "
        "Do not rephrase, restructure, or change the meaning of any part of the sentence. "
        "Do not add any commentary, notes, or parenthetical remarks about whether changes were needed. "
        "Example:\n"
        "Original: I am so tired, to be hnest.\n"
        "Corrected: I am so tired, to be honest.\n\n"
        "Now correct this sentence the same way. "
        "Return only the corrected sentence with no explanation, notes, or commentary of any kind:\n\n"
        f"{sentence}"
    )
    corrected_text = await ollama_generate(prompt)
    corrected_text = strip_explanation(corrected_text)
    return corrected_text.strip()

def strip_explanation(text: str) -> str:
    """
    Removes trailing parenthetical commentary the LLM sometimes adds
    despite being told not to (e.g. "(The original was already correct.)").
    Safety net — prompt instructions alone aren't fully reliable.
    """
    text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
    return text.strip()