import streamlit as st
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage, Settings, PromptTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_parse import LlamaParse
from datetime import datetime
from utils import (require_auth, find_quick_fix, load_quick_guides, get_quick_guides_as_text,
                   sync_manuals_to_local, download_index_from_supabase, upload_index_to_supabase)

require_auth()

# ============================================================================
# API CONFIGURATION
# ============================================================================

try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
except Exception as e:
    st.error(f"❌ API Configuration Error: {str(e)}")
    st.stop()

# ============================================================================
# INDEX MANAGEMENT
# ============================================================================

@st.cache_resource(show_spinner=False)
def get_advisor_index():
    os.makedirs("./manuals", exist_ok=True)
    os.makedirs("./storage", exist_ok=True)
    storage_path = "./storage"

    marker_file = "./storage/.index_ready"
    required_files = ['docstore.json', 'index_store.json']
    vector_files = ['vector_store.json', 'default__vector_store.json', 'image__vector_store.json']

    # Always try to restore index from Supabase Storage (overwrites stale local files)
    from utils import _supabase_direct, INDEX_BUCKET, INDEX_FILES
    _sb = _supabase_direct()
    if _sb is None:
        st.info("[DEBUG] _supabase_direct returned None — secrets missing?")
    else:
        try:
            _raw = _sb.storage.from_(INDEX_BUCKET).list()
            st.info(f"[DEBUG] Raw list() response: {_raw}")
        except Exception as _e:
            st.info(f"[DEBUG] Error listing index bucket: {_e}")
    dl_ok = download_index_from_supabase()
    st.info(f"[DEBUG] Supabase download: {'✅' if dl_ok else '❌ failed'}")

    has_required = all(os.path.exists(f"./storage/{f}") for f in required_files)
    has_vector = any(os.path.exists(f"./storage/{f}") for f in vector_files)
    has_marker = os.path.exists(marker_file)
    local_files = os.listdir("./storage") if os.path.exists("./storage") else []
    st.info(f"[DEBUG] Local storage files: {local_files}")
    st.info(f"[DEBUG] has_required={has_required}, has_vector={has_vector}")

    if has_required and has_vector:
        try:
            sc = StorageContext.from_defaults(persist_dir=storage_path)
            index = load_index_from_storage(sc)
            st.info("[DEBUG] Index loaded successfully from storage")
            if not has_marker:
                try:
                    with open(marker_file, 'w') as f:
                        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                except Exception:
                    pass
            return index
        except Exception as e:
            if has_marker:
                os.remove(marker_file)
            st.warning(f"Index corrupted, rebuilding: {e}")

    # Sync PDFs from Supabase Storage to local dir for indexing
    sync_manuals_to_local()

    pdf_files = [f for f in os.listdir("./manuals") if f.endswith('.pdf')]
    if not pdf_files:
        return None

    try:
        parser = LlamaParse(result_type="markdown", invalidate_cache=False, do_not_cache=False)
        documents = SimpleDirectoryReader("./manuals", file_extractor={".pdf": parser}).load_data()

        guides_text = get_quick_guides_as_text()
        if guides_text:
            from llama_index.core import Document
            documents.append(Document(text=guides_text, metadata={"source": "quick_guides"}))

        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=storage_path)

        with open("./storage/.index_ready", 'w') as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Push freshly built index to Supabase so it survives restarts
        upload_index_to_supabase()

        return index
    except Exception as e:
        st.error(f"❌ Index failed: {str(e)}")
        return None

# Load index
with st.spinner("🔄 Initialising system..."):
    index = get_advisor_index()

if index is None:
    st.error("❌ No PDF files found")
    st.info("💡 Upload PDFs via the Admin panel" if st.session_state.get('user_role') == 'admin' else "💡 Contact admin to upload manuals")
    st.stop()

query_engine = index.as_query_engine(similarity_top_k=8)

