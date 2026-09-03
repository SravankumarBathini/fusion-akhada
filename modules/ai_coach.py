import os
import json
import streamlit as st
from google import genai
from google.genai import types

# Using the active production model designation
GEMINI_MODEL = "gemini-3.6-flash"

def ask_ai_coach(question: str, profile: dict, workout_plan: list, workout_history: list) -> str:
    """
    Analyzes conversation context. If the user explicitly asks to modify, update, 
    add, or swap exercises in their workout, the model outputs a structured update 
    command alongside a conversational response.
    """
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return "**AI Coach Offline:** Missing `GEMINI_API_KEY`. Please configure it in your environment or Streamlit Secrets dashboard to unlock your AI Coach."

    client = genai.Client(api_key=api_key)

    # 1. Provide an elite master trainer persona that can update plans on the fly
    system_prompt = f"""
    You are an elite master strength coach specializing in Hybrid Functional Training (Western & traditional Indian Vyayam/Akhada culture).
    You have direct authority to modify the user's active workout plan based on your conversation.
    
    ATHLETE PROFILE DATA:
    - Goals: {profile.get('fitness_goal', 'General Fitness')}
    - Level: {profile.get('fitness_level', 'Intermediate')}
    - Equipment: {profile.get('equipment', ['Bodyweight'])}
    - Physical Injuries/Limitations: {profile.get('physical_injuries', 'None')}
    - Exercises to Avoid: {profile.get('exercises_to_avoid', 'None')}
    
    CURRENT ACTIVE WORKOUT PLAN:
    {json.dumps(workout_plan, indent=2)}

    CRITICAL INSTRUCTIONS:
    Evaluate the user's input message. 
    - If they are simply asking a general question, return a supportive answer and leave `updated_workout_plan` as null.
    - If they ask to update, add, delete, replace, or modify an exercise or day in their routine (e.g., "replace dands with floor press", "add gada swings to day 1"), you MUST rewrite the relevant parts of the workout plan JSON schema while respecting their injury profile.
    
    You must respond strictly in this JSON format:
    {{
        "coach_response": "Your conversational reply to the user explaining what changes were made or answering their question.",
        "requires_plan_update": true (set to true ONLY if they commanded a change, false otherwise),
        "updated_workout_plan": [ ... The entire updated workout plan array matching the exact incoming JSON list structure with your modified exercises, sets, or reps injected ... ] or null if no change requested.
    }}
    """

    try:
        # Request strict structured JSON mapping from Gemini
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system_prompt}\n\nUser Message: {question}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Parse the AI response block
        result = json.loads(response.text)
        coach_reply = result.get("coach_response", "Routines processed successfully.")
        
        # 2. Check if a dynamic plan mutation command was triggered
        if result.get("requires_plan_update") and result.get("updated_workout_plan"):
            st.session_state.workout_plan = result["updated_workout_plan"]
            
            # Persist changes dynamically based on the current storage source
            from utils.storage import save_workout_plan_to_supabase
            profile_id = st.session_state.get("profile_id")
            
            if not profile_id or st.session_state.get("storage_source") != "supabase":
                raise RuntimeError("Supabase is required to update the workout plan.")

            saved_plan = save_workout_plan_to_supabase(
                profile_id,
                result["updated_workout_plan"],
            )
            if not saved_plan:
                raise RuntimeError("Supabase did not save the updated workout plan.")
                
            coach_reply += "\n\n*System Note: Your active 'My Workout' logging table has been updated dynamically!*"
            
        return coach_reply
        
    except Exception as e:
        return f"**AI Coach Exception:** Failed to parse context or execute conversational overrides. Details: {str(e)}"

def render_ai_coach_dashboard_ui(metrics, workout_name):
    import streamlit as st
    st.write("---")
    st.markdown("### 🤖 Akhada AI Telemetry Check")
    st.caption(f"Analyzing metrics parameters for active track: **{workout_name}**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Target RPE Load", f"{metrics.get('rpe', 7)}/10")
    c2.metric("Soreness Delta", f"{metrics.get('soreness', 2)}/5")
    c3.metric("Energy Capacity", f"{metrics.get('energy', 3)}/5")
    st.info("💡 **Coach Advice:** Head over to your dedicated **AI Coach** tab panel to casually command changes, replace movements, or adjust your traditional Vyayam sets via text chat instantly!")