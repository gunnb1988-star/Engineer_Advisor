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
        padding: 1.5rem;
        border-radius: 8px;
        background-color: #1e3a1e;
        border: 2px solid #2d5a2d;
        margin: 1rem 0;
        color: #ffffff;
        line-height: 1.6;
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
    .guide-box {
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# 2. QUICK GUIDES MANAGEMENT
# ============================================================================

def load_quick_guides():
    """Load quick guides from JSON file in persistent storage"""
    # Store in ./storage/ folder which persists on Streamlit Cloud
    os.makedirs("./storage", exist_ok=True)
    guides_file = "./storage/quick_guides.json"
    
    # Create empty file if it doesn't exist
    if not os.path.exists(guides_file):
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []
    
    try:
        with open(guides_file, 'r') as f:
            return json.load(f)
    except:
        # File corrupted - reset
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []

def save_quick_guide(title, content, author):
    """Save a new quick guide to persistent storage"""
    # Ensure storage directory exists
    os.makedirs("./storage", exist_ok=True)
    guides_file = "./storage/quick_guides.json"
    
    guides = load_quick_guides()
    
    new_guide = {
        "id": len(guides) + 1,
        "title": title,
        "content": content,
        "author": author,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    guides.append(new_guide)
    
    with open(guides_file, 'w') as f:
        json.dump(guides, f, indent=2)
    
    return new_guide

def delete_quick_guide(guide_id):
    """Delete a quick guide by ID"""
    guides_file = "./storage/quick_guides.json"
    guides = load_quick_guides()
    guides = [g for g in guides if g['id'] != guide_id]
    
    with open(guides_file, 'w') as f:
        json.dump(guides, f, indent=2)

def get_quick_guides_as_text():
    """Get all quick guides formatted as searchable text"""
    guides = load_quick_guides()
    if not guides:
        return ""
    
    text = "\n\n=== QUICK REFERENCE GUIDES ===\n\n"
    for guide in guides:
        text += f"\n--- {guide['title']} ---\n"
        text += f"Author: {guide['author']} | Created: {guide['created']}\n"
        text += f"{guide['content']}\n"
        text += "-" * 50 + "\n"
    
    return text

# ============================================================================
# 3. PASSWORD MANAGEMENT FUNCTIONS
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
    os.makedirs("./data", exist_ok=True)
    
    custom_passwords = load_custom_passwords()
    custom_passwords[username] = new_password_hash
    
    with open(password_file, 'w') as f:
        json.dump(custom_passwords, f, indent=2)

def get_user_password_hash(username):
    """Get the password hash for a user (custom password takes precedence)"""
    custom_passwords = load_custom_passwords()
    if username in custom_passwords:
        return custom_passwords[username]
    
    users = st.secrets.get("users", {})
    return users.get(username)

def get_admin_users_list():
    """Get admin users list - hardcoded for reliability"""
    # Hardcoded admin list (most reliable)
    return ["bgunn", "jhutchings", "dgreen"]

def get_user_role(username):
    """Get the role of a user"""
    try:
        admin_users = get_admin_users_list()
        
        if username in admin_users:
            return "admin"
        
        users = st.secrets.get("users", {})
        if username in users or username in load_custom_passwords():
            return "user"
        
        return None
    except Exception as e:
        return None

def is_admin():
    """Check if current user is an admin"""
    return st.session_state.get('user_role') == 'admin'

# ============================================================================
# 4. SESSION STATE INITIALIZATION
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
if 'show_add_guide' not in st.session_state:
    st.session_state['show_add_guide'] = False

# ============================================================================
# 5. LOGO DISPLAY FUNCTION
# ============================================================================

def display_logo():
    """Display company logo if available, otherwise show company name"""
    logo_path = "./assets/company_logo.png"
    
    if os.path.exists(logo_path):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_path)  # Use default width behavior
    else:
        st.markdown("""
            <div class="logo-container">
                <div class="company-name">🔧 Your Company Name</div>
                <div style="color: #7f8c8d; font-size: 1rem;">Engineer Advisor System</div>
            </div>
        """, unsafe_allow_html=True)

# ============================================================================
# 6. LOGIN PAGE
# ============================================================================

if not st.session_state['authenticated']:
    display_logo()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔒 Secure Access</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Login to access technical manuals</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("🔓 Login")
            
            if submit_button:
                try:
                    stored_hash = get_user_password_hash(username)
                    
                    if stored_hash and verify_password(password, stored_hash):
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
                        st.warning(f"⚠️ Multiple failed attempts ({st.session_state['login_attempts']})")
                        
                except Exception as e:
                    st.error(f"❌ Authentication error: {str(e)}")
        
        with st.expander("ℹ️ Need Help?"):
            st.info("""
            **User Roles:**
            - **Admin**: Full system access
            - **User**: Search and add quick guides
            
            **Contact your administrator for credentials.**
            """)
    
    st.stop()

# ============================================================================
# 7. API CONFIGURATION
# ============================================================================

try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]
    
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
except Exception as e:
    st.error(f"❌ API Configuration Error: {str(e)}")
    st.info("Please check your API keys in secrets.")
    st.stop()

