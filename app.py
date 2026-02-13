import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings, PromptTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
import nest_asyncio
import os
import shutil

# 1. INITIAL SETUP
nest_asyncio.apply()
st.set_page_config(page_title="Engineer Advisor", page_icon="📟")

# 2. THE GATEKEEPER (Simple Login)
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔒 Security Login")
    user = st.text_input("Username").strip()
    pw = st.text_input("Password", type="password").strip()
    
    if st.button("Enter Advisor"):
        if pw == st.secrets["admin_password"]:
            st.session_state['auth'] = True
            st.rerun()
        else:
            st.error("Access Denied")
    st.stop()

# 3. CONFIGURE AI
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 4. SIDEBAR (Admin Tools & Backup)
with st.sidebar:
    st.title("📟 Advisor Tools")
    st.success("Authorized Access")
    
    st.divider()
    
    # --- ADMIN UPLOAD ---
    st.subheader("📁 Add New Manuals")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        if not os.path.exists("./manuals"):
            os.makedirs("./manuals")
        with open(os.path.join("./manuals", uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Saved {uploaded_file.name}!")
        st.info("Refresh page to re-index (Note: This will take time).")

    st.divider()

    # --- BACKUP BRAIN TO PHONE ---
    st.subheader("📦 System Backup")
    if st.button("Prepare Backup for GitHub"):
        storage_path = "./storage"
        if os.path.exists(storage_path):
            # Create a zip file of the storage folder
            shutil.make_archive("storage_backup", 'zip', storage_path)
            with open("storage_backup.zip", "rb") as f:
                st.download_button(
                    label="💾 Download storage.zip",
                    data=f,
                    file_name="storage.zip",
                    mime="application/zip"
                )
        else:
            st.error("No 'storage' folder found. Wait for parsing to finish.")

    st.divider()
    if st.button("Logout"):
        st.session_state['auth'] = False
        st.rerun()

# 5. DATA ENGINE
@st.cache_resource
def get_advisor_index():
    if not os.path.exists("./manuals"):
        os.makedirs("./manuals")
    
    storage_path = "./storage"
    
    # Check if the folder exists AND isn't empty
    if os.path.exists(storage_path) and len(os.listdir(storage_path)) > 0:
        try:
            # Try to load the existing brain
            sc = StorageContext.from_defaults(persist_dir=storage_path)
            return load_index_from_storage(sc)
        except Exception as e:
            # If the folder is corrupted, delete it and start over
            st.warning(f"Storage corrupted, rebuilding: {e}")
            shutil.rmtree(storage_path)
    
    # If we get here, we need to build a new brain
    parser = LlamaParse(result_type="markdown")
    file_extractor = {".pdf": parser}
    documents = SimpleDirectoryReader("./manuals", file_extractor=file_extractor).load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=storage_path)
    return index


index = get_advisor_index()
query_engine = index.as_query_engine(similarity_top_k=8)

# SET THE PROMPT
new_summary_tmpl_str = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, "
    "answer the query as a lead security engineer. Provide full, detailed, "
    "step-by-step instructions. If there is a wiring diagram described, "
    "list every terminal connection. Do not summarize; be exhaustive.\n"
    "Query: {query_str}\n"
    "Answer: "
)
new_summary_tmpl = PromptTemplate(new_summary_tmpl_str)
query_engine.update_prompts({"response_synthesizer:text_qa_template": new_summary_tmpl})

# 6. SEARCH INTERFACE
st.title("📟 Engineer Search")
query = st.text_input("Describe the fault or ask a question:")

if query:
    with st.spinner("Analyzing manuals..."):
        response = query_engine.query(query)
        st.markdown("### 🛠 Solution")
        st.success(response.response)
        
        for node in response.source_nodes:
            st.info(f"Source: {node.metadata.get('file_name')} (Page {node.metadata.get('page_label', 'N/A')})")
