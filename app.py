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
from supabase import create_client, Client

# ============================================================================
# QUICK FIXES DATABASE
# ============================================================================

QUICK_FIXES = [
    {
        "title": "Remove Line Fault - Scantronic",
        "panel": "scantronic",
        "keywords": ["remove", "line", "fault", "clear", "reset"],
        "answer": """Lost phone line:

Disable options on 101, 106, 107. 
Recommend upgrading panel to support new comms."""
    },
    {
        "title": "Change User Code - Optima",
        "panel": "optima",
        "keywords": ["change", "user", "code"],
        "answer": """Log into engineer mode (usually prog > 9999)
Press 8 > then type new code > may have to press prog to confirm."""
    },
    {
        "title": "Backdoor into Engineer Mode - Enforcer",
        "panel": "enforcer",
        "keywords": ["backdoor", "back", "door", "engineer", "force"],
        "answer": """Power down mains and battery - Put black connector in top right corner - put 2 pin jumper on pins 3 and 4 on lower from left to right - Power back up mains - when time shows press yes and let ring for 1 minute - it will then back into engineer mode, make sure you change codes you need to now and save."""
    },
    {
        "title": "Default Codes Only - Accenta G3",
        "panel": "accenta",
        "keywords": ["default", "codes", "only"],
        "answer": """Down power > wire link between left PA and far right Set > power up codes should now be default. (0123/1234 user, 9999 engineer) 

Now reset codes: prog **** > 8 > type new code."""
    },
    {
        "title": "Engineer Reset - Aritech",
        "panel": "aritech",
        "keywords": ["engineer", "reset", "how", "perform"],
        "answer": """Get into engineer menu (0-**** > press down arrow) then press either 645 or 745 depending on panel. Screen will say reset performed or similar."""
    },
    {
        "title": "How to Change Codes - Scantronic 9100/MX48",
        "panel": ["mx48", "9100", "scantronic"],
        "keywords": ["change", "user", "engineer", "code", "mx48", "9100"],
        "answer": """From engineer menu (must have panel lid open) press 20 to change engineer, 
21 to change user."""
    },
    {
        "title": "Setup Vonex App - Agility 3",
        "panel": "agility",
        "keywords": ["setup", "vonex", "app"],
        "answer": """Press button on Vonex for 1 min, 
Then connect via hot-spot from phone, 
12345678 = hot-spot password
Search in browser for 192.168.254.254
Login using A:admin, P:admin, 
Follow procedure and connect to customer WiFi"""
    },
    {
        "title": "Walk Test - FM4000",
        "panel": "fm4000",
        "keywords": ["walk", "test", "fm4000", "enter"],
        "answer": """USER code - 4 - bell test for 10 seconds
USER code - 9 - walk test
USER code - 6 - exit walk test
USER code - 7 - code change - enter new code - full set"""
    },
    {
        "title": "Add SmartCom App - Texecom Elite",
        "panel": ["texecom", "elite"],
        "keywords": ["add", "smartcom", "app", "connect"],
        "answer": """Compatibility = Elite series V4+

Connect cable to com ports (4 core to com1, 2 core to com2) 
Enter engineer mode, 
7 udl/digi options, 
Com port setup (option 8), 
Com port 1 = smartcom
Com port 2 = comip module
Leave menu and go to udl options (option 5)
Press 4 - press no - enter udl password - press yes

Now go back to main udl/digi options menu, 
Program digi (option 3), 
Change arc 1 to texecom connect, 

Have lid off smartcom and hold the yellow button for roughly 7 seconds, WiFi led will flash, 
Now connect via hot-spot from phone, 
Should take you to the texecom connect setup (if it doesn't - open browser and navigate to 192.168.2.1) 
Setup to customer WiFi. 

Go back into udl/digi options
Navigate to "Enable texecom connect app" (option 4)
System will give you a connect code to type into customer phone on the texecom connect app."""
    },
    {
        "title": "Add Pyronix Cloud - Euro/Enforcer",
        "panel": ["euro", "enforcer", "pyronix"],
        "keywords": ["add", "app", "pyronix", "cloud"],
        "answer": """Compatibility: V10
Install digi WiFi - XA into SIA port, 
Downpowered and reboot panel, 
Now navigate to communications, 
Program WiFi - sets up hot-spot, connect via phone, 
Should take you to setup page, if not navigate to 192.168.0.1,
Pick customer WiFi and enter password, 
Should say connected on screen after a few seconds, 
Now back out and go to enable app, 
Follow this menu adding what you need to add (cloud password = 2016, App password = can be user choice or whatever you put just write down for customer) 

Now setup on customers phone, 
User code will be the master manager code (this has to be able to set the system or it won't work)"""
    }
]

