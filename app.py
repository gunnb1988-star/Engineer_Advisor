import streamlit as st
import nest_asyncio
from utils import (
    get_supabase, get_user_role_from_supabase, get_display_name,
    is_admin, display_logo
)

nest_asyncio.apply()

st.set_page_config(
    page_title="Engineer Advisor",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #4da6ff; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #aaa; margin-bottom: 2rem; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: 600; }
    .success-box {
        padding: 1.5rem; border-radius: 8px;
        background-color: #1e3a1e; border: 2px solid #2d5a2d;
        margin: 1rem 0; color: #ffffff; line-height: 1.6;
    }
    .admin-badge {
        background-color: #ff6b6b; color: white;
        padding: 0.2rem 0.5rem; border-radius: 3px;
        font-size: 0.8rem; font-weight: bold;
    }
    .user-badge {
        background-color: #4dabf7; color: white;
        padding: 0.2rem 0.5rem; border-radius: 3px;
        font-size: 0.8rem; font-weight: bold;
    }
    .logo-container {
        text-align: center; padding: 1rem 0 2rem 0;
        border-bottom: 2px solid #333; margin-bottom: 2rem;
    }
    .company-name { font-size: 2rem; font-weight: 700; color: #4da6ff; margin-top: 0.5rem; }
    .guide-box {
        background-color: #1e1e2e; border-left: 4px solid #4da6ff;
        padding: 1rem; margin: 0.5rem 0; border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'login_attempts' not in st.session_state:
    st.session_state['login_attempts'] = 0
if 'show_password_change' not in st.session_state:
    st.session_state['show_password_change'] = False

# Restore Supabase session from stored tokens
supabase = get_supabase()
if (not st.session_state['authenticated']
        and st.session_state.get('refresh_token')
        and supabase is not None):
    try:
        # Always use the refresh token to get a fresh access token
        # This works even if the access token has expired
        supabase.auth.set_session(
            st.session_state.get('access_token', ''),
            st.session_state['refresh_token']
        )
        refreshed = supabase.auth.refresh_session()
        if refreshed and refreshed.user:
            user = refreshed.user
            session = refreshed.session
            st.session_state['authenticated'] = True
            st.session_state['username'] = get_display_name(user)
            st.session_state['user_email'] = user.email
            st.session_state['user_role'] = get_user_role_from_supabase(user)
            # Store the new fresh tokens
            st.session_state['access_token'] = session.access_token
            st.session_state['refresh_token'] = session.refresh_token
    except Exception:
        # Refresh token expired — user must log in again
        st.session_state.pop('access_token', None)
        st.session_state.pop('refresh_token', None)

# ============================================================================
# LOGIN
# ============================================================================

if not st.session_state['authenticated']:
    display_logo()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔒 Secure Access</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #aaa;'>Login to access technical manuals</p>", unsafe_allow_html=True)
        st.markdown("---")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("🔓 Login")

            if submit_button:
                if supabase is None:
                    st.error("❌ Supabase not connected")
                else:
                    try:
                        auth_response = supabase.auth.sign_in_with_password(
                            {"email": email, "password": password}
                        )
                        user = auth_response.user
                        session = auth_response.session
                        role = get_user_role_from_supabase(user)
                        display_name = get_display_name(user)

                        st.session_state['authenticated'] = True
                        st.session_state['username'] = display_name
                        st.session_state['user_email'] = user.email
                        st.session_state['user_role'] = role
                        st.session_state['login_attempts'] = 0
                        st.session_state['access_token'] = session.access_token
                        st.session_state['refresh_token'] = session.refresh_token

                        st.rerun()
                    except Exception as e:
                        st.session_state['login_attempts'] += 1
                        error_msg = str(e)
                        if 'Invalid login credentials' in error_msg or '400' in error_msg:
                            st.error("❌ Invalid email or password")
                        else:
                            st.error(f"❌ Authentication error: {error_msg}")
                        if st.session_state['login_attempts'] >= 3:
                            st.warning(f"⚠️ Multiple failed attempts ({st.session_state['login_attempts']})")

        with st.expander("ℹ️ Need Help?"):
            st.info("Contact your administrator for login credentials.")

    st.stop()

# ============================================================================
# SIDEBAR — lean
# ============================================================================

with st.sidebar:
    role_badge = "<span class='admin-badge'>ADMIN</span>" if is_admin() else "<span class='user-badge'>ENGINEER</span>"
    st.markdown(f"""
        <div style='padding: 0.5rem 0 0.75rem 0;'>
            <div style='font-size: 0.85rem; color: #aaa; margin-bottom: 0.25rem;'>Logged in as</div>
            <div style='font-size: 1.1rem; font-weight: 600; margin-bottom: 0.4rem;'>👤 {st.session_state['username']}</div>
            <div>{role_badge}</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("🔐 Change Password"):
        with st.form("pw_change"):
            current_pw = st.text_input("Current", type="password")
            new_pw = st.text_input("New", type="password")
            confirm_pw = st.text_input("Confirm", type="password")
            if st.form_submit_button("Update"):
                if len(new_pw) < 6:
                    st.error("6+ characters required")
                elif new_pw != confirm_pw:
                    st.error("Passwords don't match")
                elif supabase is None:
                    st.error("Supabase not connected")
                else:
                    try:
                        supabase.auth.sign_in_with_password({
                            "email": st.session_state['user_email'], "password": current_pw
                        })
                        supabase.auth.update_user({"password": new_pw})
                        st.success("✅ Password updated!")
                    except Exception as e:
                        msg = str(e)
                        st.error("❌ Current password incorrect" if '400' in msg or 'Invalid' in msg else f"❌ {msg}")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        if supabase is not None:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        for key in ['authenticated', 'username', 'user_email', 'user_role',
                    'show_password_change', 'access_token', 'refresh_token']:
            st.session_state.pop(key, None)
        st.session_state['authenticated'] = False
        st.rerun()

# ============================================================================
# NAVIGATION
# ============================================================================

pages = [
    st.Page("pages/search.py",       title="Search",       icon="🔍", default=True),
    st.Page("pages/quick_guides.py", title="Quick Guides", icon="📝"),
    st.Page("pages/diagrams.py",     title="Diagrams & PDFs", icon="📐"),
    st.Page("pages/van_stock.py",    title="Van Stock",    icon="🚐"),
]

if is_admin():
    pages.append(st.Page("pages/admin.py", title="Admin", icon="⚙️"))

pg = st.navigation(pages, position="sidebar")
pg.run()
