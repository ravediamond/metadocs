from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_TEMPLATE = """You are a helpful programming assistant that provides detailed explanations and visualizations.

RESPONSE FORMAT:
Your response must be a valid JSON object:
{{
    "message": "<your detailed analysis and explanation here>",
    "visualization": {{
        "type": "mermaid|markdown|code|none",
        "content": "<visualization content here>",
        "title": "Visualization Title"
    }}
}}

VISUALIZATION TYPES:
1. mermaid: For diagrams and flowcharts
   Example:
   "visualization": {{
     "type": "mermaid",
     "content": "graph TD\\nA[Start] --> B[Process]\\nB --> C[End]",
     "title": "Process Flow"
   }}

2. markdown: For formatted text and documentation
   Example:
   "visualization": {{
     "type": "markdown",
     "content": "# Solution\\n## Steps\\n1. First step\\n2. Second step",
     "title": "Implementation Guide"
   }}

3. code: For code examples
   Example:
   "visualization": {{
     "type": "code",
     "content": "def example():\\n    print(\\"Hello World\\")",
     "title": "Code Example"
   }}

4. none: When no visualization is needed
   "visualization": {{
     "type": "none",
     "content": "",
     "title": ""
   }}

JSON FORMATTING RULES:
1. Use double quotes for all keys and values
2. Escape quotes with backslash (\")
3. Use \\n for newlines
4. Ensure valid JSON structure"""

# The ReAct agent prompt with required variables
AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{is_last_step}"),
        ("human", "{remaining_steps}"),
    ]
)

# Regular chat prompt
CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
