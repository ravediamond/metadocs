import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from PIL import Image
from datetime import datetime
from langchain_core.tools import tool


class FileStorageTools:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.images_dir = self.base_dir / "images"
        self.markdown_dir = self.base_dir / "markdown"
        self.metadata_dir = self.base_dir / "metadata"
        self.knowledge_dir = self.base_dir / "knowledge"


@tool
def list_files_with_descriptions() -> Dict[str, dict]:
    """
    Lists all imported PDF files and their descriptions by reading from disk.
    Returns:
        Dict[str, dict]: Dictionary mapping PDF filenames to their information
    """
    storage = FileStorageTools()

    if not storage.pdfs_dir.exists():
        return {"message": "No PDFs have been imported yet"}

    pdf_descriptions = {}

    for pdf_path in storage.pdfs_dir.glob("*.pdf"):
        filename = pdf_path.name
        metadata_path = storage.metadata_dir / f"{filename}.json"

        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    description = metadata.get("description", "No description provided")
            except json.JSONDecodeError:
                description = "Error reading metadata"
        else:
            description = "No description available"

        pdf_descriptions[filename] = {
            "description": description,
            "size_kb": round(os.path.getsize(pdf_path) / 1024, 2),
            "upload_date": (
                metadata.get("upload_date", "Unknown")
                if metadata_path.exists()
                else "Unknown"
            ),
        }

    return (
        pdf_descriptions
        if pdf_descriptions
        else {"message": "No PDFs have been imported yet"}
    )


@tool
def get_page_image(filename: str, page_number: int) -> Dict[str, str]:
    """
    Retrieves a specific page image from a PDF file.
    Args:
        filename: Name of the PDF file
        page_number: Page number to retrieve (1-based index)
    Returns:
        Dict containing image information or error message
    """
    storage = FileStorageTools()

    if not storage.pdfs_dir.exists():
        return {"error": "PDF directory not found"}

    pdf_path = storage.pdfs_dir / filename
    if not pdf_path.exists():
        return {"error": f"PDF file {filename} not found"}

    image_dir = storage.images_dir / filename.replace(".pdf", "")
    image_path = image_dir / f"page_{page_number}.png"

    if not image_path.exists():
        return {"error": f"Page {page_number} not found for {filename}"}

    try:
        # Load image and convert to base64
        with Image.open(image_path) as img:
            import base64
            from io import BytesIO

            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return {
                "image": img_str,
                "filename": filename,
                "page_number": page_number,
                "width": img.width,
                "height": img.height,
            }
    except Exception as e:
        return {"error": f"Error loading image: {str(e)}"}


@tool
def load_markdown_content(filename: str) -> Dict[str, str]:
    """
    Loads markdown content for a PDF file.
    Args:
        filename: Name of the PDF file (with or without .pdf extension)
    Returns:
        Dict containing markdown content or error message
    """
    storage = FileStorageTools()

    if not filename.endswith(".pdf"):
        filename += ".pdf"

    md_path = storage.markdown_dir / f"{filename.replace('.pdf', '')}.md"

    if not md_path.exists():
        return {"error": f"Markdown content not found for {filename}"}

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Also get metadata if available
        metadata_path = storage.metadata_dir / f"{filename}.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        return {"content": content, "filename": filename, "metadata": metadata}
    except Exception as e:
        return {"error": f"Error loading markdown content: {str(e)}"}


@tool
def write_knowledge_graph(filename: str, data: dict) -> Dict[str, str]:
    """
    Writes knowledge graph data to a JSON file.
    Args:
        filename: Name of the knowledge graph file (with or without .json extension)
        data: Dictionary containing the knowledge graph data
    Returns:
        Dict containing success message or error
    """
    storage = FileStorageTools()

    if not filename.endswith(".json"):
        filename += ".json"

    try:
        file_path = storage.knowledge_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        return {
            "success": True,
            "message": f"Successfully wrote knowledge graph to {filename}",
            "path": str(file_path),
        }
    except Exception as e:
        return {"success": False, "error": f"Error writing knowledge graph: {str(e)}"}


@tool
def read_knowledge_graph(filename: str) -> Dict[str, any]:
    """
    Reads knowledge graph data from a JSON file.
    Args:
        filename: Name of the knowledge graph file (with or without .json extension)
    Returns:
        Dict containing the knowledge graph data or error message
    """
    storage = FileStorageTools()

    if not filename.endswith(".json"):
        filename += ".json"

    file_path = storage.knowledge_dir / filename

    if not file_path.exists():
        return {"error": f"Knowledge graph file {filename} not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "data": data,
            "filename": filename,
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(file_path)
            ).isoformat(),
        }
    except Exception as e:
        return {"error": f"Error reading knowledge graph: {str(e)}"}


# List of all available tools
tools = [
    list_files_with_descriptions,
    get_page_image,
    load_markdown_content,
    write_knowledge_graph,
    read_knowledge_graph,
]
