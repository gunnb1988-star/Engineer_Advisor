import streamlit as st
import streamlit_authenticator as stauth
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
import nest_asyncio
import os

# 1. SETUP
nest_asyncio.apply()
st.set_page_config(page_title="Engineer Advisor", page_icon="📟")

# 2. PULL SECRETS (This replaces the messy credentials list)
# It looks for the [credentials] section you pasted into the dashboard
authenticator = stauth.Authenticate(
    dict(st.secrets['credentials']), 
    "engineer_advisor_session", 
    "signature_key_99", 
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login("Login to Engineer Advisor", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status == None:
    st.info("Authorized access only. Please log in.")
    st.stop()

# 3. SET API KEYS FROM SECRETS
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]

# AI Brain Config
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 4. INTERFACE & SIDEBAR
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png")
    st.title("Engineer Advisor")
    st.write(f"Logged in: **{name}**")
    
    # Check if user is an admin for uploading
    if username in ["admin_user", "joe_hutchings"]:
        st.divider()
        uploaded_file = st.file_uploader("Upload new manual (PDF)", type="pdf")
        if uploaded_file:
            with open(os.path.join("manuals", uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Manual saved! Please refresh the page.")
            
    authenticator.logout("Logout", "sidebar")

st.title("📟 Engineer Advisor")

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

# 6. SEARCH
query = st.text_input("What is the issue on-site?", placeholder="e.g. factory reset Honeywell Vista")

if query:
    with st.spinner("Searching manuals..."):
        response = query_engine.query(query)
        st.success(response.response)
        
        for node in response.source_nodes:
            file = node.metadata.get('file_name', 'Manual')
            page = node.metadata.get('page_label', 'Unknown')
            st.info(f"Ref: **{file}** (Page {page})")
