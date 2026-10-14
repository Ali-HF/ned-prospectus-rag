import os
import sys
import importlib
import importlib.metadata
import warnings
from dotenv import dotenv_values

# Filter deprecation warnings during environment check
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

print("--- Checking Installed Packages (requirements.txt) ---")
pkgs_dist = importlib.metadata.packages_distributions()
dist_to_mods = {}
for mod, dists in pkgs_dist.items():
    for d in dists:
        dist_to_mods.setdefault(d.lower(), []).append(mod)

requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
with open(requirements_path, "r", encoding="utf-8") as f:
    packages = [
        line.strip().split("==")[0].split(">=")[0].split("<=")[0]
        for line in f
        if line.strip() and not line.startswith("#")
    ]

all_ok = True
for pkg in packages:
    # Look up top-level modules associated with this distribution
    mods = dist_to_mods.get(pkg.lower().replace("_", "-")) or dist_to_mods.get(pkg.lower(), [])
    # Fallback to sanitized package name if metadata has no mapping
    if not mods:
        mods = [pkg.replace("-", "_")]

    pkg_ok = False
    last_err = None
    for m in mods:
        try:
            importlib.import_module(m)
            pkg_ok = True
            break
        except Exception as e:
            last_err = e

    if pkg_ok:
        print(f"{pkg}: OK")
    else:
        all_ok = False
        print(f"Failed to import {pkg}: {last_err}")

if all_ok:
    print("Packages verification: OK")
else:
    print("Package verification failed.")

print("\n--- Checking Embedding Model ---")
try:
    from sentence_transformers import SentenceTransformer
    model_name = "BAAI/bge-small-en-v1.5"
    try:
        model = SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        model = SentenceTransformer(model_name)
    vector = model.encode("hello world")
    print(f"Embedding model '{model_name}' loaded successfully.")
    print(f"Vector length: {len(vector)}")
except Exception as e:
    print(f"Failed to load embedding model: {e}")

print("\n--- Checking Gemini API ---")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
env_values = dotenv_values(env_path) if os.path.exists(env_path) else {}
api_key = env_values.get("GOOGLE_API_KEY")

if not api_key or api_key.strip() in ("", "your-key-here"):
    print("No key found, skipping the API test")
else:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        flash_models = []
        for m in client.models.list():
            model_id = getattr(m, "name", "") or getattr(m, "id", "")
            # Clean prefixes like 'models/' if present
            clean_id = model_id.split("/")[-1] if "/" in model_id else model_id
            if "flash" in clean_id.lower():
                flash_models.append(clean_id)

        print(f"Available Gemini flash models ({len(flash_models)}): {flash_models}")

        # Target gemini-3.8-flash, or nearest flash model from list
        preferred_model = "gemini-3.8-flash" if "gemini-3.8-flash" in flash_models else None
        fallback_model = next((m for m in flash_models if m != "gemini-3.8-flash" and "preview" not in m and "tts" not in m and "image" not in m), flash_models[0] if flash_models else None)

        from langchain_google_genai import ChatGoogleGenerativeAI

        tested_successfully = False
        candidates = [preferred_model, fallback_model] if preferred_model else [fallback_model]

        for idx, model_to_test in enumerate(candidates):
            if not model_to_test:
                continue
            try:
                llm = ChatGoogleGenerativeAI(model=model_to_test, google_api_key=api_key, request_timeout=15)
                response = llm.invoke("say hi")
                reply_text = response.content if isinstance(response.content, str) else str(response.content)
                if idx > 0 or model_to_test != "gemini-3.8-flash":
                    print(f"Note: gemini-3.8-flash was not available or free quota exceeded. Using nearest flash model: {model_to_test}")
                print(f"Model ID used: {model_to_test}")
                print(f"Reply: {reply_text.strip()}")
                tested_successfully = True
                break
            except Exception as err:
                if "RESOURCE_EXHAUSTED" in str(err) or "429" in str(err) or "not found" in str(err).lower():
                    # Fallback to the next model
                    continue
                else:
                    print(f"Gemini test failed with {model_to_test}: {err}")
                    break

        if not tested_successfully:
            print("No Gemini flash model could be invoked successfully.")
    except Exception as e:
        print(f"Gemini test failed: {e}")