# ============================================================================
# 8. DISPLAY LOGO ON MAIN APP
# ============================================================================

display_logo()

# ============================================================================
# 9. SIDEBAR - CONTROLS
# ============================================================================

with st.sidebar:
    # User info with role badge
    role_badge = f"<span class='admin-badge'>ADMIN</span>" if is_admin() else f"<span class='user-badge'>USER</span>"
    st.markdown(f"### 👤 {st.session_state['username']} {role_badge}", unsafe_allow_html=True)
    st.caption(f"Session: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    
    st.title("📟 Advisor Tools")
    
    # ========================================================================
    # QUICK GUIDES (All Users)
    # ========================================================================
    st.subheader("📝 Quick Guides")
    st.caption("Add field notes & solutions")
    
    if st.button("➕ Add Quick Guide"):
        st.session_state['show_add_guide'] = not st.session_state['show_add_guide']
    
    if st.session_state['show_add_guide']:
        with st.form("add_guide_form"):
            guide_title = st.text_input("Title", placeholder="e.g., Zone 1 Sensor Fix")
            guide_content = st.text_area(
                "Solution/Notes",
                placeholder="Describe the problem and solution...",
                height=150
            )
            
            submit_guide = st.form_submit_button("✅ Save Guide")
            
            if submit_guide:
                if guide_title and guide_content:
                    save_quick_guide(guide_title, guide_content, st.session_state['username'])
                    st.success(f"✅ Guide '{guide_title}' saved!")
                    st.info("💡 Guide saved to persistent storage - available immediately in search!")
                    st.session_state['show_add_guide'] = False
                    st.rerun()
                else:
                    st.error("❌ Title and content required")
    
    # Show existing guides (compact view)
    guides = load_quick_guides()
    if guides:
        with st.expander(f"📚 View {len(guides)} Guide(s)"):
            for guide in guides:
                with st.expander(f"📝 {guide['title']}", expanded=False):
                    st.caption(f"By: {guide['author']} • {guide['created']}")
                    st.text(guide['content'])
                    
                    # Admin can delete
                    if is_admin():
                        if st.button(f"🗑️ Delete", key=f"del_{guide['id']}"):
                            delete_quick_guide(guide['id'])
                            st.rerun()
    else:
        st.caption("No guides yet - add one!")
    
    st.markdown("---")
    
    # ========================================================================
    # PDF VIEWER (All Users)
    # ========================================================================
    st.subheader("📄 View PDFs")
    
    if os.path.exists("./manuals"):
        pdf_files = [f for f in os.listdir("./manuals") if f.endswith('.pdf')]
        if pdf_files:
            selected_pdf = st.selectbox("Select Manual", pdf_files, key="pdf_viewer_all")
            if selected_pdf:
                pdf_path = os.path.join("./manuals", selected_pdf)
                
                # File info
                file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
                st.caption(f"📊 Size: {file_size:.2f} MB")
                
                # Download button
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Download PDF",
                        data=f,
                        file_name=selected_pdf,
                        mime="application/pdf",
                        key="pdf_dl_all"
                    )
                st.caption("💡 Download to view diagrams")
        else:
            st.info("No PDFs available yet")
    
    st.markdown("---")
    
    # ========================================================================
    # DIAGRAMS (All Users)
    # ========================================================================
    st.subheader("📐 Diagrams")
    
    if os.path.exists("./diagrams"):
        diagram_files = [f for f in os.listdir("./diagrams") 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if diagram_files:
            # Convert filenames to readable names
            diagram_names = {f: f.replace('-', ' ').replace('_', ' ')
                            .rsplit('.', 1)[0].title() 
                            for f in diagram_files}
            
            selected_diagram = st.selectbox(
                "View Diagram", 
                list(diagram_names.values()),
                key="diagram_selector"
            )
            
            if selected_diagram:
                # Find actual filename
                filename = [k for k, v in diagram_names.items() 
                           if v == selected_diagram][0]
                diagram_path = f"./diagrams/{filename}"
                
                # Display image with zoom capability
                st.image(diagram_path, caption=selected_diagram, use_container_width=True)
                
                # Download button
                with open(diagram_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Image",
                        data=f,
                        file_name=filename,
                        key="diagram_download"
                    )
                
                # Zoom instruction
                st.caption("💡 Click image to zoom • Right-click to open in new tab")
        else:
            st.info("No diagrams available yet")
    else:
        st.caption("📁 Diagrams folder not found")
    
    st.markdown("---")
    
    # ========================================================================
    # PASSWORD CHANGE (All Users)
    # ========================================================================
    st.subheader("🔐 Change Password")
    
    if st.button("🔑 Change My Password"):
        st.session_state['show_password_change'] = not st.session_state['show_password_change']
    
    if st.session_state['show_password_change']:
        with st.form("password_change_form"):
            st.write(f"**User:** {st.session_state['username']}")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_submit = st.form_submit_button("✅ Update Password")
            
            if change_submit:
                current_hash = get_user_password_hash(st.session_state['username'])
                
                if not verify_password(current_password, current_hash):
                    st.error("❌ Current password incorrect")
                elif len(new_password) < 6:
                    st.error("❌ Password must be 6+ characters")
                elif new_password != confirm_password:
                    st.error("❌ Passwords don't match")
                else:
                    new_hash = hash_password(new_password)
                    save_custom_password(st.session_state['username'], new_hash)
                    st.success("✅ Password changed!")
                    st.session_state['show_password_change'] = False
                    st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # ADMIN SECTIONS
    # ========================================================================
    if is_admin():
        st.success("🔑 Administrator Access")
        st.markdown("---")
        
        # --- FILE UPLOAD ---
        st.subheader("📁 Upload Manuals")
        
        uploaded_file = st.file_uploader(
            "Upload PDF Manual",
            type="pdf",
            help="High-quality parsing enabled"
        )
        
        if uploaded_file:
            try:
                os.makedirs("./manuals", exist_ok=True)
                file_path = os.path.join("./manuals", uploaded_file.name)
                
                if os.path.exists(file_path):
                    st.warning(f"⚠️ '{uploaded_file.name}' exists")
                    if st.button("Overwrite"):
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Updated {uploaded_file.name}")
                        st.info("💡 Clear cache to re-index")
                else:
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Saved {uploaded_file.name}")
                    st.info("💡 Clear cache to index")
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")
        
        st.markdown("---")
        
        # --- SYSTEM CONTROLS ---
        st.subheader("⚙️ System Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Cache"):
                st.cache_resource.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Rebuild"):
                if os.path.exists("./storage"):
                    shutil.rmtree("./storage")
                st.cache_resource.clear()
                st.success("Rebuilding!")
                st.rerun()
        
        st.markdown("---")
        
        # --- BACKUP ---
        st.subheader("📦 Backup & Download")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Index Backup"):
                storage_path = "./storage"
                if os.path.exists(storage_path):
                    try:
                        # Only backup essential index files (not nested backup folders)
                        essential_files = [
                            'docstore.json',
                            'index_store.json', 
                            'vector_store.json',
                            'default__vector_store.json',
                            'graph_store.json',
                            'image__vector_store.json',
                            'quick_guides.json',
                            '.index_ready'
                        ]
                        
                        # Create temp folder for clean backup
                        import tempfile
                        with tempfile.TemporaryDirectory() as tmpdir:
                            backup_folder = os.path.join(tmpdir, "storage")
                            os.makedirs(backup_folder)
                            
                            # Copy only essential files
                            for file in essential_files:
                                src = os.path.join(storage_path, file)
                                if os.path.exists(src):
                                    # Rename .index_ready to index_ready (visible file)
                                    if file == '.index_ready':
                                        dst = os.path.join(backup_folder, 'index_ready')
                                    else:
                                        dst = os.path.join(backup_folder, file)
                                    shutil.copy2(src, dst)
                            
                            # Create zip
                            backup_name = f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.make_archive(backup_name, 'zip', tmpdir)
                            
                            with open(f"{backup_name}.zip", "rb") as f:
                                st.download_button(
                                    label="⬇️ Download",
                                    data=f,
                                    file_name=f"{backup_name}.zip",
                                    mime="application/zip",
                                    key="backup_download"
                                )
                            
                            # Clean up zip file
                            os.remove(f"{backup_name}.zip")
                        
                        st.success("✅ Backup ready!")
                        st.caption("Marker file saved as 'index_ready' (rename to '.index_ready' on GitHub)")
                    except Exception as e:
                        st.error(f"❌ Backup failed: {e}")
                else:
                    st.warning("⚠️ No storage folder")
        
        with col2:
            if st.button("📝 Guides File"):
                guides_file = "./storage/quick_guides.json"
                if os.path.exists(guides_file):
                    with open(guides_file, "rb") as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name="quick_guides.json",
                            mime="application/json",
                            key="guides_download"
                        )
                    st.caption("Save to storage/ in your repo")
                else:
                    st.warning("⚠️ No guides file")
        
        # Clean up old backup folders
        if st.button("🧹 Clean Storage"):
            storage_path = "./storage"
            if os.path.exists(storage_path):
                removed = 0
                for item in os.listdir(storage_path):
                    item_path = os.path.join(storage_path, item)
                    # Remove directories (old backup folders)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        removed += 1
                if removed > 0:
                    st.success(f"✅ Removed {removed} old backup folder(s)")
                else:
                    st.info("Storage is already clean")
            else:
                st.warning("⚠️ No storage folder")
        
        # Create marker file manually
        if st.button("🎯 Create Marker File"):
            try:
                with open("./storage/.index_ready", 'w') as f:
                    f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.success("✅ Created .index_ready marker file!")
                st.info("💡 Download this with Index Backup and upload to GitHub")
            except Exception as e:
                st.error(f"❌ Failed: {e}")
    
    # ========================================================================
    # SYSTEM STATUS (All Users)
    # ========================================================================
    st.markdown("---")
    st.subheader("📊 System Status")
    
    # Check storage folder status with diagnostics
    storage_exists = os.path.exists("./storage")
    if storage_exists:
        storage_files = os.listdir("./storage")
        has_index = any(f.startswith('index_store') for f in storage_files)
        has_guides = 'quick_guides.json' in storage_files
        
        if has_index:
            st.caption("✅ Index: Active (loaded from storage)")
        else:
            st.caption("⚠️ Index: Building...")
        
        # Admin debug info
        if is_admin():
            st.caption(f"🔍 Storage files: {len(storage_files)}")
            st.caption(f"📝 Guides file: {'✅ Exists' if has_guides else '❌ Missing'}")
    else:
        st.caption("⚠️ Storage folder not found")
        if is_admin():
            st.caption("Creating storage folder...")
    
    if os.path.exists("./manuals"):
        num_files = len([f for f in os.listdir("./manuals") if f.endswith('.pdf')])
        st.caption(f"📚 Manuals: {num_files} file(s)")
    else:
        st.caption("📚 Manuals: 0 files")
    
    num_guides = len(load_quick_guides())
    st.caption(f"📝 Quick Guides: {num_guides}")
    
    st.markdown("---")
    
    if st.button("🚪 Logout"):
        st.session_state['authenticated'] = False
        st.session_state['username'] = None
        st.session_state['user_role'] = None
        st.session_state['show_password_change'] = False
        st.session_state['show_add_guide'] = False
        st.rerun()