def find_quick_fix(query):
    """Find matching quick fix based on panel name and keywords"""
    query_lower = query.lower()
    
    # Extract keywords (ignore common words)
    stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you', 'from'}
    query_words = [word for word in query_lower.split() if len(word) > 2 and word not in stop_words]
    
    best_match = None
    best_score = 0
    
    for quick_fix in QUICK_FIXES:
        score = 0
        matched_keywords = []
        
        # Check panel match
        panel_match = False
        panels = quick_fix['panel'] if isinstance(quick_fix['panel'], list) else [quick_fix['panel']]
        
        for panel in panels:
            if panel and panel in query_lower:
                panel_match = True
                score += 10  # Panel match is worth 10 points
                break
        
        # If no panel in query, all panels are candidates
        if not any(panel in query_lower for qf in QUICK_FIXES for panel in (qf['panel'] if isinstance(qf['panel'], list) else [qf['panel']]) if panel):
            panel_match = True  # Generic search
        
        # Count keyword matches
        for keyword in quick_fix['keywords']:
            if keyword in query_lower:
                matched_keywords.append(keyword)
                score += 1
        
        # Need at least 3 keyword matches
        if panel_match and len(matched_keywords) >= 3:
            if score > best_score:
                best_score = score
                best_match = {
                    'fix': quick_fix,
                    'matched_keywords': matched_keywords,
                    'panel_matched': panel_match
                }
    
    return best_match

# ============================================================================
# 1. INITIAL SETUP & CONFIGURATION
# ============================================================================
nest_asyncio.apply()

# Initialize Supabase client
try:
    supabase: Client = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )
except Exception as e:
    st.error(f"❌ Supabase connection failed: {e}")
    supabase = None  # Fall back to local storage

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
# 2. QUICK GUIDES MANAGEMENT (Now using Supabase!)
# ============================================================================

def load_quick_guides():
    """Load quick guides from Supabase database"""
    if supabase is None:
        # Fallback to local file if Supabase not available
        return load_quick_guides_local()
    
    try:
        response = supabase.table('quick_guides').select('*').order('created', desc=True).execute()
        
        # DEBUG: Show what we got from Supabase
        if response.data:
            return response.data
        else:
            # No data in Supabase, fall back to local
            return load_quick_guides_local()
            
    except Exception as e:
        # Show error to admins for debugging
        st.sidebar.error(f"⚠️ Supabase error: {str(e)[:100]}")
        return load_quick_guides_local()

def load_quick_guides_local():
    """Fallback: Load quick guides from local JSON file"""
    os.makedirs("./storage", exist_ok=True)
    guides_file = "./storage/quick_guides.json"
    
    if not os.path.exists(guides_file):
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []
    
    try:
        with open(guides_file, 'r') as f:
            return json.load(f)
    except:
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []

def save_quick_guide(title, content, author):
    """Save a new quick guide to Supabase"""
    if supabase is None:
        return save_quick_guide_local(title, content, author)
    
    try:
        new_guide = {
            "title": title,
            "content": content,
            "author": author
        }
        
        response = supabase.table('quick_guides').insert(new_guide).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error saving guide to Supabase: {e}")
        return save_quick_guide_local(title, content, author)

