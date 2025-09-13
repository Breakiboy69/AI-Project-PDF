import os


# Basisverzeichnis (bei Bedarf anpassen)
BASE_DIR = r"C:\\Users\\gamin\\AI-Project-PDF"
INPUT_DIR = os.path.join(BASE_DIR, "input")
TXT_DIR = os.path.join(BASE_DIR, "txtspace")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


# LM Studio API
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama_-_meta-llama-3-8b-instruct" # aus /v1/models


# Betriebsmodus: "clean_for_tts" | "tts_passthrough" | "summary" | "clean_fast"
MODE = "clean_for_tts"



# Extractor: v2 nutzen, falls Datei vorhanden/importierbar
USE_EXTRACTOR_V2 = True


# LLM-Parameter
MAX_TOKENS_CLEAN = 2000
MAX_TOKENS_SUMMARY = 1500
CHUNK_SIZE = 4000
SINGLECALL_LIMIT = 5000

