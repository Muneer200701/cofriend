import streamlit as st
from google import genai
from PIL import Image
import requests
import prompts

# 1. Page setup
st.set_page_config(page_title="cofriend", page_icon="🥗")



# 2. Create a "switch" in memory to track if they finished onboarding
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

# ==========================================
# SCREEN 1: ONBOARDING
# ==========================================
if not st.session_state.onboarded:
    st.title("Welcome to cofriend 🫂")
    st.write("Let's get set up so I can send your food summaries to your Telegram.")

    name = st.text_input("What is your name?")
    chat_id = st.text_input("What is your Telegram Chat ID?")

    if st.button("Start Tracking"):
        if name and chat_id:
            # Save their details
            st.session_state.user_name = name
            st.session_state.chat_id = chat_id
            # Flip the switch!
            st.session_state.onboarded = True
            # Refresh the page instantly
            st.rerun() 
        else:
            st.error("Please fill in both fields!")

# ==========================================
# SCREEN 2: THE CHAT INTERFACE
# ==========================================
else:
    st.title("cofriend 🫂")

    # Connect to Gemini
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # TEMPORARY CODE TO FIND YOUR MODEL NAME
    st.write("### Your Available Models:")
    for m in client.models.list():
        st.write(m.name)

    # Initialize chat history using their actual name!
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "model", "content": prompts.WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.user_name)}
        ]

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Upload & Chat boxes
    uploaded_file = st.file_uploader("Snap or upload a photo of your meal 📸", type=["jpg", "jpeg", "png"])
    user_text = st.chat_input("Tell me what you ate...")

    if user_text:
        # Show user message
        st.session_state.chat_history.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        # Prepare data
        contents = [user_text]
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            contents.append(img)

        # Get AI response
        with st.chat_message("model"):
            loading = st.empty()
            loading.write("Analyzing your food... 🔍")
            try:
               response = client.models.generate_content(
                model="gemini-pro-latest",
                contents=contents,
                config={"system_instruction": prompts.SYSTEM_PROMPT}
              )
            
               loading.write(response.text)
               st.session_state.chat_history.append({"role": "model", "content": response.text})
            except Exception as e:
                    # If Google's servers are busy, show a polite message instead of crashing
                    loading.error("Google's AI servers are a bit overloaded right now! Please wait 30 seconds and try again. 🚦")

    # ==========================================
    # TELEGRAM SUMMARY BUTTON
    # ==========================================
    st.divider() 
    
    if st.button("✈️ Send Summary to Telegram"):
        with st.spinner("Writing your summary..."):
            
            # 1. Ask Gemini to read the history and summarize it
            summary_response = client.models.generate_content(
                model="gemini-pro-latest",
                contents=[str(st.session_state.chat_history), prompts.SUMMARY_REQUEST_PROMPT]
            )
            
            # 2. Send to Telegram using a simple web request
            bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
            user_chat_id = st.session_state.chat_id
            message_text = f"Hi {st.session_state.user_name}!\n\n{summary_response.text}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": user_chat_id, "text": message_text}
            
            try:
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    st.success("✅ Summary sent to your Telegram!")
                else:
                    st.error(f"Failed to send. Telegram said: {res.text}")
            except Exception as e:
                st.error(f"Error connecting to Telegram: {e}")