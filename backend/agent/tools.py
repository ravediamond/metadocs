import json
import os
from typing import Dict, List
from langchain_core.tools import tool


@tool("list_files")
def list_files_with_descriptions() -> Dict[str, str]:
    """
    Lists all Python files in the project with their descriptions.

    Returns:
        Dict[str, str]: Dictionary mapping filenames to their descriptions
    """
    file_descriptions = {
        "app.py": "Main Streamlit application file that handles the UI, PDF management, and chat interface",
        "assistant.py": "Handles the chat response generation and message formatting using LangChain and Claude",
        "pdf_parser.py": "Manages PDF processing, including conversion to images and markdown using PyMuPDF",
        "prompts.py": "Contains system prompts and templates for the chat interface",
        "tools.py": "Utility tools for file operations and data handling",
    }
    return file_descriptions


@tool("load_markdown")
def load_markdown_file(filename: str) -> str:
    """
    Loads and returns the content of a markdown file.

    Args:
        filename: Name of the markdown file to load (with or without .md extension)

    Returns:
        str: Content of the markdown file

    Raises:
        FileNotFoundError: If the markdown file doesn't exist
    """
    if not filename.endswith(".md"):
        filename += ".md"

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Markdown file {filename} not found")


@tool("write_json")
def write_json_file(filename: str, data: dict) -> str:
    """
    Writes data to a JSON file.

    Args:
        filename: Name of the JSON file to write (with or without .json extension)
        data: Dictionary data to write to the file

    Returns:
        str: Success message

    Raises:
        Exception: If there's an error writing the file
    """
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return f"Successfully wrote data to {filename}"
    except Exception as e:
        raise Exception(f"Error writing JSON file: {str(e)}")


@tool("read_json")
def read_json_file(filename: str) -> dict:
    """
    Reads data from a JSON file.

    Args:
        filename: Name of the JSON file to read (with or without .json extension)

    Returns:
        dict: Data from the JSON file

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        ValueError: If the file contains invalid JSON
    """
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file {filename} not found")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in file {filename}")


# List of all available tools
tools = [
    list_files_with_descriptions,
    load_markdown_file,
    write_json_file,
    read_json_file,
]

if __name__ == "__main__":
    # Example usage
    print("Available files and descriptions:")
    print(list_files_with_descriptions())

    # Write JSON example
    sample_data = {"name": "Test Data", "values": [1, 2, 3], "nested": {"key": "value"}}
    print("\nWriting JSON:")
    print(write_json_file("test.json", sample_data))

    # Read JSON example
    print("\nReading JSON:")
    print(read_json_file("test.json"))

    # Load markdown example
    print("\nTrying to load markdown:")
    try:
        md_content = load_markdown_file("example.md")
        print(md_content)
    except FileNotFoundError as e:
        print(f"Error: {e}")
