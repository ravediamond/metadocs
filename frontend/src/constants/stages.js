export const stages = [
    { id: 'NOT_STARTED', name: 'Not Started', icon: '📋' },
    { id: 'PARSE', name: 'Parse', icon: '📄' },
    { id: 'EXTRACT', name: 'Extract', icon: '🔍' },
    { id: 'MERGE', name: 'Merge', icon: '🔄' },
    { id: 'GROUP', name: 'Group', icon: '📊' },
    { id: 'VALIDATE', name: 'Validate', icon: '✓' },
  ];
  
  export const prompts = {
    'NOT_STARTED': "Would you like to create a new version or modify an existing one?",
    PARSE: "How would you like to modify the document structure?",
    EXTRACT: "What entities should I extract or modify?",
    MERGE: "Which entities should be merged?",
    GROUP: "How should I adjust the groupings?",
    ONTOLOGY: "Would you like to verify the high-level relationships in the final knowledge graph?"
  };