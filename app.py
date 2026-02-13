import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
import nest_asyncio
import os

# 1. INITIAL SETUP
nest_asyncio.apply()
st.set_page_config(page_title="Engineer Advisor", page_icon="📟")

# 2. THE GATEKEEPER (Manual Login)
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔒 Security Login")
    user = st.text_input("Username").strip()
    pw = st.text_input("Password", type="password").strip()
    
    if st.button("Enter Advisor"):
        # This looks for 'admin_password' in your Secrets box
        if pw == st.secrets["admin_password"]:
            st.session_state['auth'] = True
            st.rerun()
        else:
            st.error("Access Denied")
    st.stop()

# 3. CONFIGURE AI (Only runs if logged in)
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 4. SIDEBAR
with st.sidebar:
    st.title("📟 Engineer Advisor")
    st.success("Authorized Access")
    if st.button("Logout"):
        st.session_state['auth'] = False
        st.rerun()

# 5. DATA ENGINE
@st.cache_resource
def get_advisor_index():
    if not os.path.exists("./manuals"):
        os.makedirs("./manuals")
    
    storage_path = "./storage"
    if not os.path.exists(storage_path):
        parser = LlamaParse(result_type="markdown")
        file_extractor = {".pdf": parser}
        documents = SimpleDirectoryReader("./manuals", file_extractor=file_extractor).load_data()
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=storage_path)
        return index
    else:
        sc = StorageContext.from_persist_dir(persist_dir=storage_path)
        return load_index_from_storage(sc)

index = get_advisor_index()
query_engine = index.as_query_engine(similarity_top_k=3)

# 6. SEARCH INTERFACE
st.title("📟 Search Manuals")
query = st.text_input("Describe the fault or ask a question:")

if query:
    with st.spinner("Analyzing manuals..."):
        response = query_engine.query(query)
        st.markdown("### 🛠 Solution")
        st.success(response.response)
        
        for node in response.source_nodes:
            st.info(f"Source: {node.metadata.get('file_name')} (Page {node.metadata.get('page_label')})")