def save_quick_guide_local(title, content, author):
    """Fallback: Save quick guide to local JSON file"""
    os.makedirs("./storage", exist_ok=True)
    guides_file = "./storage/quick_guides.json"
    
    guides = load_quick_guides_local()
    
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
    """Delete a quick guide from Supabase"""
    if supabase is None:
        return delete_quick_guide_local(guide_id)
    
    try:
        supabase.table('quick_guides').delete().eq('id', guide_id).execute()
    except Exception as e:
        st.error(f"Error deleting guide from Supabase: {e}")
        delete_quick_guide_local(guide_id)

def delete_quick_guide_local(guide_id):
    """Fallback: Delete quick guide from local JSON file"""
    guides_file = "./storage/quick_guides.json"
    guides = load_quick_guides_local()
    guides = [g for g in guides if g.get('id') != guide_id]
    
    with open(guides_file, 'w') as f:
        json.dump(guides, f, indent=2)

def get_quick_guides_as_text():
    """Get all quick guides formatted as searchable text"""
    guides = load_quick_guides()
    if not guides:
        return ""
    
    text = "\n\n=== QUICK REFERENCE GUIDES ===\n\n"
    for guide in guides:
        # Handle both Supabase (timestamp) and local (string) format
        created_str = guide.get('created', '')
        if isinstance(created_str, str):
            display_date = created_str
        else:
            # If it's a timestamp, format it
            display_date = created_str.strftime("%Y-%m-%d %H:%M:%S") if created_str else ""
        
        text += f"\n--- {guide['title']} ---\n"
        text += f"Author: {guide['author']} | Created: {display_date}\n"
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
                    result = save_quick_guide(guide_title, guide_content, st.session_state['username'])
                    if result:
                        st.success(f"✅ Guide '{guide_title}' saved to database!")
                        st.info("💡 Available instantly to all users - no refresh needed!")
                        st.session_state['show_add_guide'] = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to save guide")
                else:
                    st.error("❌ Title and content required")
    
    # Show existing guides (dropdown + modal view)
    guides = load_quick_guides()
    if guides:
        st.caption(f"📚 {len(guides)} guide(s) available")
        
        # Create dropdown with guide titles
        guide_titles = ["Select a guide..."] + [guide['title'] for guide in guides]
        selected_title = st.selectbox(
            "View Guide",
            guide_titles,
            key="guide_selector"
        )
        
        # If a guide is selected, store it in session state to show modal
        if selected_title != "Select a guide...":
            selected_guide = next((g for g in guides if g['title'] == selected_title), None)
            if selected_guide:
                st.session_state['selected_guide'] = selected_guide
                st.session_state['show_guide_modal'] = True
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
                            '.index_ready'
                        ]
                        
                        # Only include quick_guides.json if it has content
                        guides_file = './storage/quick_guides.json'
                        if os.path.exists(guides_file):
                            try:
                                with open(guides_file, 'r') as f:
                                    guides_data = json.load(f)
                                    if guides_data and len(guides_data) > 0:
                                        essential_files.append('quick_guides.json')
                            except:
                                pass  # Skip if file is corrupted
                        
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

# Configure prompt - Smart Adaptive Style
new_summary_tmpl_str = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "You are a senior field engineer helping a colleague. Answer naturally and conversationally.\n\n"
    "ADAPT YOUR RESPONSE:\n"
    "- Simple questions (what/where/when): Answer directly in 1-2 sentences\n"
    "- How-to questions: Give clear, practical steps (3-5 steps)\n"
    "- Troubleshooting: Start with the most common cause first, then alternatives\n"
    "- Complex topics: Provide key information without unnecessary detail\n\n"
    "STYLE:\n"
    "- Talk like you're explaining to a colleague in person\n"
    "- Be direct and practical - skip the fluff\n"
    "- Use normal language, not robotic phrases\n"
    "- If wiring is relevant, mention key connections only\n"
    "- Focus on what they need to know, not everything possible\n\n"
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

# ============================================================================
# GUIDE MODAL OVERLAY (Shows when guide selected from sidebar)
# ============================================================================

