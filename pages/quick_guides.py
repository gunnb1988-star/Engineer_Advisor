import streamlit as st
from utils import require_auth, is_admin, load_quick_guides, save_quick_guide, delete_quick_guide

require_auth()

st.markdown("## 📝 Quick Guides")
st.caption("Field notes and solutions added by engineers")
st.markdown("---")

# ============================================================================
# ADD GUIDE
# ============================================================================

with st.expander("➕ Add New Guide", expanded=False):
    with st.form("add_guide_form"):
        guide_title = st.text_input("Title", placeholder="e.g., Zone 1 Sensor Fix")
        guide_content = st.text_area("Solution / Notes", placeholder="Describe the problem and solution...", height=150)
        submit_guide = st.form_submit_button("✅ Save Guide")

        if submit_guide:
            if guide_title and guide_content:
                result = save_quick_guide(guide_title, guide_content, st.session_state['username'])
                if result:
                    st.success(f"✅ Guide '{guide_title}' saved!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save guide")
            else:
                st.error("❌ Title and content required")

# ============================================================================
# BROWSE GUIDES
# ============================================================================

guides = load_quick_guides()

if not guides:
    st.info("No guides yet — add one above!")
    st.stop()

st.caption(f"📚 {len(guides)} guide(s) available")

# Search/filter
search = st.text_input("🔍 Filter guides", placeholder="Type to filter...")
if search:
    guides = [g for g in guides if search.lower() in g['title'].lower() or search.lower() in g['content'].lower()]
    if not guides:
        st.info("No guides match your search")
        st.stop()

# Display guides
for guide in guides:
    created_str = guide.get('created', '')
    display_date = created_str if isinstance(created_str, str) else (
        created_str.strftime("%Y-%m-%d %H:%M:%S") if created_str else "")

    with st.expander(f"📝 {guide['title']}", expanded=False):
        st.markdown(f"**Author:** {guide['author']}  •  **Added:** {display_date}")
        st.markdown("---")
        st.text(guide['content'])

        if is_admin():
            if st.button("🗑️ Delete", key=f"del_{guide['id']}"):
                delete_quick_guide(guide['id'])
                st.success("Deleted!")
                st.rerun()
