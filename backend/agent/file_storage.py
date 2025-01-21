import os
import shutil
from pathlib import Path
from PIL import Image
from typing import Dict, Optional, List
import streamlit as st
import json
from datetime import datetime


class FileStorage:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.create_dirs()

    def create_dirs(self):
        self.pdfs_dir = self.base_dir / "pdfs"
        self.images_dir = self.base_dir / "images"
        self.markdown_dir = self.base_dir / "markdown"
        self.metadata_dir = self.base_dir / "metadata"
        self.entities_dir = self.base_dir / "entities"
        self.knowledge_graph_dir = self.base_dir / "knowledge_graph"

        for directory in [
            self.pdfs_dir,
            self.images_dir,
            self.markdown_dir,
            self.metadata_dir,
            self.entities_dir,
            self.knowledge_graph_dir,
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

    def save_extracted_data(self, pdf_name: str, entities: dict, relationships: list):
        """Save extracted entities and relationships as individual JSON files and create a summary."""
        # Create subdirectories for individual files
        entities_dir = self.entities_dir / f"{pdf_name.replace('.pdf', '')}_entities"
        relationships_dir = (
            self.entities_dir / f"{pdf_name.replace('.pdf', '')}_relationships"
        )
        entities_dir.mkdir(parents=True, exist_ok=True)
        relationships_dir.mkdir(parents=True, exist_ok=True)

        # Save individual entity files
        for entity_name, entity_data in entities.items():
            entity_file = entities_dir / f"{entity_name}.json"
            with open(entity_file, "w", encoding="utf-8") as f:
                json.dump(entity_data, f, indent=4, ensure_ascii=False)

        # Save individual relationship files
        for i, relationship in enumerate(relationships):
            rel_file = relationships_dir / f"relationship_{i}.json"
            with open(rel_file, "w", encoding="utf-8") as f:
                json.dump(relationship, f, indent=4, ensure_ascii=False)

        # Create and save summary file
        summary = {
            "entities": {
                name: data.get("definition", "No definition available")
                for name, data in entities.items()
            },
            "relationships": [
                {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"],
                    "description": rel.get("description", "No description available"),
                }
                for rel in relationships
            ],
        }

        summary_path = (
            self.entities_dir / f"{pdf_name.replace('.pdf', '')}_summary.json"
        )
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

    def save_knowledge_graph(
        self, pdf_name: str, entities: List[Dict], relationships: List[Dict]
    ):
        """Save knowledge graph entities and relationships as individual JSON files and create a summary."""
        # Create subdirectories
        graph_entities_dir = (
            self.knowledge_graph_dir / f"{pdf_name.replace('.pdf', '')}_entities"
        )
        graph_relations_dir = (
            self.knowledge_graph_dir / f"{pdf_name.replace('.pdf', '')}_relations"
        )
        graph_entities_dir.mkdir(parents=True, exist_ok=True)
        graph_relations_dir.mkdir(parents=True, exist_ok=True)

        # Save individual entity files
        for i, entity in enumerate(entities):
            entity_file = (
                graph_entities_dir / f"{entity['name'].lower().replace(' ', '_')}.json"
            )
            with open(entity_file, "w", encoding="utf-8") as f:
                json.dump(entity, f, indent=4, ensure_ascii=False)

        # Save individual relationship files
        for i, relationship in enumerate(relationships):
            rel_file = (
                graph_relations_dir
                / f"{relationship['source']}_{relationship['target']}.json"
            )
            with open(rel_file, "w", encoding="utf-8") as f:
                json.dump(relationship, f, indent=4, ensure_ascii=False)

        for entity in entities:
            print("#" * 20)
            print(entity)

        # Create and save summary file
        summary = {
            "entities": {
                entity.get("name", "no name"): {
                    "definition": entity.get("definition", "No definition available"),
                }
                for entity in entities
            },
            "relationships": [
                {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"],
                    "description": rel.get("description", "No description available"),
                }
                for rel in relationships
            ],
        }

        summary_path = (
            self.knowledge_graph_dir
            / f"{pdf_name.replace('.pdf', '')}_graph_summary.json"
        )
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

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

                # Load extracted data if exists
                entities_path = (
                    self.entities_dir / f"{pdf_name.replace('.pdf', '')}_entities.json"
                )
                relationships_path = (
                    self.entities_dir
                    / f"{pdf_name.replace('.pdf', '')}_relationships.json"
                )
                extracted_data = {}
                if entities_path.exists() and relationships_path.exists():
                    with open(entities_path, "r", encoding="utf-8") as f:
                        entities = json.load(f)
                    with open(relationships_path, "r", encoding="utf-8") as f:
                        relationships = json.load(f)
                    extracted_data = {
                        "entities": entities,
                        "relationships": relationships,
                    }

                stored_files[pdf_name] = {
                    "content": markdown_content,
                    "page_images": page_images,
                    "total_pages": len(page_images),
                    "processed": True,
                    "description": description,
                    "extracted_data": extracted_data,
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
            # Remove entities and relationships files
            entities_path = (
                self.entities_dir / f"{pdf_name.replace('.pdf', '')}_entities.json"
            )
            relationships_path = (
                self.entities_dir / f"{pdf_name.replace('.pdf', '')}_relationships.json"
            )
            if entities_path.exists():
                entities_path.unlink()
            if relationships_path.exists():
                relationships_path.unlink()
            return True
        except Exception as e:
            st.error(f"Error removing files: {str(e)}")
            return False
