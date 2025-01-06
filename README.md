# Domain Knowledge Extraction System

## Architecture Overview

This system extracts, processes, and structures business domain knowledge from various documents into a knowledge graph. The system uses a step-by-step processing pipeline with version control and user validation at each stage.

### Core Components

1. **Domain Management**
   - Organizes knowledge by business domains (e.g., gas bottle sales, medical equipment)
   - Each domain maintains its own set of documents and processing history
   - Supports domain-specific terminology and validation rules

2. **Processing Pipeline**
   - Sequential processing steps with version control
   - User validation and iteration capability at each step
   - Chat-based interaction for modifications and improvements

### Processing Steps

1. **Document Parsing**
   - Converts input documents to markdown format
   - Maintains original document structure
   - Output: Structured markdown files

2. **Entity Extraction**
   - Identifies domain-specific entities
   - Extracts relationships between entities
   - Output: JSON/JSONL files containing entities and relationships

3. **Entity Merging**
   - Combines entities from multiple documents
   - Resolves conflicts and duplicates
   - Output: Consolidated entity list with relationships

4. **Entity Grouping**
   - Organizes entities into logical groups
   - Establishes hierarchy and relationships
   - Output: Grouped entity structure

5. **Ontology Generation**
   - Creates domain-specific ontology
   - Defines entity types and relationships
   - Output: Domain ontology file

6. **Knowledge Graph Generation**
   - Builds final knowledge graph
   - Incorporates all processed information
   - Output: Complete domain knowledge graph

### Data Model

```mermaid
erDiagram
    Domain ||--o{ ProcessRun : "has many"
    ProcessRun ||--|{ ProcessStep : "contains"
    File }|--o{ ProcessRun : "used in"
    
    Domain {
        UUID domain_id PK
        string name
    }

    ProcessRun {
        UUID run_id PK
        UUID domain_id FK
        string status
        string error
        timestamp created_at
        int version
    }

    ProcessStep {
        UUID step_id PK
        UUID run_id FK
        string step_type
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
        UUID previous_step_id FK
    }

    File {
        UUID file_id PK
        UUID domain_id FK
        string filepath
        timestamp uploaded_at
    }
```

#### Key Entities

1. **Domain**
   - Represents a specific business domain
   - Contains all related files and processing runs

2. **ProcessRun**
   - Represents one complete processing attempt
   - Maintains version control for the entire process
   - Tracks overall status and errors

3. **ProcessStep**
   - Individual steps in the processing pipeline
   - Maintains input and output file paths
   - Links to previous versions for history tracking

4. **File**
   - Tracks uploaded documents
   - Maintains file paths and metadata

### User Interface

```mermaid
flowchart TD
    %% Main Navigation Nodes
    login[Login Screen]
    dash[Domain Dashboard]
    dwork[Domain Knowledge Workspace]
    kgraph[Knowledge Graph]
    uconfig[User Settings]
    dconfig[Domain Settings]
    sconfig[System Settings]

    %% Dashboard Elements and Links
    subgraph "Domain Dashboard"
        dash --> dlist[Domain List<br>- Gas Bottle Sales<br>- Medical Equipment<br>- Industrial Cleaning<br>etc.]
        dash --> metrics[Domain Knowledge Metrics<br>- Entities Count<br>- Relationships<br>- Coverage Areas]
        dash --> recent[Recent Activities]
        dlist --> dnew[+ New Domain]
    end

    %% Domain Workspace Elements
    subgraph "Domain Knowledge Workspace"
        dwork --> vis1[Visualization Area]
        dwork --> chat1[Chat Interface]
        dwork --> docs[Document Manager<br>- Industry Standards<br>- Process Documents<br>- Market Reports]
        dwork --> steps[Knowledge Extraction Steps]
        steps --> s1[1. Parse Documents]
        steps --> s2[2. Extract Domain Entities<br>- Products<br>- Processes<br>- Stakeholders]
        steps --> s3[3. Merge Knowledge]
        steps --> s4[4. Group Concepts]
        steps --> s5[5. Create Domain Ontology]
        steps --> s6[6. Generate Knowledge Graph]
    end

    %% Knowledge Graph Elements
    subgraph "Knowledge Graph View"
        kgraph --> gvis[Domain Knowledge Visualization]
        kgraph --> filters[Knowledge Filters<br>- Entity Types<br>- Relationship Types<br>- Process Flows]
        kgraph --> export[Export Options]
        kgraph --> layers[View Layers<br>- Core Concepts<br>- Processes<br>- Relationships]
    end

    %% Settings Pages
    subgraph "Settings"
        uconfig --> uprefs[UI Preferences]
        uconfig --> uacc[Account Settings]
        
        dconfig --> dent[Domain Entity Types]
        dconfig --> dterm[Domain Terminology]
        dconfig --> dval[Domain Validation Rules]
        
        sconfig --> sproc[Processing Settings]
        sconfig --> sapi[API Configuration]
        sconfig --> sstore[Storage Settings]
    end

    %% Main Navigation Links
    dash --> dwork
    dwork --> kgraph

    %% Settings Access Links
    dash --> uconfig
    dash --> sconfig
    dwork --> dconfig
    dwork --> uconfig
    kgraph --> dconfig

    %% Return Links
    dwork --> dash
    kgraph --> dwork
    uconfig --> dash
    dconfig --> dwork
    sconfig --> dash

    %% Styling
    classDef mainPage fill:#f9f,stroke:#333,stroke-width:2px
    classDef subPage fill:#bbf,stroke:#333,stroke-width:1px
    classDef configPage fill:#bfb,stroke:#333,stroke-width:1px

    class dash,dwork,kgraph mainPage
    class dlist,docs,gvis,filters subPage
    class uconfig,dconfig,sconfig configPage
```

