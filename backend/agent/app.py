import streamlit as st
import streamlit_mermaid as stmd
import tempfile
import os
from assistant import generate_response
from pdf_parser import PDFParser
from file_storage import FileStorage
from langchain_aws.chat_models import ChatBedrock


# Initialize session states and components
def init_session_state():
    """Initialize session state and load saved files."""
    # Initialize file storage
    if "file_storage" not in st.session_state:
        st.session_state.file_storage = FileStorage()

    # Initialize messages if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI programming assistant. I can help you with programming questions and analyze uploaded PDF documents. How can I help you today?",
                "viz_content": "",
                "viz_type": "markdown",
            }
        ]

    # Initialize PDFs dict and load stored files
    if "pdfs" not in st.session_state:
        st.session_state.pdfs = {}

    # Load stored files if pdfs dict is empty
    if not st.session_state.pdfs:
        stored_files = st.session_state.file_storage.load_stored_files()
        if stored_files:
            st.session_state.pdfs.update(stored_files)

    # Initialize PDF parser if not exists
    if "pdf_parser" not in st.session_state:
        model = ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1",
            credentials_profile_name="ho-s-e0-df-ds-workspaces",
            model_kwargs={"temperature": 0, "max_tokens": 4096},
        )
        st.session_state.pdf_parser = PDFParser(model)


def pdf_management_page():
    st.title("PDF Management")

    # Create two columns: left for management, right for viewing
    manage_col, view_col = st.columns([1, 2])

    with manage_col:
        st.subheader("Upload and Manage PDFs")

        # Display currently loaded PDFs
        if st.session_state.pdfs:
            st.info(f"📚 {len(st.session_state.pdfs)} PDFs currently loaded")

            # Create an expander to show loaded PDFs
            with st.expander("View Loaded PDFs", expanded=True):
                for pdf_name, pdf_info in st.session_state.pdfs.items():
                    st.write(f"📄 {pdf_name}")
                    st.caption(f"Pages: {pdf_info['total_pages']}")
                    if pdf_info.get("description"):
                        st.caption(f"Description: {pdf_info['description']}")

        # File uploader
        st.markdown("---")
        st.markdown("### Upload New PDFs")
        uploaded_files = st.file_uploader(
            "Upload PDF files",
            type="pdf",
            accept_multiple_files=True,
            help="Upload new PDF files to process and analyze",
        )

        # Description input for uploaded files
        if uploaded_files:
            st.markdown("### Add Descriptions")
            descriptions = {}
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.pdfs:
                    descriptions[uploaded_file.name] = st.text_area(
                        f"Description for {uploaded_file.name}",
                        help="Add a brief description of the PDF content",
                        key=f"desc_{uploaded_file.name}",
                    )

            # Process button
            if st.button("Process PDFs", key="process_pdfs"):
                for uploaded_file in uploaded_files:
                    if uploaded_file.name not in st.session_state.pdfs:
                        # Save PDF to disk
                        with st.status(
                            f"Processing {uploaded_file.name}...", expanded=True
                        ) as status:
                            try:
                                status.write("Saving PDF...")
                                pdf_path = st.session_state.file_storage.save_pdf(
                                    uploaded_file, uploaded_file.name
                                )

                                # Save description
                                description = descriptions.get(uploaded_file.name, "")
                                st.session_state.file_storage.save_pdf_metadata(
                                    uploaded_file.name, description
                                )

                                status.write("Extracting content...")
                                markdown_content, page_images = (
                                    st.session_state.pdf_parser.parse_pdf(str(pdf_path))
                                )

                                status.write("Saving extracted content...")
                                st.session_state.file_storage.save_markdown(
                                    markdown_content, uploaded_file.name
                                )
                                for page_num, image in page_images.items():
                                    st.session_state.file_storage.save_page_image(
                                        image, uploaded_file.name, page_num
                                    )

                                # Update session state
                                st.session_state.pdfs[uploaded_file.name] = {
                                    "content": markdown_content,
                                    "page_images": page_images,
                                    "total_pages": len(page_images),
                                    "processed": True,
                                    "description": description,
                                }

                                status.update(
                                    label=f"✅ Processed {uploaded_file.name}",
                                    state="complete",
                                )
                            except Exception as e:
                                status.update(
                                    label=f"❌ Error processing {uploaded_file.name}",
                                    state="error",
                                )
                                st.error(f"Error: {str(e)}")
                                st.session_state.file_storage.remove_pdf(
                                    uploaded_file.name
                                )

        # PDF Management section
        if st.session_state.pdfs:
            st.markdown("---")
            st.markdown("### Manage PDFs")
            selected_pdf = st.selectbox(
                "Select a PDF to manage:",
                options=list(st.session_state.pdfs.keys()),
                key="pdf_selector",
            )

            # Show current description with edit option
            if selected_pdf:
                current_description = st.session_state.pdfs[selected_pdf].get(
                    "description", ""
                )
                new_description = st.text_area(
                    "Edit Description",
                    value=current_description,
                    key=f"edit_desc_{selected_pdf}",
                )

                # Save description changes
                if new_description != current_description:
                    if st.button("Save Description Changes"):
                        st.session_state.file_storage.save_pdf_metadata(
                            selected_pdf, new_description
                        )
                        st.session_state.pdfs[selected_pdf][
                            "description"
                        ] = new_description
                        st.success("Description updated successfully!")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Remove PDF", key=f"remove_{selected_pdf}"):
                    if st.session_state.file_storage.remove_pdf(selected_pdf):
                        del st.session_state.pdfs[selected_pdf]
                        st.rerun()
            with col2:
                if st.button("🔄 Reprocess PDF", key=f"reprocess_{selected_pdf}"):
                    # Implement reprocessing logic here
                    st.info("Reprocessing functionality coming soon...")

    with view_col:
        st.subheader("PDF Content Viewer")
        if st.session_state.pdfs and "pdf_selector" in st.session_state:
            selected_pdf = st.session_state.pdf_selector
            pdf_info = st.session_state.pdfs[selected_pdf]

            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["📄 Content", "🖼️ Pages", "📊 Info"])

            with tab1:
                # Add view options
                view_options = st.radio(
                    "View options:",
                    ["Rendered Markdown", "Raw Markdown"],
                    horizontal=True,
                    key=f"view_options_{selected_pdf}",
                )

                if view_options == "Rendered Markdown":
                    st.markdown(pdf_info["content"])
                else:
                    st.code(pdf_info["content"], language="markdown")

            with tab2:
                if "page_images" in pdf_info:
                    page_num = st.slider("Select page", 1, pdf_info["total_pages"], 1)
                    if page_num in pdf_info["page_images"]:
                        st.image(
                            pdf_info["page_images"][page_num],
                            caption=f"Page {page_num}",
                            use_column_width=True,
                        )

            with tab3:
                st.json(
                    {
                        "filename": selected_pdf,
                        "total_pages": pdf_info["total_pages"],
                        "processed": pdf_info["processed"],
                        "description": pdf_info.get(
                            "description", "No description provided"
                        ),
                        "size": os.path.getsize(
                            st.session_state.file_storage.pdfs_dir / selected_pdf
                        )
                        / 1024,  # KB
                    }
                )

            # Add download button for markdown content
            st.download_button(
                label="📥 Download Markdown",
                data=pdf_info["content"],
                file_name=f"{selected_pdf}.md",
                mime="text/markdown",
            )
        else:
            st.info("Upload or select a PDF to view its content here.")