prompt_tmpl = PromptTemplate(
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
query_engine.update_prompts({"response_synthesizer:text_qa_template": prompt_tmpl})

# ============================================================================
# SEARCH UI
# ============================================================================

st.markdown("<h1 class='main-header'>📟 Engineer Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Search manuals and quick guides</p>", unsafe_allow_html=True)

query = st.text_input(
    "🔍 Describe the fault or ask a question:",
    placeholder="e.g., Zone 1 sensor not working",
    help="Searches Quick Guides first (fast), then technical manuals (detailed)"
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
        # Quick Fix match
        quick_fix_match = find_quick_fix(query)
        if quick_fix_match:
            st.markdown("### ⚡ Quick Fix")
            matched_kw = ', '.join(quick_fix_match['matched_keywords'][:5])
            st.markdown(
                f"""<div style='padding:1.5rem;border-radius:8px;background-color:#3d3d00;
                border:2px solid #8d8d2d;margin:1rem 0;color:#ffffff;line-height:1.6;'>
                <h4 style='color:#ffeb3b;margin-top:0;'>⚡ {quick_fix_match['fix']['title']}</h4>
                <div style='margin:1rem 0;white-space:pre-wrap;font-family:system-ui;'>{quick_fix_match['fix']['answer']}</div>
                <p style='margin-top:1rem;font-size:0.85em;color:#ffd54f;border-top:1px solid #8d8d2d;padding-top:0.5rem;'>
                🎯 Matched: {matched_kw}</p></div>""",
                unsafe_allow_html=True
            )
            st.markdown("---")

        # Quick Guides keyword search
        guides = load_quick_guides()
        stop_words = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do', 'i', 'my', 'can', 'you'}
        query_words = [w.lower() for w in query.split() if len(w) > 2 and w.lower() not in stop_words]
        matching_guides = []

        if query_words:
            for guide in guides:
                guide_text = (guide['title'] + ' ' + guide['content']).lower()
                matches = sum(1 for w in query_words if w in guide_text)
                required = 1 if len(query_words) <= 2 else 2
                if matches >= required:
                    matching_guides.append({'guide': guide, 'match_count': matches,
                                            'match_words': [w for w in query_words if w in guide_text]})
            matching_guides.sort(key=lambda x: x['match_count'], reverse=True)

        if matching_guides:
            st.markdown("### 📝 Quick Reference Guides")
            st.caption(f"Found {len(matching_guides)} guide(s) matching your keywords")
            for match_info in matching_guides:
                guide = match_info['guide']
                matched_words = ', '.join(match_info['match_words'])
                st.markdown(
                    f"""<div style='padding:1.5rem;border-radius:8px;background-color:#1e3a5a;
                    border:2px solid #2d5a8d;margin:1rem 0;color:#ffffff;line-height:1.6;'>
                    <h4 style='color:#4da6ff;margin-top:0;'>📝 {guide['title']}</h4>
                    <p style='margin:0.5rem 0;white-space:pre-wrap;'>{guide['content']}</p>
                    <p style='margin-top:1rem;font-size:0.85em;color:#b3d9ff;'>
                    Added by {guide['author']} • {guide['created']}<br>
                    <span style='color:#80bfff;'>Matched: {matched_words}</span></p></div>""",
                    unsafe_allow_html=True
                )
            st.markdown("---")

        # AI manual search
        with st.spinner("🔍 Searching technical manuals..."):
            response = query_engine.query(query)

        st.markdown("### 🛠 Technical Solution")
        st.caption("From technical manuals and documentation")
        st.markdown(f"<div class='success-box'>{response.response}</div>", unsafe_allow_html=True)

        st.markdown("### 📚 Source References")
        if hasattr(response, 'source_nodes') and response.source_nodes:
            stop_words2 = {'how', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for', 'with', 'is', 'do',
                           'i', 'my', 'can', 'you', 'test', 'install', 'setup'}
            query_keywords = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stop_words2]

            matching_title_sources, other_sources = [], []
            for node in response.source_nodes:
                if hasattr(node, 'score') and node.score < 0.5:
                    continue
                if node.metadata.get('source') == 'quick_guides':
                    matching_title_sources.append(node)
                else:
                    file_name = node.metadata.get('file_name', '').lower()
                    if any(kw in file_name for kw in query_keywords):
                        matching_title_sources.append(node)
                    else:
                        other_sources.append(node)

            def group_sources(sources):
                grouped = {}
                for node in sources:
                    key = '📝 Quick Reference Guides' if node.metadata.get('source') == 'quick_guides' \
                        else node.metadata.get('file_name', 'Unknown')
                    grouped.setdefault(key, []).append(node)
                return grouped

            matching_grouped = group_sources(matching_title_sources)
            other_grouped = group_sources(other_sources)

            if matching_grouped:
                st.markdown("#### 🎯 Relevant Manuals")
                for file_name, nodes in matching_grouped.items():
                    if '📝' in file_name:
                        st.info(file_name)
                    else:
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
