from typing import Optional, Dict, Any


def generate_visualization(content: str, state: Dict[str, Any]) -> Optional[Dict]:
    """Generate visualization based on content and state"""

    # Check content for visualization needs
    needs_mermaid = any(
        keyword in content.lower()
        for keyword in ["relationship", "diagram", "structure", "flow"]
    )
    needs_code = any(
        keyword in content.lower() for keyword in ["code", "implementation", "function"]
    )
    needs_markdown = any(
        keyword in content.lower() for keyword in ["table", "list", "documentation"]
    )

    # Generate appropriate visualization
    if needs_mermaid:
        return generate_mermaid_diagram(content, state)
    elif needs_code:
        return generate_code_visualization(content, state)
    elif needs_markdown:
        return generate_markdown_content(content, state)

    return None


def generate_mermaid_diagram(content: str, state: Dict[str, Any]) -> Dict:
    """Generate Mermaid diagram based on content"""
    # Extract ontology data if available
    ontology_version = state.get("versions", {}).get("ontology_version")

    # Create a default diagram structure
    diagram = """
    classDiagram
        class Contract {
            +String category
            +Date startDate
            +Date endDate
        }
        class Customer
        class SalesRepresentative
        class PriceEffect

        Contract -- Customer : belongs to
        Contract -- SalesRepresentative : reviewed by
        Contract -- PriceEffect : implements
    """

    return {
        "type": "mermaid",
        "content": diagram.strip(),  # Remove extra whitespace
        "title": "Contract Entity Relationships",
    }


def generate_code_visualization(content: str, state: Dict[str, Any]) -> Dict:
    """Generate code visualization"""
    # Example code visualization
    code = """
    class Entity:
        def __init__(self):
            self.relationships = []
            
        def add_relationship(self, entity):
            self.relationships.append(entity)
    """

    return {
        "type": "code",
        "content": code,
        "title": "Code Structure",
        "language": "python",
    }


def generate_markdown_content(content: str, state: Dict[str, Any]) -> Dict:
    """Generate markdown content"""
    # Example markdown content
    markdown = """
    # Analysis Results

    | Entity | Type | Count |
    |--------|------|-------|
    | Contract | Core | 150 |
    | Party | Related | 300 |
    """

    return {"type": "markdown", "content": markdown, "title": "Data Analysis"}
