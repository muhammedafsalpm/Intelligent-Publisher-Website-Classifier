# test_all.py
"""
Multi-URL classification test covering all site types.
Results are saved to test_results.json.
Usage: python test_all.py
"""
import asyncio
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_all():
    from app.services.classifier import WebsiteClassifier
    classifier = WebsiteClassifier()
    
    test_urls = [
        ("https://www.flipkart.com", "E-commerce"),
        ("https://www.rakuten.com",  "Cashback"),
        ("https://www.example.com",  "Minimal/Test"),
    ]
    
    results = []
    print("=" * 65)
    print("CLASSIFICATION SUITE (Multi-URL)")
    print("=" * 65)
    
    for url, site_type in test_urls:
        print(f"\n[Site Type: {site_type}] {url}")
        start = time.time()
        try:
            r = await classifier.classify(url)
            elapsed = time.time() - start
            
            print(f"  ✓ {elapsed:.1f}s | Score: {r['overall_score']}/100 | Confidence: {r['confidence']}")
            print(f"    Cashback: {r['is_cashback_site']} | Adult: {r['is_adult_content']} | Gambling: {r['is_gambling']}")
            print(f"    Agency: {r['is_agency_or_introductory']} | Scam: {r['is_scam_or_low_quality']}")
            print(f"    RAG: {r['rag_chunks_used']} chunks | Content: {r['scraped_content_length']}ch")
            print(f"    Summary: {r.get('summary','')[:150]}")
            results.append(r)
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ✗ {elapsed:.1f}s | ERROR: {e}")
    
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 65)
    print(f"Done — results saved to test_results.json")

if __name__ == "__main__":
    asyncio.run(test_all())
