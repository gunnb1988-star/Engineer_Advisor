import streamlit as st
import os
import json
from datetime import datetime
from supabase import create_client, Client

# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_supabase():
    """Get per-session Supabase client."""
    if 'supabase_client' not in st.session_state:
        try:
            st.session_state['supabase_client'] = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"]
            )
        except Exception as e:
            st.session_state['supabase_client'] = None
    return st.session_state['supabase_client']

# ============================================================================
# AUTH HELPERS
# ============================================================================

def get_user_role_from_supabase(user):
    if user and user.user_metadata:
        return user.user_metadata.get('role', 'user')
    return 'user'

def get_display_name(user):
    if user and user.user_metadata:
        name = user.user_metadata.get('name') or user.user_metadata.get('full_name')
        if name:
            return name
    return user.email if user else ''

def is_admin():
    return st.session_state.get('user_role') == 'admin'

def require_auth():
    if not st.session_state.get('authenticated'):
        st.warning("Please log in to access this page.")
        st.stop()

def require_admin():
    require_auth()
    if not is_admin():
        st.error("❌ Admin access required.")
        st.stop()

# ============================================================================
# LOGO
# ============================================================================

def display_logo():
    logo_path = "./assets/company_logo.png"
    if os.path.exists(logo_path):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_path)
    else:
        st.markdown("""
            <div class="logo-container">
                <div class="company-name">🔧 Your Company Name</div>
                <div style="color: #7f8c8d; font-size: 1rem;">Engineer Advisor System</div>
            </div>
        """, unsafe_allow_html=True)

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
    query_lower = query.lower()
    stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you', 'from'}
    query_words = [word for word in query_lower.split() if len(word) > 2 and word not in stop_words]

    best_match = None
    best_score = 0

    for quick_fix in QUICK_FIXES:
        score = 0
        matched_keywords = []

        panels = quick_fix['panel'] if isinstance(quick_fix['panel'], list) else [quick_fix['panel']]
        panel_match = any(panel and panel in query_lower for panel in panels)

        if not any(panel in query_lower for qf in QUICK_FIXES
                   for panel in (qf['panel'] if isinstance(qf['panel'], list) else [qf['panel']]) if panel):
            panel_match = True

        if panel_match:
            score += 10

        for keyword in quick_fix['keywords']:
            if keyword in query_lower:
                matched_keywords.append(keyword)
                score += 1

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
# QUICK GUIDES
# ============================================================================

def load_quick_guides():
    supabase = get_supabase()
    if supabase is None:
        return load_quick_guides_local()
    try:
        response = supabase.table('quick_guides').select('*').order('created', desc=True).execute()
        if response.data:
            return response.data
        return load_quick_guides_local()
    except Exception as e:
        return load_quick_guides_local()

def load_quick_guides_local():
    os.makedirs("./storage", exist_ok=True)
    guides_file = "./storage/quick_guides.json"
    if not os.path.exists(guides_file):
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []
    try:
        with open(guides_file, 'r') as f:
            return json.load(f)
    except Exception:
        with open(guides_file, 'w') as f:
            json.dump([], f)
        return []

