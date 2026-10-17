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
            # Send the whole history so the AI remembers earlier messages
            stream = client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=st.session_state.messages,
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
