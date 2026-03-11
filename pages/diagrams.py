import streamlit as st
import os
from utils import require_auth, list_manuals, download_manual

require_auth()

st.markdown("## 📐 Diagrams & PDFs")
st.markdown("---")

col1, col2 = st.columns(2)

# ============================================================================
# PDFs
# ============================================================================

with col1:
    st.subheader("📄 Manuals")

    pdf_files = list_manuals()
    if pdf_files:
        selected_pdf = st.selectbox("Select Manual", pdf_files)
        if selected_pdf:
            with st.spinner("Fetching..."):
                pdf_bytes = download_manual(selected_pdf)
            if pdf_bytes:
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=selected_pdf,
                    mime="application/pdf"
                )
                st.caption("💡 Download to view on your device")
            else:
                st.error("Could not fetch PDF")
    else:
        st.info("No PDFs available yet")

# ============================================================================
# DIAGRAMS
# ============================================================================

with col2:
    st.subheader("🖼️ Diagrams")

    if os.path.exists("./diagrams"):
        diagram_files = [f for f in os.listdir("./diagrams")
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if diagram_files:
            diagram_names = {f: f.replace('-', ' ').replace('_', ' ').rsplit('.', 1)[0].title()
                             for f in diagram_files}

            selected_diagram = st.selectbox("Select Diagram", list(diagram_names.values()))

            if selected_diagram:
                filename = [k for k, v in diagram_names.items() if v == selected_diagram][0]
                diagram_path = f"./diagrams/{filename}"
                st.image(diagram_path, caption=selected_diagram, use_container_width=True)

                with open(diagram_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Image",
                        data=f,
                        file_name=filename
                    )
                st.caption("💡 Click image to zoom • Right-click to open in new tab")
        else:
            st.info("No diagrams available yet")
    else:
        st.info("No diagrams folder found")
