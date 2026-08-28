import json

from google import genai
from google.genai import types

import streamlit as st


GEMINI_MODEL = "gemini-3.6-flash"


def get_gemini_client():
    """
    Create the Gemini API client using the API key
    stored securely in Streamlit secrets.
    """

    try:
        api_key = st.secrets[
            "GEMINI_API_KEY"
        ]

    except Exception:
        raise RuntimeError(
            "GEMINI_API_KEY was not found in "
            ".streamlit/secrets.toml"
        )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is empty."
        )

    return genai.Client(
        api_key=api_key
    )


def ask_ai_coach(
    question,
    profile,
    workout_plan,
    workout_history,
):
    """
    Ask Gemini for personalized workout guidance.
    """

    context = {
        "profile": profile,
        "workout_plan": workout_plan,
        "recent_workout_history": (
            workout_history[-10:]
        ),
    }

    system_prompt = """
You are the AI coach inside a Personal Workout Trainer app.

Your job is to provide practical, personalized fitness guidance
based on the user's profile, workout plan, and workout history.

Important rules:

- Be concise and practical.
- Use the user's available equipment and fitness level.
- Respect the user's stated exercises to avoid.
- Do not invent workout history or personal information.
- Do not diagnose injuries or medical conditions.
- If the user mentions significant pain, injury, dizziness,
  chest pain, breathing difficulty, or other concerning symptoms,
  recommend stopping the exercise and consulting an appropriate
  healthcare professional.
- When suggesting exercise changes, explain the reason briefly.
- Focus on progressive overload, consistency, recovery,
  exercise technique, and appropriate training volume.
- Answer the user's actual question directly.
- Do not unnecessarily repeat the entire profile.
- Keep responses easy to read inside a Streamlit application.
"""

    user_prompt = f"""
Here is the user's current training information:

{json.dumps(
    context,
    indent=2,
    ensure_ascii=False,
)}

User's question:

{question}
"""

    client = get_gemini_client()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1200,
        ),
    )

    answer = response.text

    if not answer:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return answer.strip()