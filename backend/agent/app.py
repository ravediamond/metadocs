import streamlit as st
import streamlit_mermaid as stmd
import tempfile
import os
from assistant import generate_response
from pdf_parser import PDFParser
from langchain_aws.chat_models import ChatBedrock


# Initialize session states and components
def init_session_state():
    # Initialize messages if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI programming assistant. I can help you with programming questions and analyze uploaded PDF documents. How can I help you today?",
                "explanation": "Hello! I'm your AI programming assistant. I can help you with programming questions and analyze uploaded PDF documents. How can I help you today?",
                "viz_content": "",
                "viz_type": "markdown",
            }
        ]

    # Initialize PDFs dict if not exists
    if "pdfs" not in st.session_state:
        st.session_state.pdfs = {}

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

        # File uploader
        uploaded_files = st.file_uploader(
            "Upload PDF files", type="pdf", accept_multiple_files=True
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.pdfs:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())

                        with st.spinner(f"Processing {uploaded_file.name}..."):
                            markdown_content = st.session_state.pdf_parser.parse_pdf(
                                tmp_file.name
                            )

                            st.session_state.pdfs[uploaded_file.name] = {
                                "content": markdown_content,
                                "processed": True,
                            }

                        os.unlink(tmp_file.name)
                    st.success(f"Processed {uploaded_file.name}")

        # Display processed PDFs list
        st.subheader("Processed PDFs")

        # Add PDF selector
        if st.session_state.pdfs:
            selected_pdf = st.radio(
                "Select a PDF to view:",
                list(st.session_state.pdfs.keys()),
                key="pdf_selector",
            )

            # Remove button for selected PDF
            if st.button("Remove Selected PDF", key=f"remove_{selected_pdf}"):
                del st.session_state.pdfs[selected_pdf]
                st.rerun()
        else:
            st.write("No PDFs uploaded yet.")

    with view_col:
        st.subheader("PDF Content Viewer")

        if st.session_state.pdfs:
            if "pdf_selector" in st.session_state:
                selected_pdf = st.session_state.pdf_selector

                # Add view options
                view_options = st.radio(
                    "View options:",
                    ["Rendered Markdown", "Raw Markdown"],
                    horizontal=True,
                )

                # Display content based on selected view option
                if view_options == "Rendered Markdown":
                    st.markdown(st.session_state.pdfs[selected_pdf]["content"])
                else:
                    st.code(
                        st.session_state.pdfs[selected_pdf]["content"],
                        language="markdown",
                    )

                # Add download button for markdown content
                st.download_button(
                    label="Download Markdown",
                    data=st.session_state.pdfs[selected_pdf]["content"],
                    file_name=f"{selected_pdf}.md",
                    mime="text/markdown",
                )
        else:
            st.info("Upload a PDF to view its content here.")


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

                # Add PDF context to the messages
                pdf_context = "\n\n".join(
                    [
                        f"Content from {pdf_name}:\n{pdf_info['content']}"
                        for pdf_name, pdf_info in st.session_state.pdfs.items()
                    ]
                )

                # Generate response with PDF context
                response = generate_response(st.session_state.messages, pdf_context)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "explanation": response["explanation"],
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
                        st.write(message["explanation"])

    with viz_col:
        st.subheader("Visualization")
        if st.session_state.messages and "viz_content" in st.session_state.messages[-1]:
            last_msg = st.session_state.messages[-1]
            if last_msg["viz_content"]:
                if last_msg["viz_type"] == "markdown":
                    st.markdown(last_msg["viz_content"])
                elif last_msg["viz_type"] == "mermaid":
                    stmd.st_mermaid(last_msg["viz_content"])
                elif last_msg["viz_type"] == "code":
                    st.code(last_msg["viz_content"])
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

# Initialize session state
init_session_state()

# Main app layout
page = st.sidebar.radio("Navigation", ["PDF Management", "Chat"])

if page == "PDF Management":
    pdf_management_page()
else:
    chat_page()
