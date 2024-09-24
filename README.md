# Metadocs

## Features

The MVP (Minimum Viable Product) of your SaaS aims to enhance RAG (Retrieval-Augmented Generation) systems by managing domain-specific concepts and definitions in a specific store, integrating with other system like Langchain, and dynamically detecting undefined concepts. Here are the summarized features:

1. Concept and Definition Management:

    Centralized repository for creating, editing, deleting, and managing domain-specific concepts and definitions.
    Categorization, tagging, and synonym management for better organization and retrieval.

2. LangChain Integration:

    Dedicated API endpoints for seamless integration with LangChain-based RAG pipelines.
    Pre-built LangChain components (e.g., ConceptRetriever) to simplify integration.   
    Real-time sync to reflect changes in concepts for integrated systems.

3. Service Account Management:

    Creation and management of service accounts with role-based access control (e.g., read-only, read-write).
    API key generation and management, including usage monitoring, rate limiting, and audit logs.

4. Semantic Search and Synonym Support:

    Basic semantic search using embeddings to retrieve relevant concepts based on context.
    Support for managing synonyms to improve retrieval accuracy.

5. User Roles and Permissions:

    Role-based access control (RBAC) for managing user permissions (e.g., Admin, Viewer).
    Ability to invite users and manage roles.

6. Feedback and Suggestions:

    Mechanism for users to suggest new definitions or modifications and provide feedback on existing definitions.
    Admin capabilities to review, approve, or reject suggestions.

7. Analytics Dashboard:

    Basic analytics to show usage statistics, most searched concepts, user engagement, and other key metrics.

8. Undefined Concept Detection:

    Query Analysis Module: Capture and analyze user queries to identify undefined terms.
    Data Retrieval Analysis Module: Analyze retrieved data to detect frequently occurring undefined terms.
    Suggestions for Undefined Concepts: Generate a list of undefined concepts with a review interface for admins to add or dismiss them.
    Feedback Loop: Allow users to mark suggestions as "Not Relevant" or "Add Later," improving future suggestions.




## Screens Needed for the MVP

1. Login and Signup Screen: Secure access to the platform with options for OAuth login, password recovery, and account creation.

2. Dashboard Screen: Overview of key metrics, recent activities, and quick actions for managing concepts, undefined concepts, and user roles.

3. Concept Library Screen: A searchable and filterable table displaying all concepts with actions to edit, delete, and add new concepts. A new tab for "Undefined Concepts" to display detected undefined terms.

4. Concept Detail and Edit Screen: Detailed view of a concept with options to edit fields like definition, category, and synonyms.

5. Add New Concept Screen (or Modal): A form/modal for adding new concepts with fields for term, definition, tags, and synonyms.

6. Suggestions and Feedback Screen: Display suggestions for new definitions or edits submitted by users, with options for admins to approve or reject.

7. User Management Screen: Manage users and service accounts, including role assignment and invitation management.

8. Integration Settings Screen: Configure and manage integrations, particularly for LangChain, with API settings and integration status.

9. Service Accounts Management Screen: Create and manage service accounts, view API key usage, and monitor activity.

10. Undefined Concept Review Screen: A dedicated screen for reviewing all detected undefined concepts, seeing context snippets, and defining or dismissing them.

11. API Documentation and Support Screen: Provide detailed information on API usage, endpoints, and integration guides, specifically for LangChain.

12. Analytics Screen (Updated): Include analytics on undefined concepts, such as frequency, user actions, and trends over time.

13. Notification Screen: Manage and view notifications related to concept management activities.

14. Settings Screen: Customize platform settings, manage API keys, security options, and set up notification preferences.

15. Global intégration of any system by just using putting this service around the other service

16. Anonymization of all personal related data when stored and sorted in specific région and capacity to destroy everything whenever you want


## Dev

```
docker-compose down -v
docker-compose up --build
```