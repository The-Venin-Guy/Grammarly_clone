from grammar_model import run_tagged_prompt

MODES = {
    "Academic": {
        "instruction": (
            "Rewrite the following text in an academic tone. Preserve every fact and the "
            "overall meaning exactly. Do not add or remove information."
        ),
        "example": (
            "Original: For me,arguments tend to become very accusatory and very defensive. It is one of the banes of emotional argumentators. \n"
            "<answer>In my experience, such arguments often become accusatory and defensive, which I find challenging to navigate.</answer>"
        ),
    },
    "Professional": {
        "instruction": (
            "Rewrite the following text in a professional, workplace-appropriate tone. "
            "Preserve every fact and the overall meaning exactly."
        ),
        "example": (
            "Original: your work on this was kinda sloppy, fix it\n"
            "<answer>There are a few areas in this work that need improvement. "
            "Could you please revise it?</answer>"
        ),
    },
    "Concise": {
        "instruction": (
            "Rewrite the following text to be as concise as possible, removing redundant "
            "words and filler. Preserve every distinct fact and idea — do not drop content, "
            "only tighten the wording."
        ),
        "example": (
            "Original: I just wanted to reach out and let you know that, at this point in time, "
            "we are still working on the project and it is going fairly well so far.\n"
            "<answer>We're still working on the project, and it's going well so far.</answer>"
        ),
    },
    "Friendly": {
        "instruction": (
            "Rewrite the following text in a warm, friendly tone, while keeping it polite. "
            "Preserve every fact and the overall meaning exactly."
        ),
        "example": (
            "Original: The deadline is Friday. Submit your work by then.\n"
            "<answer>Just a friendly reminder that the deadline is Friday — looking forward "
            "to seeing your work!</answer>"
        ),
    },
    "Persuasive": {
        "instruction": (
            "Rewrite the following text to be more persuasive and compelling, while preserving "
            "every fact exactly. Do not invent claims, statistics, or benefits that are not "
            "already present in the original text."
        ),
        "example": (
            "Original: Our product saves time.\n"
            "<answer>Our product gives you back hours of your day — time you can spend "
            "on what actually matters.</answer>"
        ),
    },
}

async def transform_text(text: str, mode: str) -> str:
    config = MODES[mode]
    return await run_tagged_prompt(config["instruction"], config["example"], text)