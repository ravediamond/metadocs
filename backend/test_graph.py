import networkx as nx
import matplotlib.pyplot as plt
import json

# Load JSON data from file
with open("output_data.json", "r") as file:
    data = json.load(file)

# Define the maximum number of pages to process
max_pages = 10  # Set this to the desired number of pages

# Initialize the directed graph
G = nx.DiGraph()

# Add nodes and edges based on entities and their relationships, limited to max_pages
for i, page in enumerate(data):
    if i >= max_pages:
        break  # Stop processing when reaching max_pages

    for entity in page["entities"]:
        entity_name = entity["entity_name"]
        G.add_node(entity_name)

        # Add an edge if there's a parent entity
        if entity["parent_entity"]:
            parent_entity = entity["parent_entity"]
            G.add_edge(parent_entity, entity_name)

# Draw the graph
plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G)  # Positioning of nodes
nx.draw(
    G,
    pos,
    with_labels=True,
    node_size=2000,
    font_size=10,
    font_weight="bold",
    arrows=True,
)
plt.title(f"Entity Relationship Graph (First {max_pages} Pages)")
plt.show()
