import os
import time
import streamlit as st
from openai import OpenAI, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ask AI", page_icon=":material/smart_toy:")


@st.cache_resource
def get_client():
    return OpenAI(
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("API_KEY"),
    )


client = get_client()

# Each behavior is a system prompt that tells the AI how to act
BEHAVIORS = {
    "Assistant": "You are a helpful assistant. Give clear, accurate answers.",
    "Student": "You are a curious student. Answer as a student who is still learning: think out loud, ask follow-up questions, and admit when you are unsure.",
    "Teacher": "You are a patient teacher. Explain step by step with simple examples, then check understanding with a short question.",
    "Comedian": "You are a stand-up comedian. Answer correctly, but add jokes, puns, and playful exaggeration.",
    "Doctor": "You are a friendly doctor. Explain health topics in plain language and remind the user to see a real doctor for diagnosis or treatment.",
    "Chef": "You are an enthusiastic chef. Relate answers to cooking when you can, and give recipes with ingredients and steps.",
    "Motivational coach": "You are an energetic motivational coach. Encourage the user, stay positive, and end with an action they can take today.",
    "Software engineer": "You are a senior software engineer. Give practical, precise answers with code examples when useful.",
    "Storyteller": "You are a storyteller. Answer by weaving the information into a short, vivid story.",
    "Pirate": "You are a pirate captain. Answer correctly, but talk like a pirate with lots of 'Arr' and sea slang.",
}


def stream_answer(stream, status=None, thinking_box=None):
    """Yield only the answer text; if a status box is given, show the model's thinking in it."""
    thinking = ""
    start = time.time()
    answering = False
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning", None)
        if reasoning and thinking_box:
            thinking += reasoning
            thinking_box.markdown(thinking)
        if delta.content:
            if status and not answering:
                answering = True
                status.update(label=f"Thought for {time.time() - start:.0f} seconds", state="complete")
            yield delta.content


# Remember the conversation between reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Ask AI")
st.caption(f"Model: {os.getenv('MODEL')}")

behavior = st.selectbox("Behavior", list(BEHAVIORS))

with st.container(horizontal=True, vertical_alignment="center"):
    think = st.toggle("Think before answering (much slower)")
    if st.button("New chat", icon=":material/refresh:"):
        st.session_state.messages = []
        st.rerun()

# Show the conversation so far
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your question", submit_mode="disable"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = thinking_box = None
        if think:
            with st.status(":shimmer[Thinking]", type="compact") as status:
                thinking_box = st.empty()
        try:
            # Send the behavior first, then the whole history so the AI remembers earlier messages
            system = {"role": "system", "content": BEHAVIORS[behavior]}
            stream = client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=[system] + st.session_state.messages,
                stream=True,
                # "none" turns off thinking in Ollama; small models can think for minutes
                reasoning_effort="medium" if think else "none",
            )
            answer = st.write_stream(stream_answer(stream, status, thinking_box))
            if answer:
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.warning("The model didn't give an answer. Try again or rephrase.")
                st.session_state.messages.pop()
        except APIConnectionError:
            if status:
                status.update(label="Failed", state="error")
            st.error(
                "Start Ollama with `ollama serve` (or open the Ollama app), then try again.",
                title="Can't reach the AI server",
            )
            st.session_state.messages.pop()  # drop the unanswered question
