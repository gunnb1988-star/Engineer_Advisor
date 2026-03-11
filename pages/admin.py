import streamlit as st
import os
import shutil
import json
import tempfile
from datetime import datetime
from utils import require_admin, get_supabase, list_manuals, upload_manual, download_manual, delete_manual, insert_manuals_into_index

require_admin()

st.markdown("## ⚙️ Admin Panel")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📁 Manuals", "⚙️ System", "📦 Backup", "👤 Users"])

# ============================================================================
# TAB 1 — UPLOAD MANUALS
# ============================================================================

with tab1:
    st.subheader("Upload PDF Manuals")
    st.caption("PDFs are stored in Supabase Storage — not in GitHub.")

    uploaded_files = st.file_uploader("Upload PDF Manuals", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        if st.button(f"⬆️ Upload & Index {len(uploaded_files)} file(s)"):
            # Step 1 — Upload all files to Supabase Storage
            success, failed = [], []
            for uploaded_file in uploaded_files:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    ok, err = upload_manual(uploaded_file.name, uploaded_file.getvalue())
                if ok:
                    success.append(uploaded_file.name)
                else:
                    failed.append((uploaded_file.name, err))

            for name, err in failed:
                st.error(f"❌ {name} failed to upload: {err}")

            # Step 2 — Incrementally index only the new files
            if success:
                with st.spinner(f"Indexing {len(success)} new manual(s) — this may take a moment..."):
                    indexed, err = insert_manuals_into_index(success)

                if indexed:
                    st.success(f"✅ Uploaded and indexed: {', '.join(success)}")
                    st.cache_resource.clear()  # Force Search to reload updated index
                else:
                    st.warning(f"⚠️ Uploaded but indexing failed: {err}")
                    st.info("Visit **Search** to trigger a full rebuild")

    st.markdown("---")
    st.subheader("Current Manuals")
    pdf_files = list_manuals()
    if pdf_files:
        for f in pdf_files:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.caption(f"📄 {f}")
            with col2:
                pdf_bytes = download_manual(f)
                if pdf_bytes:
                    st.download_button("📥", data=pdf_bytes, file_name=f,
                                       mime="application/pdf", key=f"dl_{f}")
            with col3:
                if st.button("🗑️", key=f"del_pdf_{f}"):
                    if delete_manual(f):
                        local_path = f"./manuals/{f}"
                        if os.path.exists(local_path):
                            os.remove(local_path)
                        # Full rebuild needed on delete (can't remove from index incrementally)
                        if os.path.exists("./storage"):
                            shutil.rmtree("./storage")
                        st.cache_resource.clear()
                        st.success(f"Deleted {f} — visit Search to rebuild index")
                        st.rerun()
                    else:
                        st.error("Delete failed")
    else:
        st.info("No manuals uploaded yet")

# ============================================================================
# TAB 2 — SYSTEM CONTROLS
# ============================================================================

with tab2:
    st.subheader("System Controls")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_resource.clear()
            st.success("Cache cleared!")
            st.rerun()
    with col2:
        if st.button("🔄 Rebuild Index", use_container_width=True):
            if os.path.exists("./storage"):
                shutil.rmtree("./storage")
            st.cache_resource.clear()
            st.success("Index rebuild triggered — visit Search to rebuild")
            st.rerun()

    st.markdown("---")
    st.subheader("Storage Status")

    if os.path.exists("./storage"):
        files = os.listdir("./storage")
        has_index = any(f.startswith('index_store') for f in files)
        has_vector = any('vector_store' in f for f in files)
        st.caption(f"📁 Files in storage: {len(files)}")
        st.caption(f"{'✅' if has_index else '❌'} index_store.json")
        st.caption(f"{'✅' if has_vector else '❌'} vector_store.json")
        st.caption(f"{'✅' if os.path.exists('./storage/.index_ready') else '❌'} .index_ready marker")

        if st.button("🎯 Create Marker File"):
            try:
                with open("./storage/.index_ready", 'w') as f:
                    f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.success("✅ Created .index_ready marker")
            except Exception as e:
                st.error(f"❌ Failed: {e}")

        if st.button("🧹 Clean Old Backup Folders"):
            removed = 0
            for item in os.listdir("./storage"):
                item_path = os.path.join("./storage", item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    removed += 1
            st.success(f"Removed {removed} folder(s)") if removed > 0 else st.info("Already clean")
    else:
        st.warning("Storage folder not found")

    if os.path.exists("./manuals"):
        num = len([f for f in os.listdir("./manuals") if f.endswith('.pdf')])
        st.caption(f"📚 Manuals: {num} file(s)")

# ============================================================================
# TAB 3 — BACKUP
# ============================================================================

with tab3:
    st.subheader("Backup & Download")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Create Index Backup", use_container_width=True):
            storage_path = "./storage"
            if os.path.exists(storage_path):
                try:
                    essential_files = [
                        'docstore.json', 'index_store.json', 'vector_store.json',
                        'default__vector_store.json', 'graph_store.json',
                        'image__vector_store.json', '.index_ready'
                    ]
                    guides_file = './storage/quick_guides.json'
                    if os.path.exists(guides_file):
                        try:
                            with open(guides_file, 'r') as f:
                                if json.load(f):
                                    essential_files.append('quick_guides.json')
                        except Exception:
                            pass

                    with tempfile.TemporaryDirectory() as tmpdir:
                        backup_folder = os.path.join(tmpdir, "storage")
                        os.makedirs(backup_folder)
                        for file in essential_files:
                            src = os.path.join(storage_path, file)
                            if os.path.exists(src):
                                dst_name = 'index_ready' if file == '.index_ready' else file
                                shutil.copy2(src, os.path.join(backup_folder, dst_name))

                        backup_name = f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.make_archive(backup_name, 'zip', tmpdir)
                        with open(f"{backup_name}.zip", "rb") as f:
                            st.download_button("⬇️ Download Backup", f, f"{backup_name}.zip", "application/zip")
                        os.remove(f"{backup_name}.zip")
                    st.success("✅ Backup ready")
                    st.caption("Rename 'index_ready' to '.index_ready' when uploading to GitHub")
                except Exception as e:
                    st.error(f"❌ Backup failed: {e}")
            else:
                st.warning("No storage folder")

    with col2:
        if st.button("📝 Download Guides JSON", use_container_width=True):
            guides_file = "./storage/quick_guides.json"
            if os.path.exists(guides_file):
                with open(guides_file, "rb") as f:
                    st.download_button("⬇️ Download", f, "quick_guides.json", "application/json")
                st.caption("Save to storage/ in your repo")
            else:
                st.warning("No guides file found")

# ============================================================================
# TAB 4 — USER MANAGEMENT
# ============================================================================

with tab4:
    st.subheader("User Management")
    st.info("Users are managed in Supabase Auth.")

    st.markdown("""
    **To add a user:**
    1. Supabase dashboard → Authentication → Users → Add user
    2. Enter email + password

    **To make someone an admin:**
    Run in Supabase SQL Editor:
    ```sql
    UPDATE auth.users
    SET raw_user_meta_data = '{"role": "admin", "name": "Full Name"}'
    WHERE email = 'user@example.com';
    ```

    **To add a display name:**
    ```sql
    UPDATE auth.users
    SET raw_user_meta_data = jsonb_set(raw_user_meta_data, '{name}', '"Full Name"')
    WHERE email = 'user@example.com';
    ```
    """)

    st.markdown("---")

    # Change own password
    st.subheader("🔐 Change My Password")
    with st.form("password_change_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        change_submit = st.form_submit_button("✅ Update Password")

        if change_submit:
            supabase = get_supabase()
            if len(new_password) < 6:
                st.error("❌ Password must be 6+ characters")
            elif new_password != confirm_password:
                st.error("❌ Passwords don't match")
            elif supabase is None:
                st.error("❌ Supabase not connected")
            else:
                try:
                    supabase.auth.sign_in_with_password({
                        "email": st.session_state['user_email'],
                        "password": current_password
                    })
                    supabase.auth.update_user({"password": new_password})
                    st.success("✅ Password changed!")
                except Exception as e:
                    error_msg = str(e)
                    if 'Invalid login credentials' in error_msg or '400' in error_msg:
                        st.error("❌ Current password incorrect")
                    else:
                        st.error(f"❌ Error: {error_msg}")
