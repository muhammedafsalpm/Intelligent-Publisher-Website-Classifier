# load_policies_manual.py
"""
Force-loads classification_policies.md into ChromaDB from scratch.
Use this if check_policies.py shows 0 chunks or stale data.
Usage: python load_policies_manual.py
"""
import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def force_load():
    print("=" * 55)
    print("FORCE POLICY LOADER")
    print("=" * 55)
    
    # Step 1: Delete stale ChromaDB
    db_path = "./chroma_db"
    if os.path.exists(db_path):
        print(f"\n[1/3] Removing stale ChromaDB at {db_path}...")
        shutil.rmtree(db_path)
        print("      Done.")
    else:
        print(f"\n[1/3] No existing ChromaDB — creating fresh.")
    
    # Step 2: Verify policy file
    policy_path = "app/policies/classification_policies.md"
    if not os.path.exists(policy_path):
        print(f"\n✗ POLICY FILE NOT FOUND: {policy_path}")
        return
    
    with open(policy_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"\n[2/3] Policy file found ({len(content)} chars)")
    
    # Step 3: Reload via PolicyStore (triggers _initialize_policies)
    from app.services.rag import PolicyStore
    print("\n[3/3] Initializing PolicyStore...")
    store = PolicyStore()
    count = store.collection.count()
    
    print(f"\n✓ SUCCESS: {count} policy chunks loaded into ChromaDB")
    
    # Show summary
    print("\n[Sections Loaded]")
    try:
        results = store.collection.get()
        sections = set(m.get('section', 'unknown') for m in results.get('metadatas', []))
        for s in sorted(sections):
            print(f"  • {s}")
    except Exception as e:
        print(f"  (Cannot list sections: {e})")

if __name__ == "__main__":
    force_load()