# ============================================================================
# 10. DATA ENGINE - INDEX MANAGEMENT
# ============================================================================

@st.cache_resource(show_spinner=False)
def get_advisor_index():
    """Build or load the vector index"""
    
    os.makedirs("./manuals", exist_ok=True)
    os.makedirs("./storage", exist_ok=True)
    storage_path = "./storage"
    
    # Check for ANY vector store file (LlamaIndex creates different names)
    marker_file = "./storage/.index_ready"
    required_files = ['docstore.json', 'index_store.json']
    vector_files = ['vector_store.json', 'default__vector_store.json', 'image__vector_store.json']
    
    has_required = all(os.path.exists(f"./storage/{f}") for f in required_files)
    has_vector = any(os.path.exists(f"./storage/{f}") for f in vector_files)
    has_marker = os.path.exists(marker_file)
    
    # Load if we have the essential files (marker is helpful but not required)
    if has_required and has_vector:
        try:
            # Index exists and is complete - load it!
            sc = StorageContext.from_defaults(persist_dir=storage_path)
            index = load_index_from_storage(sc)
            
            # Create marker file if it doesn't exist (for next time)
            if not has_marker:
                try:
                    with open(marker_file, 'w') as f:
                        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                except:
                    pass  # Ignore if we can't create it
            
            return index
        except Exception as e:
            # Corrupted - delete marker and rebuild
            if has_marker:
                os.remove(marker_file)
            st.warning(f"Index corrupted, rebuilding: {e}")
    
    # Build new index
    pdf_files = [f for f in os.listdir("./manuals") if f.endswith('.pdf')]
    
    if not pdf_files:
        return None
    
    try:
        # RELIABLE PARSING with available features
        parser = LlamaParse(
            result_type="markdown",
            # Using only standard features that work reliably
            invalidate_cache=False,  # Use cache to save tokens
            do_not_cache=False
        )
        
        file_extractor = {".pdf": parser}
        documents = SimpleDirectoryReader(
            "./manuals",
            file_extractor=file_extractor
        ).load_data()
        
        # Add quick guides to the index as additional documents
        guides_text = get_quick_guides_as_text()
        if guides_text:
            from llama_index.core import Document
            guides_doc = Document(text=guides_text, metadata={"source": "quick_guides"})
            documents.append(guides_doc)
        
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=storage_path)
        
        # Create marker file to indicate index is ready
        with open("./storage/.index_ready", 'w') as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return index
        
    except Exception as e:
        st.error(f"❌ Index failed: {str(e)}")
        return None

