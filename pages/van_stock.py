import streamlit as st
from utils import require_auth, is_admin

require_auth()

st.markdown("## 🚐 Van Stock")
st.markdown("---")

st.info("🚧 Van Stock dashboard coming soon.")
st.markdown("""
**Planned features:**
- Each engineer sees their own van inventory
- Admins can view all vans at once
- Add / remove stock items
- Low stock alerts
- Transfer stock between vans
""")
