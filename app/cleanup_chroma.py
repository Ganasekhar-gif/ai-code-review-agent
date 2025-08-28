# cleanup_chroma.py
import os
import chromadb

# Use the same path as indexer.py
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
print(f"Using CHROMA_DIR: {CHROMA_DIR}")

# Initialize client
client = chromadb.PersistentClient(path=CHROMA_DIR)

# List collections
print("Available collections:")
collections = client.list_collections()
for col in collections:
    print(f"  - {col.name}")

# Delete the corrupted collection
collection_name = "github.com_Ganasekhar-gif_real-time-credit-card-fraud-detection-system.git"
print(f"\nDeleting corrupted collection: {collection_name}")

try:
    client.delete_collection(name=collection_name)
    print(f"✅ Successfully deleted collection: {collection_name}")
except Exception as e:
    print(f"❌ Error deleting collection: {e}")

# List collections again
print("\nRemaining collections:")
collections = client.list_collections()
for col in collections:
    print(f"  - {col.name}")