# Build/load the index
startup_placeholder = st.empty()
with startup_placeholder:
    with st.spinner("🔄 Initializing system..."):
        # Show what's actually happening
        if os.path.exists("./storage"):
            files_in_storage = os.listdir("./storage")
            st.info(f"📁 Storage folder exists with {len(files_in_storage)} files")
            
            # Check for essential files
            has_docstore = os.path.exists("./storage/docstore.json")
            has_index = os.path.exists("./storage/index_store.json")
            has_vector = os.path.exists("./storage/vector_store.json")
            has_marker = os.path.exists("./storage/.index_ready")
            
            st.info(f"✓ docstore.json: {has_docstore}")
            st.info(f"✓ index_store.json: {has_index}")
            st.info(f"✓ vector_store.json: {has_vector}")
            st.info(f"✓ .index_ready marker: {has_marker}")
            
            if has_docstore and has_index and has_vector:
                st.success("✅ All index files present - should load from storage!")
            else:
                st.warning("⚠️ Missing index files - will rebuild")
        else:
            st.error("❌ Storage folder does not exist - will rebuild from scratch")
        
        index = get_advisor_index()

# Clear the diagnostic messages after loading
startup_placeholder.empty()

if index is None:
    st.error("❌ No PDF files found")
    st.info("💡 Upload PDFs to get started" if is_admin() else "💡 Contact admin")
    st.stop()

