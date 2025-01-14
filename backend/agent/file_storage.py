import os
import shutil
from pathlib import Path
from PIL import Image
from typing import Dict, Optional
import streamlit as st
import json
from datetime import datetime


class FileStorage:
    def __init__(self, base_dir: str = "data"):
        """Initialize file storage with directory structure."""
        self.base_dir = Path(base_dir)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.images_dir = self.base_dir / "images"
        self.markdown_dir = self.base_dir / "markdown"
        self.knowledge_dir = self.base_dir / "knowledge"
        self.metadata_dir = self.base_dir / "metadata"

        # Create directories if they don't exist
        for directory in [
            self.pdfs_dir,
            self.images_dir,
            self.markdown_dir,
            self.knowledge_dir,
            self.metadata_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def save_pdf(self, file_obj, filename: str) -> Path:
        """Save uploaded PDF file."""
        pdf_path = self.pdfs_dir / filename
        with open(pdf_path, "wb") as f:
            f.write(file_obj.getvalue())
        return pdf_path

    def save_pdf_metadata(self, filename: str, description: str):
        """Save PDF metadata including description."""
        metadata_path = self.metadata_dir / f"{filename}.json"
        metadata = {
            "filename": filename,
            "description": description,
            "upload_date": str(datetime.now()),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

    def save_page_image(self, image: Image.Image, pdf_name: str, page_num: int) -> Path:
        """Save page image."""
        pdf_images_dir = self.images_dir / pdf_name.replace(".pdf", "")
        pdf_images_dir.mkdir(exist_ok=True)
        image_path = pdf_images_dir / f"page_{page_num}.png"
        image.save(image_path, "PNG")
        return image_path

    def save_markdown(self, content: str, pdf_name: str) -> Path:
        """Save markdown content."""
        md_path = self.markdown_dir / f"{pdf_name.replace('.pdf', '')}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        return md_path

    def get_page_image(self, pdf_name: str, page_num: int) -> Optional[Image.Image]:
        """Load a specific page image."""
        image_path = (
            self.images_dir / pdf_name.replace(".pdf", "") / f"page_{page_num}.png"
        )
        if image_path.exists():
            return Image.open(image_path)
        return None

    def get_markdown_content(self, pdf_name: str) -> Optional[str]:
        """Load markdown content for a PDF."""
        md_path = self.markdown_dir / f"{pdf_name.replace('.pdf', '')}.md"
        if md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def load_stored_files(self) -> dict:
        """Load all stored files into memory with their metadata."""
        stored_files = {}
        for pdf_path in self.pdfs_dir.glob("*.pdf"):
            pdf_name = pdf_path.name
            md_path = self.markdown_dir / f"{pdf_name.replace('.pdf', '')}.md"
            metadata_path = self.metadata_dir / f"{pdf_name}.json"

            if md_path.exists():
                with open(md_path, "r", encoding="utf-8") as f:
                    markdown_content = f.read()

                # Load metadata if exists
                description = ""
                if metadata_path.exists():
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        description = metadata.get("description", "")

                page_images = {}
                images_dir = self.images_dir / pdf_name.replace(".pdf", "")
                if images_dir.exists():
                    for img_path in images_dir.glob("page_*.png"):
                        page_num = int(img_path.stem.split("_")[1])
                        page_images[page_num] = Image.open(img_path)

                stored_files[pdf_name] = {
                    "content": markdown_content,
                    "page_images": page_images,
                    "total_pages": len(page_images),
                    "processed": True,
                    "description": description,
                }

        return stored_files

    def remove_pdf(self, pdf_name: str) -> bool:
        """Remove all files associated with a PDF."""
        try:
            # Remove PDF file
            pdf_path = self.pdfs_dir / pdf_name
            if pdf_path.exists():
                pdf_path.unlink()

            # Remove markdown file
            md_path = self.markdown_dir / f"{pdf_name.replace('.pdf', '')}.md"
            if md_path.exists():
                md_path.unlink()

            # Remove images directory
            images_dir = self.images_dir / pdf_name.replace(".pdf", "")
            if images_dir.exists():
                shutil.rmtree(images_dir)

            return True
        except Exception as e:
            st.error(f"Error removing files: {str(e)}")
            return False
