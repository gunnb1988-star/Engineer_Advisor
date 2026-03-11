import streamlit as st
import os
import shutil
import json
import tempfile
import threading
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

    # Show background indexing status
    import builtins as _builtins
    job = getattr(_builtins, '_index_job', None)
    if job:
        if not job['done']:
            st.warning(f"⏳ Indexing in progress: {', '.join(job['files'])} — you can navigate away safely")
        elif job['ok']:
            st.success(f"✅ Indexing complete: {', '.join(job['files'])}")
            st.cache_resource.clear()
            _builtins._index_job = None
        else:
            st.error(f"❌ Indexing failed: {job['err']}")
            _builtins._index_job = None

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

            # Step 2 — Kick off indexing in a background thread so navigation won't kill it
            if success:
                def _index_in_background(filenames):
                    ok, err = insert_manuals_into_index(filenames)
                    # Store result in a shared location for status checking
                    import builtins
                    builtins._index_job = {"done": True, "ok": ok, "err": err, "files": filenames}

                builtins_import = __import__('builtins')
                builtins_import._index_job = {"done": False, "files": success}

                thread = threading.Thread(target=_index_in_background, args=(success,), daemon=True)
                thread.start()

                st.success(f"✅ Uploaded: {', '.join(success)}")
                st.info("🔄 Indexing running in background — you can navigate away safely. Check back here to see when it's done.")

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
    st.caption("Index and manuals are stored in Supabase Storage.")

    supabase = get_supabase()

    # Index bucket status
    try:
        index_files = [f['name'] for f in supabase.storage.from_('index').list()]
        has_index = 'index_store.json' in index_files
        has_vector = any('vector_store' in f for f in index_files)
        st.caption(f"{'✅' if has_index else '❌'} index_store.json (Supabase)")
        st.caption(f"{'✅' if has_vector else '❌'} vector_store.json (Supabase)")
        st.caption(f"📁 Index files in Supabase: {len(index_files)}")
    except Exception as e:
        st.warning(f"⚠️ Could not check index bucket: {e}")

    # Manuals bucket status
    try:
        manual_files = [f['name'] for f in supabase.storage.from_('manuals').list()]
        pdf_count = len([f for f in manual_files if f.endswith('.pdf')])
        st.caption(f"📚 Manuals in Supabase: {pdf_count} file(s)")
    except Exception as e:
        st.warning(f"⚠️ Could not check manuals bucket: {e}")

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
