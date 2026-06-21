import textstat

def get_flesch(text):
    return textstat.flesch_reading_ease(text)

def analyze(text):
    score = get_flesch(text)
    grade = textstat.flesch_kincaid_grade(text)

    if score >= 90:
        label = "Very Easy"
    elif score >= 70:
        label = "Easy"
    elif score >= 50:
        label = "Fairly Easy"
    elif score >= 30:
        label = "Difficult"
    else:
        label = "Very Difficult"

    return {
        "flesch_reading_ease": score,
        "grade_level": grade,
        "readability_label": label
    }