import openai
import streamlit as st
from openai import OpenAI
import time

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

assistants = {
    "seans chat": "asst_i2G0tKzk078avpQRVDHaBSCn"
}

def ensure_single_thread_id():
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
    return st.session_state.thread_id

def get_filename(file_id):
    try:
        file_metadata = client.files.retrieve(file_id)
        filename = file_metadata.filename
        return filename
    except Exception as e:
        print(f"Error retrieving file: {e}")
        return None
    
def format_citation(annotation):
    file_id = annotation.file_citation.file_id
    filename = get_filename(file_id)
    if filename:
        citation_info = f" **{filename}** "
    else:
        citation_info = "[Citation from an unknown file]"
    return citation_info

def stream_generator(prompt, thread_id, assistant_id):
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    with st.spinner("Wait... Generating response..."):
        stream = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            stream=True,
            max_prompt_tokens=40000          
        )
        partial_response = ""
        for event in stream:
            if event.data.object == "thread.message.delta":
                print(event)
                for content in event.data.delta.content:
                    if content.type == 'text':
                        text_value = content.text.value
                        annotations = content.text.annotations
                        if annotations:
                            for annotation in annotations:
                                citation_info = format_citation(annotation)
                                indexes = f"from index {annotation.start_index} to {annotation.end_index}]"
                                text_value = f"{citation_info}"
                        partial_response += text_value
                        words = partial_response.split(' ')
                        for word in words[:-1]:
                            yield word + ' '
                        partial_response = words[-1]
            else:
                pass
        if partial_response:
            yield partial_response

# Streamlit interface
st.set_page_config(page_icon="📖")
st.title("Discuss Guru Knowledge Base With ChatGPT")
st.subheader("Be wary that ChatGPT often makes mistakes and fills in the gaps with its own reasoning. Verify its responses using the provided citation links.")

# Dropdown to select the assistant
selected_assistant_name = st.selectbox("Select an Assistant", list(assistants.keys()))
selected_assistant_id = assistants[selected_assistant_name]

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Enter your message")
if prompt:
    thread_id = ensure_single_thread_id()
    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response_container = st.empty()
        full_response = ""
        for chunk in stream_generator(prompt, thread_id, selected_assistant_id):
            full_response += chunk
            response_container.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

