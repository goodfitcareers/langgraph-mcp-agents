import os
import streamlit as st
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()
client = MultiServerMCPClient.from_file("mcp-config.yaml")

st.set_page_config(page_title="Resume Automation", layout="wide")

st.title("Resume Automation System")

tabs = st.tabs(["Upload", "Review", "Database", "Export"])

with tabs[0]:
    uploaded = st.file_uploader("Upload Resume", type=["pdf", "docx", "txt"])
    client_id = st.text_input("Client Name")
    if st.button("Process") and uploaded:
        path = os.path.join("uploads", uploaded.name)
        os.makedirs("uploads", exist_ok=True)
        with open(path, "wb") as f:
            f.write(uploaded.read())
        text = client.call("document-processor", "extract_text", document_path=path)
        st.session_state["latest_text"] = text
        st.success("Document processed")

with tabs[1]:
    st.text_area("Extracted Text", st.session_state.get("latest_text", ""), height=300)
    if st.button("Approve"):
        st.success("Approved (mock)")

with tabs[2]:
    st.write("Notion entries would appear here.")

with tabs[3]:
    st.write("Export functions go here.")