def chat_page():
    st.title("Chat Interface")
    chat_col, viz_col = st.columns(2)

    with chat_col:
        st.subheader("Chat")
        message_container = st.container()
        input_container = st.container()

        with input_container:
            if prompt := st.chat_input("What's on your mind?"):
                st.session_state.messages.append({"role": "user", "content": prompt})

                # Generate response with PDF context
                response = generate_response(st.session_state.messages)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response["content"],
                        "viz_content": response["viz_content"],
                        "viz_type": response["viz_type"],
                    }
                )

        with message_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])

    with viz_col:
        st.subheader("Visualization")
        if st.session_state.messages and "viz_content" in st.session_state.messages[-1]:
            last_msg = st.session_state.messages[-1]
            if last_msg["viz_content"]:
                if last_msg["viz_type"] == "markdown":
                    st.markdown(last_msg["viz_content"])
                elif last_msg["viz_type"] == "mermaid":
                    stmd.st_mermaid(last_msg["viz_content"])
                else:
                    st.write(last_msg["viz_content"])


# Add custom styling
st.markdown(
    """
<style>
.stMarkdown {
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    background-color: #ffffff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.stMarkdown h1 {
    color: #0066cc;
    border-bottom: 2px solid #0066cc;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}
.stMarkdown h2 {
    color: #0066cc;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
}
.stMarkdown ul, .stMarkdown ol {
    padding-left: 1.5rem;
    margin-bottom: 1rem;
}
.stMarkdown pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.3rem;
    margin: 1rem 0;
}
.stMarkdown table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
}
.stMarkdown th, .stMarkdown td {
    border: 1px solid #ddd;
    padding: 0.5rem;
}
.stMarkdown th {
    background-color: #f8f9fa;
}
.stMarkdown blockquote {
    border-left: 4px solid #0066cc;
    padding-left: 1rem;
    margin: 1rem 0;
    color: #666;
}
</style>
""",
    unsafe_allow_html=True,
)


# Main app
def main():
    # Initialize session state
    init_session_state()

    # Main app layout
    page = st.sidebar.radio("Navigation", ["PDF Management", "Chat"])

    if page == "PDF Management":
        pdf_management_page()
    else:
        chat_page()


if __name__ == "__main__":
    main()
