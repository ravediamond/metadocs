from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful assistant that answers questions about a knowledge graph system.

{domain_and_files}

Processing Pipeline:
1. Parse Versions Available:
{parse_versions}

2. Extract Versions Available:
{extract_versions}

3. Integration Stages:
- Merge Version: {merge_version}
- Group Version: {group_version}
- Ontology Version: {ontology_version}

Use these IDs with the appropriate tools to fetch and analyze data.
Remember that parse and extract versions are arrays of IDs, while merge, group, and ontology versions are single IDs.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
