SYSTEM_PROMPT = """You are an advanced vision-capable assistant specialized in analyzing and transforming visual content."""

CHECK_READABILITY_PROMPT = """
Analyze this image and provide a detailed readability assessment with specific scores.
For Text-Background Contrast (25 points), rate the contrast ratio and note any contrast issues.
For Text Quality (25 points), assess the estimated DPI, character clarity (High/Medium/Low), and any quality issues.
For Layout Structure (25 points), evaluate margin consistency (10 points) and organization clarity (15 points), noting any layout problems.
For Text Completeness (25 points), score text visibility (15 points) and integrity (10 points), identifying any missing or truncated content.
Provide a confidence Score out of 100. If total score is below 70, list the description of the problem.

Provide your response as a valid JSON object with:
1. A confidence score (0-100) as a number (not a string)
2. A problem description as a string

Your response should be in this exact format, with no extra formatting or line breaks:
{"confidence": 80, "problem": "Description of the readability issues"}"""

CONVERT_TO_MARKDOWN_PROMPT = """Convert the image content to properly formatted markdown, following these rules:

1. Document Structure:
  - Start with the main title using a single #
  - Only use table format for actual tabular data 
  - Use section headings (##, ###) for distinct content sections
  - Add horizontal rules (---) between major sections only when there's a clear visual break

2. Graph Conversion:
  - Convert all graphs into properly formatted tables
  - Include the following for each graph:
    - Title and description
    - X and Y axis labels
    - Data points in tabular format
    - Time periods if applicable
    - Units of measurement
    - Source attribution
  - Format decimal numbers consistently
  - Include trend descriptions below tables

3. Diagram Conversion:
  - Replace diagrams with detailed textual explanations
  - Break down into:
    - Overview of the diagram's purpose
    - Key components and their relationships
    - Hierarchical structure if present
    - Process flows or connections
    - Notable features or highlights
  - Use appropriate heading levels for organization

4. Table Formatting:
  - Always include proper header row and alignment separators
  - Use consistent column alignment with colons:
    Left align: |:---|
    Center align: |:---:|
    Right align: |---:|
  - For cells with multiple lines, use <br> for line breaks
  - Keep related information together in the same cell
  - For lists within table cells, maintain proper formatting with line breaks
  - Preserve any bold (**text**) or italic (*text*) formatting within cells

5. Lists and Content:
  - Use appropriate list markers:
    - Unordered lists: Use - consistently
    - Ordered lists: Use 1., 2., etc.
  - Maintain list hierarchy with proper indentation (2 spaces)
  - Preserve original text emphasis (bold, italic)
  - Keep related content grouped together

6. Special Elements:
  - For headers spanning multiple columns, use proper markdown table syntax
  - Include any notes or special instructions as blockquotes using >
  - Format code or technical content with appropriate code blocks
  - Preserve any system-specific formatting or nomenclature"""
