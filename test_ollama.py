# test_ollama.py
import asyncio
import httpx
import json

async def test_ollama():
    """Diagnostic tool to verify Ollama status and model responsiveness"""
    
    print("=" * 40)
    print("OLLAMA DIAGNOSTICS")
    print("=" * 40)
    
    base_url = "http://localhost:11434"
    
    # 1. Connectivity Check
    print(f"\n1. Checking connectivity to {base_url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                print("   ✓ Ollama is running")
                models_data = response.json()
                models = [m['name'] for m in models_data.get('models', [])]
                print(f"   ✓ Available models: {models if models else 'None (Pull a model first!)'}")
            else:
                print(f"   ✗ Ollama returned HTTP {response.status_code}")
                return
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("   TIP: Run 'ollama serve' in a terminal")
        return

    # 2. Model responsiveness
    test_model = "phi"  # Change to llama3.2 if needed
    if test_model not in [m.split(':')[0] for m in models]:
        print(f"\n2. Skipping model test: '{test_model}' not found in 'ollama list'")
        return

    print(f"\n2. Testing model responsiveness ('{test_model}')...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": test_model,
                "prompt": "Return a JSON object with one field 'status' set to 'ok'.",
                "stream": False,
                "options": {"temperature": 0}
            }
            
            response = await client.post(f"{base_url}/api/generate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                print(f"   ✓ Model responded: {content.strip()}")
                
                # Check JSON extraction
                try:
                    if "{" in content:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        parsed = json.loads(content[start:end])
                        print(f"   ✓ JSON Extraction: SUCCESS ({parsed})")
                    else:
                        print("   ⚠ Response does not contain JSON brackets")
                except:
                    print("   ✗ JSON Extraction: FAILED")
            else:
                print(f"   ✗ Model test failed with HTTP {response.status_code}")
                
    except Exception as e:
        print(f"   ✗ Model test error: {e}")

    print("\n" + "=" * 40)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(test_ollama())