if st.session_state.get('show_guide_modal') and st.session_state.get('selected_guide'):
    guide = st.session_state['selected_guide']
    
    # Handle both Supabase (timestamp) and local (string) format  
    created_str = guide.get('created', '')
    if isinstance(created_str, str):
        display_date = created_str
    else:
        display_date = created_str.strftime("%Y-%m-%d %H:%M:%S") if created_str else ""
    
    # Modal content with overlay
    st.markdown(f"""
    <div style='
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.7);
        z-index: 999;
    '></div>
    <div style='
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: white;
        padding: 2.5rem;
        padding-bottom: 1rem;
        border-radius: 12px;
        max-width: 700px;
        width: 90%;
        max-height: 70vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        z-index: 1000;
        border: 3px solid #2d5a8d;
    '>
        <div style='
            font-size: 1.8rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 1rem;
        '>
            📝 {guide['title']}
        </div>
        <div style='
            color: #666;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid #e0e0e0;
        '>
            👤 <strong>By:</strong> {guide['author']} &nbsp;&nbsp;•&nbsp;&nbsp; 
            📅 <strong>Created:</strong> {display_date}
        </div>
        <div style='
            color: #333;
            line-height: 1.8;
            white-space: pre-wrap;
            font-family: system-ui;
            font-size: 1.05rem;
            margin-bottom: 2rem;
        '>
{guide['content']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Control buttons - OUTSIDE the modal HTML, in Streamlit
    st.markdown("<br><br><br>", unsafe_allow_html=True)  # Spacer
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✖️ Close", key="close_modal", use_container_width=True, type="primary"):
            st.session_state['show_guide_modal'] = False
            st.session_state['selected_guide'] = None
            st.rerun()
    
    with col2:
        if is_admin():
            if st.button("🗑️ Delete This Guide", key="delete_modal_guide", use_container_width=True):
                delete_quick_guide(guide['id'])
                st.session_state['show_guide_modal'] = False
                st.session_state['selected_guide'] = None
                st.success("✅ Guide deleted!")
                st.rerun()
    
    st.stop()  # Don't show search interface when modal is open

# ============================================================================
# MAIN SEARCH BOX
# ============================================================================


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
        # FIRST: Check for Quick Fix match
        quick_fix_match = find_quick_fix(query)
        
        if quick_fix_match:
            st.markdown("### ⚡ Quick Fix")
            matched_kw = ', '.join(quick_fix_match['matched_keywords'][:5])
            
            st.markdown(
                f"""<div style='padding: 1.5rem; border-radius: 8px; background-color: #3d3d00; 
                border: 2px solid #8d8d2d; margin: 1rem 0; color: #ffffff; line-height: 1.6;'>
                <h4 style='color: #ffeb3b; margin-top: 0;'>⚡ {quick_fix_match['fix']['title']}</h4>
                <div style='margin: 1rem 0; white-space: pre-wrap; font-family: system-ui;'>{quick_fix_match['fix']['answer']}</div>
                <p style='margin-top: 1rem; font-size: 0.85em; color: #ffd54f; border-top: 1px solid #8d8d2d; padding-top: 0.5rem;'>
                🎯 Matched keywords: {matched_kw}</p>
                </div>""",
                unsafe_allow_html=True
            )
            st.markdown("---")
        
        # SECOND: Search Quick Guides directly (multi-keyword matching)
        guides = load_quick_guides()
        
        # DEBUG: Show how many guides loaded
        if is_admin():
            st.caption(f"🔍 DEBUG: Loaded {len(guides)} guides from {'Supabase' if supabase else 'local file'}")
        
        matching_guides = []
        
        # Extract meaningful keywords from query (ignore common words)
        stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you'}
        query_words = [word.lower() for word in query.split() if len(word) > 2 and word.lower() not in stop_words]
        
        # DEBUG: Show what keywords were extracted
        if is_admin() and query_words:
            st.caption(f"🔍 DEBUG: Searching for keywords: {', '.join(query_words)}")
        
        if query_words:  # Only search if we have meaningful keywords
            for guide in guides:
                # Combine title and content for searching
                guide_text = (guide['title'] + ' ' + guide['content']).lower()
                
                # Count how many query keywords match in the guide
                matches = sum(1 for word in query_words if word in guide_text)
                
                # SIMPLIFIED MATCHING: More lenient rules
                if len(query_words) == 1:
                    required_matches = 1  # Single keyword: need 1
                elif len(query_words) == 2:
                    required_matches = 1  # Two keywords: need at least 1
                elif len(query_words) == 3:
                    required_matches = 2  # Three keywords: need 2
                else:
                    required_matches = 2  # 4+ keywords: need 2
                
                # DEBUG: Show matching details for admins
                if is_admin() and matches > 0:
                    st.caption(f"🔍 '{guide['title']}': {matches}/{len(query_words)} matches (need {required_matches})")
                
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
        
        # THIRD: Search PDFs with AI (comprehensive search)
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
            # Extract keywords from query for title matching
            stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you', 'test', 'install', 'setup'}
            query_keywords = [word.lower() for word in query.split() if len(word) > 3 and word.lower() not in stop_words]
            
            # Separate sources by title relevance
            matching_title_sources = []
            other_sources = []
            
            for node in response.source_nodes:
                source_type = node.metadata.get('source', '')
                
                # Skip if relevance too low
                if hasattr(node, 'score') and node.score < 0.5:
                    continue
                
                if source_type == 'quick_guides':
                    matching_title_sources.append(node)
                else:
                    file_name = node.metadata.get('file_name', '').lower()
                    
                    # Check if any query keyword is in the PDF filename
                    title_matches = any(keyword in file_name for keyword in query_keywords)
                    
                    if title_matches:
                        matching_title_sources.append(node)
                    else:
                        other_sources.append(node)
            
            # Group matching sources by file
            def group_sources(sources):
                grouped = {}
                for node in sources:
                    source_type = node.metadata.get('source', '')
                    if source_type == 'quick_guides':
                        file_name = '📝 Quick Reference Guides'
                    else:
                        file_name = node.metadata.get('file_name', 'Unknown')
                    
                    if file_name not in grouped:
                        grouped[file_name] = []
                    grouped[file_name].append(node)
                return grouped
            
            matching_grouped = group_sources(matching_title_sources)
            other_grouped = group_sources(other_sources)
            
            # Display matching title sources first (priority)
            if matching_grouped:
                st.markdown("#### 🎯 Relevant Manuals")
                for file_name, nodes in matching_grouped.items():
                    if '📝' in file_name:
                        st.info(f"{file_name}")
                    else:
                        # Collect pages
                        pages = set()
                        for node in nodes:
                            page = node.metadata.get('page_label', node.metadata.get('page_number'))
                            if page and str(page) not in ['N/A', 'None', '']:
                                pages.add(str(page))
                        
                        page_info = f" (Page{'s' if len(pages) > 1 else ''}: {', '.join(sorted(pages))})" if pages else ""
                        
                        with st.expander(f"📄 {file_name}{page_info}", expanded=True):
                            for idx, node in enumerate(nodes, 1):
                                if hasattr(node, 'score'):
                                    st.caption(f"**Match {idx} - Relevance: {node.score:.1%}**")
                                
                                preview = node.text[:400] + "..." if len(node.text) > 400 else node.text
                                st.text(preview)
                                
                                if idx < len(nodes):
                                    st.markdown("---")
            
            # Show other sources (lower priority)
            if other_grouped:
                with st.expander(f"📋 Other References ({len(other_grouped)} manual(s))", expanded=False):
                    for file_name, nodes in other_grouped.items():
                        pages = set()
                        for node in nodes:
                            page = node.metadata.get('page_label', node.metadata.get('page_number'))
                            if page and str(page) not in ['N/A', 'None', '']:
                                pages.add(str(page))
                        
                        page_info = f" (Pages: {', '.join(sorted(pages))})" if pages else ""
                        st.caption(f"📄 {file_name}{page_info}")
            
            if not matching_grouped and not other_grouped:
                st.info("No source references available")
        else:
            st.info("No source references available")
            
    except Exception as e:
        st.error(f"❌ Query failed: {str(e)}")
        st.info("💡 Try rephrasing or check system status")

st.markdown("---")
st.caption("Engineer Advisor • High-Quality OCR • Quick Guides • Version 3.0")
