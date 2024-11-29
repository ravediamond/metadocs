export const stages = [
    { id: 'new-version', name: 'New Version', icon: '📋' },
    { id: 'parse', name: 'Parse', icon: '📄' },
    { id: 'extract', name: 'Extract', icon: '🔍' },
    { id: 'merge', name: 'Merge', icon: '🔄' },
    { id: 'group', name: 'Group', icon: '📊' },
    { id: 'verification', name: 'Verification', icon: '✓' }
  ];
  
  export const prompts = {
    'new-version': "Would you like to create a new version or modify an existing one?",
    parse: "How would you like to modify the document structure?",
    extract: "What entities should I extract or modify?",
    merge: "Which entities should be merged?",
    group: "How should I adjust the groupings?",
    verification: "Would you like to verify the high-level relationships in the final knowledge graph?"
  };