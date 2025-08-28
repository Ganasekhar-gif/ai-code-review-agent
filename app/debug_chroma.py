# debug_chroma.py
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

# Try to access the specific collection
collection_name = "github.com_Ganasekhar-gif_real-time-credit-card-fraud-detection-system.git"
print(f"\nTrying to access collection: {collection_name}")

try:
    col = client.get_collection(name=collection_name)
    print(f"✅ Successfully got collection: {col}")
    
    # Try to get basic info
    print("Collection name:", col.name)
    
    # Try to get count (this is where it hangs)
    print("Attempting to get count...")
    count = col.count()
    print(f"Count: {count}")
    
    # Try to get a sample
    print("Attempting to get sample...")
    sample = col.get(limit=1)
    print(f"Sample: {sample}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