The system provides a chat-based interface for interaction:

1. **Main Views**
   - Domain Dashboard: Overview of all domains and their status
   - Domain Workspace: Processing interface with visualization and chat
   - Knowledge Graph View: Final graph visualization and export

2. **Interaction Model**
   - Chat-based interface for all operations
   - Natural language processing for user commands
   - Interactive visualizations of processing results

3. **User Validation**
   - Each processing step can be validated via chat
   - Users can request modifications or improvements
   - System generates new versions based on feedback

### File Storage

- Files are stored in local storage or S3
- Only file paths are stored in the database
- Organized by domain and processing step
- Version control through separate files for each process run

### Configuration Levels

1. **User Configuration**
   - UI preferences
   - Default views
   - Notification settings

2. **Domain Configuration**
   - Entity types
   - Validation rules
   - Terminology standards

3. **System Configuration**
   - Processing parameters
   - Storage settings
   - API configurations

### Processing Flow

```mermaid
flowchart TD
    subgraph Domain Creation
        start[Start] --> create_domain[Create Domain]
        create_domain --> create_version[Create Domain Version]
        create_version --> upload[Upload Files]
    end

    subgraph Pipeline Setup
        upload --> init_pipeline[Initialize Processing Pipeline]
        init_pipeline --> create_parse[Create ParseVersion]
    end

    subgraph Processing Steps
        create_parse --> run_parse[Run Parse]
        run_parse --> |Success| update_parse[Update Current Parse Version]
        update_parse --> create_extract[Create ExtractVersion]
        
        create_extract --> run_extract[Run Extract]
        run_extract --> |Success| update_extract[Update Current Extract Version]
        update_extract --> create_merge[Create MergeVersion]
        
        create_merge --> run_merge[Run Merge]
        run_merge --> |Success| update_merge[Update Current Merge Version]
        update_merge --> create_group[Create GroupVersion]
        
        create_group --> run_group[Run Group]
        run_group --> |Success| update_group[Update Current Group Version]
        update_group --> create_onto[Create OntologyVersion]
        
        create_onto --> run_onto[Run Ontology]
        run_onto --> |Success| update_onto[Update Current Ontology Version]
        update_onto --> create_graph[Create GraphVersion]
        
        create_graph --> run_graph[Run Graph]
        run_graph --> |Success| update_graph[Update Current Graph Version]
    end

    subgraph User Iteration
        update_parse --> |User Feedback| new_parse[Create New Parse Version]
        new_parse --> run_parse
        
        update_extract --> |User Feedback| new_extract[Create New Extract Version]
        new_extract --> run_extract
        
        update_merge --> |User Feedback| new_merge[Create New Merge Version]
        new_merge --> run_merge
        
        update_group --> |User Feedback| new_group[Create New Group Version]
        new_group --> run_group
        
        update_onto --> |User Feedback| new_onto[Create New Ontology Version]
        new_onto --> run_onto
        
        update_graph --> |User Feedback| new_graph[Create New Graph Version]
        new_graph --> run_graph
    end

    subgraph Error Handling
        run_parse --> |Error| error_parse[Log Parse Error]
        run_extract --> |Error| error_extract[Log Extract Error]
        run_merge --> |Error| error_merge[Log Merge Error]
        run_group --> |Error| error_group[Log Group Error]
        run_onto --> |Error| error_onto[Log Ontology Error]
        run_graph --> |Error| error_graph[Log Graph Error]
        
        error_parse --> retry_parse[Retry/Update Parse]
        error_extract --> retry_extract[Retry/Update Extract]
        error_merge --> retry_merge[Retry/Update Merge]
        error_group --> retry_group[Retry/Update Group]
        error_onto --> retry_onto[Retry/Update Ontology]
        error_graph --> retry_graph[Retry/Update Graph]
    end

    subgraph New Domain Version
        update_graph --> |Major Changes| new_version[Create New Domain Version]
        new_version --> copy_files[Copy/Add Files]
        copy_files --> init_pipeline
    end

    classDef process fill:#f9f,stroke:#333,stroke-width:2px;
    classDef userAction fill:#bbf,stroke:#333,stroke-width:2px;
    classDef error fill:#fbb,stroke:#333,stroke-width:2px;
    
    class run_parse,run_extract,run_merge,run_group,run_onto,run_graph process;
    class new_parse,new_extract,new_merge,new_group,new_onto,new_graph userAction;
    class error_parse,error_extract,error_merge,error_group,error_onto,error_graph error;
```