def save_quick_guide(title, content, author):
    supabase = get_supabase()
    if supabase is None:
        return save_quick_guide_local(title, content, author)
    try:
        response = supabase.table('quick_guides').insert({
            "title": title, "content": content, "author": author
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error saving guide: {e}")
        return save_quick_guide_local(title, content, author)

def save_quick_guide_local(title, content, author):
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
    supabase = get_supabase()
    if supabase is None:
        return delete_quick_guide_local(guide_id)
    try:
        supabase.table('quick_guides').delete().eq('id', guide_id).execute()
    except Exception as e:
        st.error(f"Error deleting guide: {e}")
        delete_quick_guide_local(guide_id)

def delete_quick_guide_local(guide_id):
    guides_file = "./storage/quick_guides.json"
    guides = load_quick_guides_local()
    guides = [g for g in guides if g.get('id') != guide_id]
    with open(guides_file, 'w') as f:
        json.dump(guides, f, indent=2)

# ============================================================================
# SUPABASE STORAGE — MANUALS
# ============================================================================

MANUALS_BUCKET = "manuals"

def list_manuals():
    """List PDF files in Supabase Storage."""
    supabase = get_supabase()
    if supabase is None:
        return _list_manuals_local()
    try:
        response = supabase.storage.from_(MANUALS_BUCKET).list()
        return [f['name'] for f in response if f.get('name', '').endswith('.pdf')]
    except Exception:
        return _list_manuals_local()

def _list_manuals_local():
    if os.path.exists("./manuals"):
        return [f for f in os.listdir("./manuals") if f.endswith('.pdf')]
    return []

def upload_manual(filename, data):
    """Upload a PDF to Supabase Storage, overwriting if it exists."""
    supabase = get_supabase()
    if supabase is None:
        return False, "Supabase not connected"
    try:
        supabase.storage.from_(MANUALS_BUCKET).upload(
            path=filename,
            file=data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        return True, None
    except Exception as e:
        return False, str(e)

def download_manual(filename):
    """Download a PDF from Supabase Storage. Returns bytes or None."""
    supabase = get_supabase()
    if supabase is None:
        return None
    try:
        return supabase.storage.from_(MANUALS_BUCKET).download(filename)
    except Exception:
        return None

def delete_manual(filename):
    """Delete a PDF from Supabase Storage."""
    supabase = get_supabase()
    if supabase is None:
        return False
    try:
        supabase.storage.from_(MANUALS_BUCKET).remove([filename])
        return True
    except Exception:
        return False

def sync_manuals_to_local():
    """Download all PDFs from Supabase Storage to ./manuals/ for indexing.
    Skips files already present locally."""
    os.makedirs("./manuals", exist_ok=True)
    files = list_manuals()
    for filename in files:
        local_path = f"./manuals/{filename}"
        if not os.path.exists(local_path):
            data = download_manual(filename)
            if data:
                with open(local_path, 'wb') as f:
                    f.write(data)
    return files


# ============================================================================
# SUPABASE STORAGE — INDEX
# ============================================================================

INDEX_BUCKET = "index"
INDEX_FILES = [
    'docstore.json',
    'index_store.json',
    'vector_store.json',
    'default__vector_store.json',
    'graph_store.json',
    'image__vector_store.json',
]

def _supabase_direct():
    """Create a Supabase client directly from secrets (safe inside cached functions)."""
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

def download_index_from_supabase():
    """Download index files from Supabase Storage to ./storage/.
    Returns True if a valid index was found and downloaded."""
    supabase = _supabase_direct()
    if supabase is None:
        return False
    try:
        files_in_bucket = [f['name'] for f in supabase.storage.from_(INDEX_BUCKET).list()]
        if 'index_store.json' not in files_in_bucket:
            return False  # No index stored yet

        os.makedirs("./storage", exist_ok=True)
        for filename in INDEX_FILES:
            if filename in files_in_bucket:
                data = supabase.storage.from_(INDEX_BUCKET).download(filename)
                with open(f"./storage/{filename}", 'wb') as f:
                    f.write(data)
        return True
    except Exception:
        return False

def upload_index_to_supabase():
    """Upload index files from ./storage/ to Supabase Storage."""
    supabase = _supabase_direct()
    if supabase is None:
        return False
    try:
        for filename in INDEX_FILES:
            local_path = f"./storage/{filename}"
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    data = f.read()
                supabase.storage.from_(INDEX_BUCKET).upload(
                    path=filename,
                    file=data,
                    file_options={"upsert": "true"}
                )
        return True
    except Exception:
        return False


# ============================================================================
# INCREMENTAL INDEXING
# ============================================================================

def insert_manuals_into_index(filenames):
    """Insert one or more PDFs into the existing index without full rebuild.
    Returns (success: bool, error: str or None)."""
    import os
    from llama_index.core import (
        StorageContext, load_index_from_storage,
        VectorStoreIndex, SimpleDirectoryReader, Settings
    )
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI
    from llama_parse import LlamaParse

    try:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
        os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]
        Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    except Exception as e:
        return False, f"API config error: {e}"

    os.makedirs("./manuals", exist_ok=True)
    storage_path = "./storage"

    # Pull latest index from Supabase before inserting
    download_index_from_supabase()

    # Download any files not already local
    for filename in filenames:
        local_path = f"./manuals/{filename}"
        if not os.path.exists(local_path):
            data = download_manual(filename)
            if data:
                with open(local_path, 'wb') as f:
                    f.write(data)
            else:
                return False, f"Could not download {filename} from Supabase"

    try:
        # Load existing index or create empty one
        required = ['docstore.json', 'index_store.json']
        has_index = all(os.path.exists(f"{storage_path}/{f}") for f in required)

        if has_index:
            sc = StorageContext.from_defaults(persist_dir=storage_path)
            index = load_index_from_storage(sc)
        else:
            index = VectorStoreIndex([])

        # Parse only the new PDFs
        parser = LlamaParse(result_type="markdown", invalidate_cache=False, do_not_cache=False)
        local_paths = [f"./manuals/{f}" for f in filenames]
        documents = SimpleDirectoryReader(
            input_files=local_paths,
            file_extractor={".pdf": parser}
        ).load_data()

        # Insert new documents into existing index
        for doc in documents:
            index.insert(doc)

        # Persist updated index locally then push to Supabase
        os.makedirs(storage_path, exist_ok=True)
        index.storage_context.persist(persist_dir=storage_path)
        upload_index_to_supabase()

        return True, None

    except Exception as e:
        return False, str(e)


def get_quick_guides_as_text():
    guides = load_quick_guides()
    if not guides:
        return ""
    text = "\n\n=== QUICK REFERENCE GUIDES ===\n\n"
    for guide in guides:
        created_str = guide.get('created', '')
        display_date = created_str if isinstance(created_str, str) else (
            created_str.strftime("%Y-%m-%d %H:%M:%S") if created_str else "")
        text += f"\n--- {guide['title']} ---\n"
        text += f"Author: {guide['author']} | Created: {display_date}\n"
        text += f"{guide['content']}\n"
        text += "-" * 50 + "\n"
    return text