# Create query engine
query_engine = index.as_query_engine(similarity_top_k=8)

# Configure prompt
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
# 11. MAIN SEARCH INTERFACE
# ============================================================================

st.markdown("<h1 class='main-header'>📟 Engineer Advisor Search</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Search manuals and quick guides</p>", unsafe_allow_html=True)

query = st.text_input(
    "🔍 Describe the fault or ask a question:",
    placeholder="e.g., Zone 1 sensor not working",
    help="Searches Quick Guides first (fast), then technical manuals (detailed)",
    key="main_search"
)

with st.expander("💡 Example Questions"):
    st.markdown("""
    - How do I troubleshoot door sensor connectivity issues?
    - What are the wiring connections for panel zone 1?
    - Explain the installation procedure for motion detectors
    - What voltage should I expect at terminal X?
    - How do I reset the main control panel?
    """)

if query:
    try:
        # FIRST: Search Quick Guides directly (multi-keyword matching)
        guides = load_quick_guides()
        matching_guides = []
        
        # Extract meaningful keywords from query (ignore common words)
        stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you'}
        query_words = [word.lower() for word in query.split() if len(word) > 2 and word.lower() not in stop_words]
        
        if query_words:  # Only search if we have meaningful keywords
            for guide in guides:
                # Combine title and content for searching
                guide_text = (guide['title'] + ' ' + guide['content']).lower()
                
                # Count how many query keywords match in the guide
                matches = sum(1 for word in query_words if word in guide_text)
                
                # Smart matching: scale required matches with query length
                if len(query_words) == 1:
                    required_matches = 1  # Single keyword: need 1
                elif len(query_words) == 2:
                    required_matches = 2  # Two keywords: need both
                elif len(query_words) <= 4:
                    required_matches = 3  # 3-4 keywords: need 3
                else:
                    required_matches = 3  # 5+ keywords: still need 3 (most specific)
                
                if matches >= required_matches:
                    matching_guides.append({
                        'guide': guide,
                        'match_count': matches,
                        'match_words': [w for w in query_words if w in guide_text]
                    })
            
            # Sort by number of matches (best matches first)
            matching_guides.sort(key=lambda x: x['match_count'], reverse=True)
        
        # Show Quick Guides in BLUE box if found
        if matching_guides:
            st.markdown("### ⚡ Quick Reference Guides")
            st.caption(f"Found {len(matching_guides)} guide(s) matching your keywords")
            
            for match_info in matching_guides:
                guide = match_info['guide']
                matched_words = ', '.join(match_info['match_words'])
                
                st.markdown(
                    f"""<div style='padding: 1.5rem; border-radius: 8px; background-color: #1e3a5a; 
                    border: 2px solid #2d5a8d; margin: 1rem 0; color: #ffffff; line-height: 1.6;'>
                    <h4 style='color: #4da6ff; margin-top: 0;'>📝 {guide['title']}</h4>
                    <p style='margin: 0.5rem 0; white-space: pre-wrap;'>{guide['content']}</p>
                    <p style='margin-top: 1rem; font-size: 0.85em; color: #b3d9ff;'>
                    Added by {guide['author']} • {guide['created']}<br>
                    <span style='color: #80bfff;'>Matched keywords: {matched_words}</span></p>
                    </div>""",
                    unsafe_allow_html=True
                )
            st.markdown("---")
        
        # SECOND: Search PDFs with AI (comprehensive search)
        with st.spinner("🔍 Searching technical manuals..."):
            response = query_engine.query(query)
        
        st.markdown("### 🛠 Detailed Technical Solution")
        st.caption("From technical manuals and documentation")
        
        st.markdown(
            f"""<div class='success-box'>
            {response.response}
            </div>""",
            unsafe_allow_html=True
        )
        
        st.markdown("### 📚 Source References")
        
        if hasattr(response, 'source_nodes') and response.source_nodes:
            # Filter by relevance and group by file
            sources_by_file = {}
            
            for node in response.source_nodes:
                # Only show sources with good relevance (>0.5) or top 3
                if hasattr(node, 'score') and node.score < 0.5 and len(sources_by_file) >= 2:
                    continue
                
                source_type = node.metadata.get('source', '')
                if source_type == 'quick_guides':
                    file_name = '📝 Quick Reference Guides'
                else:
                    file_name = node.metadata.get('file_name', 'Unknown')
                
                if file_name not in sources_by_file:
                    sources_by_file[file_name] = []
                sources_by_file[file_name].append(node)
            
            # Display grouped sources
            for file_name, nodes in sources_by_file.items():
                if '📝' in file_name:
                    # Quick guide - show as info box
                    st.info(f"{file_name}")
                else:
                    # PDF source - show with pages
                    pages = set()
                    for node in nodes:
                        page = node.metadata.get('page_label', node.metadata.get('page_number'))
                        if page and str(page) not in ['N/A', 'None', '']:
                            pages.add(str(page))
                    
                    page_info = f" (Page{'s' if len(pages) > 1 else ''}: {', '.join(sorted(pages))})" if pages else ""
                    
                    with st.expander(f"📄 {file_name}{page_info}"):
                        for idx, node in enumerate(nodes, 1):
                            if hasattr(node, 'score'):
                                st.caption(f"**Match {idx} - Relevance: {node.score:.1%}**")
                            
                            # Show text preview
                            preview = node.text[:400] + "..." if len(node.text) > 400 else node.text
                            st.text(preview)
                            
                            if idx < len(nodes):
                                st.markdown("---")
        else:
            st.info("No source references available")
            
    except Exception as e:
        st.error(f"❌ Query failed: {str(e)}")
        st.info("💡 Try rephrasing or check system status")

st.markdown("---")
st.caption("Engineer Advisor • High-Quality OCR • Quick Guides • Version 3.0")
