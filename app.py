import streamlit as st
import streamlit_authenticator as stauth
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
import nest_asyncio
import os

# 1. INITIAL SETUP
nest_asyncio.apply()
st.set_page_config(page_title="Engineer Advisor", page_icon="📟")

# 2. LOGIN SYSTEM
authenticator = stauth.Authenticate(
    dict(st.secrets['credentials']), 
    st.secrets['cookie']['name'], 
    st.secrets['cookie']['key'], 
    st.secrets['cookie']['expiry_days'],
    auto_hash=False
)

# Render the login box
authenticator.login(location="main")

# Check authentication status
if st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.info("Authorized access only. Please log in.")
    st.stop()

# Set user variables
name = st.session_state["name"]
username = st.session_state["username"]

# 3. CONFIGURE AI BRAIN
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 4. SIDEBAR & ADMIN TOOLS
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png")
    st.title("Engineer Advisor")
    st.write(f"Logged in: **{name}**")
    
    if username in ["admin_user", "joe_hutchings"]:
        st.divider()
        st.subheader("Admin: Add Manuals")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            if not os.path.exists("manuals"):
                os.makedirs("manuals")
            with open(os.path.join("manuals", uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File saved! Refresh the page.")
            
    authenticator.logout("Logout", "sidebar")

# 5. SEARCH ENGINE
st.title("📟 Engineer Advisor")

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
query = st.text_input("How can I help you on-site?", placeholder="e.g. reset Honeywell Vista")

if query:
    with st.spinner("Consulting manuals..."):
        response = query_engine.query(query)
        st.markdown("### 🛠 Solution")
        st.success(response.response)
        
        st.markdown("### 📄 Source Documentation")
        # Fixed syntax for the source loop
        for node in response.source_nodes:
            metadata = node.metadata
            file_name = metadata.get('file_name', 'Manual')
            page_num = metadata.get('page_label', 'Unknown')
            st.info(f"Ref: **{file_name}** (Page {page_num})")