1. **Document Upload**
   - Files are uploaded to storage
   - System creates file records
   - Associates files with domain

2. **Processing Initiation**
   - Creates new ProcessRun
   - Initializes version control
   - Begins sequential processing

3. **Step Processing**
   - Each step creates new ProcessStep record
   - Maintains input/output paths
   - Updates status and error information

4. **Version Control**
   - Each modification creates new version
   - Maintains links to previous versions
   - Enables rollback if needed

### Error Handling

- Each step tracks its own errors
- Full error context stored in database
- Processing can be resumed from failed step
- Version history maintained even for failed runs


### Data Model

```mermaid
erDiagram
    %% Core Entities
    Tenant ||--o{ Domain : has
    Domain ||--o{ DomainVersion : "has versions"
    DomainVersion ||--o{ File : contains
    DomainVersion ||--o{ ProcessingPipeline : has
    
    %% Processing Steps
    ProcessingPipeline ||--o{ ParseVersion : has
    ProcessingPipeline ||--o{ ExtractVersion : has
    ProcessingPipeline ||--o{ MergeVersion : has
    ProcessingPipeline ||--o{ GroupVersion : has
    ProcessingPipeline ||--o{ OntologyVersion : has
    ProcessingPipeline ||--o{ GraphVersion : has
    
    %% User Management
    User ||--o{ UserTenant : has
    Tenant ||--o{ UserTenant : has
    User ||--o{ UserRole : has
    Domain ||--o{ UserRole : has
    Role ||--o{ UserRole : has
    Tenant ||--o{ Role : has
    
    %% Configurations
    Domain ||--o{ DomainConfig : has
    User ||--o{ UserConfig : has
    User ||--o{ APIKey : has
    
    %% Invitations
    User ||--o{ Invitation : sends
    Domain ||--o{ Invitation : for

    Tenant {
        UUID tenant_id PK
        string tenant_name
        timestamp created_at
    }

    User {
        UUID user_id PK
        string email
        string hashed_password
        string name
        timestamp created_at
    }

    UserTenant {
        UUID user_id PK
        UUID tenant_id PK
        UUID role_id FK
        timestamp created_at
    }

    Role {
        UUID role_id PK
        UUID tenant_id FK
        string role_name
        string description
    }

    UserRole {
        UUID user_id PK
        UUID domain_id PK
        UUID role_id FK
        timestamp created_at
    }

    APIKey {
        UUID api_key_id PK
        string api_key
        UUID user_id FK
        UUID tenant_id FK
        timestamp created_at
        timestamp revoked
    }

    Domain {
        UUID domain_id PK
        UUID tenant_id FK
        UUID owner_user_id FK
        string domain_name
        string description
        timestamp created_at
    }

    DomainVersion {
        UUID version_id PK
        UUID domain_id FK
        UUID tenant_id FK
        int version
        timestamp created_at
    }

    ProcessingPipeline {
        UUID pipeline_id PK
        UUID domain_version_id FK
        UUID current_parse_id FK
        UUID current_extract_id FK
        UUID current_merge_id FK
        UUID current_group_id FK
        UUID current_ontology_id FK
        UUID current_graph_id FK
        timestamp created_at
        string status
        string error
    }

    File {
        UUID file_id PK
        UUID domain_version_id FK
        string filename
        string filepath
        timestamp uploaded_at
        UUID uploaded_by FK
    }

    DomainConfig {
        UUID config_id PK
        UUID domain_id FK
        UUID tenant_id FK
        string config_key
        string config_value
        timestamp created_at
    }

    UserConfig {
        UUID config_id PK
        UUID user_id FK
        UUID tenant_id FK
        string config_key
        string config_value
        timestamp created_at
    }

    Invitation {
        UUID invitation_id PK
        UUID inviter_user_id FK
        string invitee_email
        UUID tenant_id FK
        UUID domain_id FK
        string status
        timestamp created_at
        timestamp expires_at
        timestamp accepted_at
    }

    %% Step Version Tables
    ParseVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }

    ExtractVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }

    MergeVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }

    GroupVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }

    OntologyVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }

    GraphVersion {
        UUID version_id PK
        UUID pipeline_id FK
        int version_number
        string status
        string input_path
        string output_path
        string error
        timestamp created_at
    }
```

### Extension Points

1. **New Process Steps**
   - System designed for easy addition of new steps
   - Each step is independent and versioned

2. **Custom Validation Rules**
   - Domain-specific validation can be added
   - Rules stored in domain configuration

3. **Export Formats**
   - Knowledge graph can be exported in various formats
   - New export formats can be added as needed

This architecture provides a flexible, maintainable system for domain knowledge extraction with strong version control and user validation capabilities.


## Dev

### Launch locally

```
docker-compose down -v && docker-compose up --build
```

