import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings, PromptTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
import nest_asyncio
import os
import shutil
import hashlib
from datetime import datetime
import json

# ============================================================================
# 1. INITIAL SETUP & CONFIGURATION
# ============================================================================
nest_asyncio.apply()

st.set_page_config(
    page_title="Engineer Advisor",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: 600;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .admin-badge {
        background-color: #ff6b6b;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .user-badge {
        background-color: #4dabf7;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .logo-container {
        text-align: center;
        padding: 1rem 0 2rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    .company-name {
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
        margin-top: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# 2. PASSWORD MANAGEMENT FUNCTIONS
# ============================================================================

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password, stored_hash):
    """Verify password against stored hash"""
    return hash_password(input_password) == stored_hash

def load_custom_passwords():
    """Load custom passwords from file"""
    password_file = "./data/custom_passwords.json"
    if os.path.exists(password_file):
        try:
            with open(password_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_custom_password(username, new_password_hash):
    """Save a custom password for a user"""
    password_file = "./data/custom_passwords.json"
    
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    
    # Load existing custom passwords
    custom_passwords = load_custom_passwords()
    
    # Update with new password
    custom_passwords[username] = new_password_hash
    
    # Save to file
    with open(password_file, 'w') as f:
        json.dump(custom_passwords, f, indent=2)

def get_user_password_hash(username):
    """Get the password hash for a user (custom password takes precedence)"""
    # First check custom passwords
    custom_passwords = load_custom_passwords()
    if username in custom_passwords:
        return custom_passwords[username]
    
    # Fall back to secrets.toml
    users = st.secrets.get("users", {})
    return users.get(username)

def get_user_role(username):
    """Get the role of a user from secrets"""
    try:
        admin_users = st.secrets.get("admin_users", [])
        if username in admin_users:
            return "admin"
        
        users = st.secrets.get("users", {})
        if username in users or username in load_custom_passwords():
            return "user"
        
        return None
    except Exception:
        return None

def is_admin():
    """Check if current user is an admin"""
    return st.session_state.get('user_role') == 'admin'

# ============================================================================
# 3. SESSION STATE INITIALIZATION
# ============================================================================

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'login_attempts' not in st.session_state:
    st.session_state['login_attempts'] = 0
if 'show_password_change' not in st.session_state:
    st.session_state['show_password_change'] = False

# ============================================================================
# 4. LOGO DISPLAY FUNCTION
# ============================================================================

def display_logo():
    """Display company logo if available, otherwise show company name"""
    logo_path = "./assets/company_logo.png"
    
    if os.path.exists(logo_path):
        # Display logo image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_path, use_container_width=True)
    else:
        # Display company name as fallback
        st.markdown("""
            <div class="logo-container">
                <div class="company-name">🔧 Your Company Name</div>
                <div style="color: #7f8c8d; font-size: 1rem;">Engineer Advisor System</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Show info on first load about adding logo
        if 'logo_info_shown' not in st.session_state:
            st.info("💡 **Tip:** Add your company logo as `./assets/company_logo.png` to display it here!")
            st.session_state['logo_info_shown'] = True

# ============================================================================
# 5. LOGIN PAGE
# ============================================================================

if not st.session_state['authenticated']:
    # Display logo at top
    display_logo()
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔒 Secure Access</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Login to access technical manuals</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("🔓 Login")
            
            if submit_button:
                try:
                    # Get password hash for user
                    stored_hash = get_user_password_hash(username)
                    
                    if stored_hash and verify_password(password, stored_hash):
                        # Get user role
                        user_role = get_user_role(username)
                        
                        if user_role:
                            st.session_state['authenticated'] = True
                            st.session_state['username'] = username
                            st.session_state['user_role'] = user_role
                            st.session_state['login_attempts'] = 0
                            
                            role_display = "Administrator" if user_role == "admin" else "Engineer"
                            st.success(f"✅ Welcome, {username}! ({role_display})")
                            st.rerun()
                        else:
                            st.session_state['login_attempts'] += 1
                            st.error("❌ User not found")
                    else:
                        st.session_state['login_attempts'] += 1
                        st.error("❌ Invalid username or password")
                    
                    if st.session_state['login_attempts'] >= 3:
                        st.warning(f"⚠️ Multiple failed attempts detected ({st.session_state['login_attempts']})")
                        
                except Exception as e:
                    st.error("❌ Authentication system error. Please contact administrator.")
        
        # Help section
        with st.expander("ℹ️ Need Help?"):
            st.info("""
            **User Roles:**
            - **Admin**: Can upload files, create backups, manage system, and change passwords
            - **User**: Can search manuals and change own password
            
            **Security Note:**
            - Passwords are hashed using SHA-256
            - You can change your password after logging in
            - Session expires when browser closes
            
            **Contact your administrator if you've forgotten your password.**
            """)
    
    st.stop()

# ============================================================================
# 6. API CONFIGURATION
# ============================================================================

try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]
    
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
except Exception as e:
    st.error(f"❌ API Configuration Error: {str(e)}")
    st.info("Please check your `.streamlit/secrets.toml` file for valid API keys.")
    st.stop()

# ============================================================================
# 7. DISPLAY LOGO ON MAIN APP
# ============================================================================

display_logo()

# ============================================================================
# 8. SIDEBAR - ROLE-BASED CONTROLS
# ============================================================================

with st.sidebar:
    # User info with role badge
    role_badge = f"<span class='admin-badge'>ADMIN</span>" if is_admin() else f"<span class='user-badge'>USER</span>"
    st.markdown(f"### 👤 {st.session_state['username']} {role_badge}", unsafe_allow_html=True)
    st.caption(f"Session started: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    
    # Title
    st.title("📟 Advisor Tools")
    
    # ========================================================================
    # PASSWORD CHANGE (Available to all users)
    # ========================================================================
    st.subheader("🔐 Change Password")
    
    if st.button("🔑 Change My Password"):
        st.session_state['show_password_change'] = not st.session_state['show_password_change']
    
    if st.session_state['show_password_change']:
        with st.form("password_change_form"):
            st.write(f"**Changing password for:** {st.session_state['username']}")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_submit = st.form_submit_button("✅ Update Password")
            
            if change_submit:
                # Verify current password
                current_hash = get_user_password_hash(st.session_state['username'])
                
                if not verify_password(current_password, current_hash):
                    st.error("❌ Current password is incorrect")
                elif len(new_password) < 6:
                    st.error("❌ New password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match")
                else:
                    # Save new password
                    new_hash = hash_password(new_password)
                    save_custom_password(st.session_state['username'], new_hash)
                    st.success("✅ Password changed successfully!")
                    st.info("Your new password will be active immediately.")
                    st.session_state['show_password_change'] = False
                    st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # ADMIN-ONLY SECTIONS
    # ========================================================================
    if is_admin():
        st.success("🔑 Administrator Access")
        st.markdown("---")
        
        # --- ADMIN: FILE UPLOAD ---
        st.subheader("📁 Document Management")
        st.caption("👑 Admin Only")
        
        uploaded_file = st.file_uploader(
            "Upload Technical Manual (PDF)",
            type="pdf",
            help="Upload PDF manuals to expand the knowledge base"
        )
        
        if uploaded_file:
            try:
                if not os.path.exists("./manuals"):
                    os.makedirs("./manuals")
                
                file_path = os.path.join("./manuals", uploaded_file.name)
                
                if os.path.exists(file_path):
                    st.warning(f"⚠️ '{uploaded_file.name}' already exists")
                    if st.button("Overwrite existing file"):
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Updated {uploaded_file.name}")
                        st.info("💡 Clear cache and refresh to re-index")
                else:
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Saved {uploaded_file.name}")
                    st.info("💡 Clear cache and refresh to re-index")
                    
            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")
        
        st.markdown("---")
        
        # --- ADMIN: STORAGE BACKUP ---
        st.subheader("📦 System Backup")
        st.caption("👑 Admin Only")
        
        if st.button("🔄 Prepare Backup"):
            storage_path = "./storage"
            
            if os.path.exists(storage_path) and os.listdir(storage_path):
                try:
                    with st.spinner("Creating backup..."):
                        backup_name = f"storage_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.make_archive(backup_name, 'zip', storage_path)
                        
                        with open(f"{backup_name}.zip", "rb") as f:
                            st.download_button(
                                label="💾 Download Backup",
                                data=f,
                                file_name=f"{backup_name}.zip",
                                mime="application/zip"
                            )
                        st.success("✅ Backup ready!")
                except Exception as e:
                    st.error(f"❌ Backup failed: {str(e)}")
            else:
                st.warning("⚠️ No storage data found. Upload and index files first.")
        
        st.markdown("---")
        
        # --- ADMIN: SYSTEM CONTROLS ---
        st.subheader("⚙️ System Controls")
        st.caption("👑 Admin Only")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Cache"):
                st.cache_resource.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Rebuild Index"):
                if os.path.exists("./storage"):
                    shutil.rmtree("./storage")
                st.cache_resource.clear()
                st.success("Index will rebuild!")
                st.rerun()
    
    # ========================================================================
    # USER SECTIONS
    # ========================================================================
    else:
        st.info("👤 Engineer Access")
        st.caption("Search manuals and manage your password")
        st.markdown("---")
    
    # System status (visible to all)
    st.subheader("📊 System Status")
    
    if os.path.exists("./storage"):
        st.caption("✅ Index: Active")
    else:
        st.caption("⚠️ Index: Not built")
    
    if os.path.exists("./manuals"):
        num_files = len([f for f in os.listdir("./manuals") if f.endswith('.pdf')])
        st.caption(f"📚 Manuals: {num_files} file(s)")
    else:
        st.caption("📚 Manuals: 0 files")
    
    st.markdown("---")
    
    # Logout (available to all)
    if st.button("🚪 Logout"):
        st.session_state['authenticated'] = False
        st.session_state['username'] = None
        st.session_state['user_role'] = None
        st.session_state['show_password_change'] = False
        st.rerun()

# ============================================================================
# 9. DATA ENGINE - INDEX MANAGEMENT
# ============================================================================

@st.cache_resource
def get_advisor_index():
    """Build or load the vector index from manuals"""
    
    if not os.path.exists("./manuals"):
        os.makedirs("./manuals")
    
    storage_path = "./storage"
    
    # Try to load existing index
    if os.path.exists(storage_path) and len(os.listdir(storage_path)) > 0:
        try:
            st.info("📚 Loading existing index...")
            sc = StorageContext.from_defaults(persist_dir=storage_path)
            index = load_index_from_storage(sc)
            st.success("✅ Index loaded successfully!")
            return index
        except Exception as e:
            st.warning(f"⚠️ Storage corrupted, rebuilding index: {str(e)}")
            shutil.rmtree(storage_path)
    
    # Build new index
    pdf_files = [f for f in os.listdir("./manuals") if f.endswith('.pdf')]
    
    if not pdf_files:
        st.error("❌ No PDF files found in './manuals' directory")
        st.info("💡 Upload PDF manuals using the sidebar to get started" if is_admin() else "💡 Contact your administrator to upload PDF manuals")
        return None
    
    try:
        st.info(f"🔄 Building index from {len(pdf_files)} PDF file(s)...")
        st.warning("⏳ This may take several minutes depending on file size...")
        
        parser = LlamaParse(result_type="markdown")
        file_extractor = {".pdf": parser}
        documents = SimpleDirectoryReader(
            "./manuals",
            file_extractor=file_extractor
        ).load_data()
        
        st.info(f"📄 Processed {len(documents)} document chunks")
        
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=storage_path)
        
        st.success("✅ Index built and saved successfully!")
        return index
        
    except Exception as e:
        st.error(f"❌ Index building failed: {str(e)}")
        st.info("💡 Check your API keys and ensure PDF files are valid")
        return None

# Build/load the index
with st.spinner("🔄 Initializing system..."):
    index = get_advisor_index()

if index is None:
    st.stop()

# Create query engine
query_engine = index.as_query_engine(similarity_top_k=8)

# Configure the prompt template
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

# ============================================================================
# 10. MAIN SEARCH INTERFACE
# ============================================================================

# Header
st.markdown("<h1 class='main-header'>📟 Engineer Advisor Search</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Get instant answers from technical manuals</p>", unsafe_allow_html=True)

# Search interface
query = st.text_input(
    "🔍 Describe the fault or ask a technical question:",
    placeholder="e.g., How do I troubleshoot door sensor connectivity issues?",
    help="Ask specific technical questions for best results"
)

# Quick example questions
with st.expander("💡 Example Questions"):
    st.markdown("""
    - How do I troubleshoot door sensor connectivity issues?
    - What are the wiring connections for panel zone 1?
    - Explain the installation procedure for motion detectors
    - What voltage should I expect at terminal X?
    - How do I reset the main control panel?
    """)

# Process query
if query:
    try:
        with st.spinner("🔍 Analyzing technical manuals..."):
            response = query_engine.query(query)
        
        # Display response
        st.markdown("---")
        st.markdown("### 🛠 Technical Solution")
        
        # Main answer
        st.markdown(
            f"""<div class='success-box'>
            {response.response}
            </div>""",
            unsafe_allow_html=True
        )
        
        # Source references
        st.markdown("### 📚 Source References")
        
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for idx, node in enumerate(response.source_nodes, 1):
                file_name = node.metadata.get('file_name', 'Unknown')
                page = node.metadata.get('page_label', 'N/A')
                
                with st.expander(f"📄 Source {idx}: {file_name} (Page {page})"):
                    st.caption(f"**Relevance Score:** {node.score:.3f}" if hasattr(node, 'score') else "")
                    st.text(node.text[:500] + "..." if len(node.text) > 500 else node.text)
        else:
            st.info("No specific source references available")
            
    except Exception as e:
        st.error(f"❌ Query failed: {str(e)}")
        st.info("💡 Try rephrasing your question or check system status in sidebar")

# Footer
st.markdown("---")
st.caption("Engineer Advisor • Powered by OpenAI & LlamaParse • Version 2.5")

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
