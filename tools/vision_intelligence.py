import os
import json
import base64
import requests
from google.cloud import vision
from google.oauth2 import service_account
from core.tool_registry import register_tool
import database as db

def _get_vision_client():
    """
    Initializes the Google Cloud Vision client.
    Uses 'google_vision_key_path' from settings for explicit authentication.
    """
    settings = db.load_settings()
    key_path = settings.get("google_vision_key_path", "").strip().strip('"').strip("'")
    
    try:
        if key_path and os.path.exists(key_path):
             credentials = service_account.Credentials.from_service_account_file(key_path)
             return vision.ImageAnnotatorClient(credentials=credentials)
        else:
             return vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"[Vision Error] Could not initialize cloud client: {e}")
        return None

def _get_ollama_vision(image_path, query, model="moondream"):
    """
    Analyzes an image using local Ollama model.
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        prompt = query if query else "Describe this image in detail."
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "images": [encoded_image]
        }
        
        print(f"[Ollama Vision] Sending request to {model}...")
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
        
        if response.status_code == 200:
            return response.json().get("response", "No response from local model.")
        else:
            return f"Ollama Error: Status {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Local Vision Error: {str(e)}"

@register_tool
def analyze_image_vision(image_path: str, query: str = None) -> str:
    """
    Analyzes an image using a Vision model (Local Ollama or Google Cloud) 
    and explains the findings.
    
    Args:
        image_path: Absolute path to the image file.
        query: Optional question or instruction about the image.
    """
    if not os.path.exists(image_path):
        return f"Error: File not found at {image_path}"

    settings = db.load_settings()
    provider = settings.get("vision_provider", "ollama")
    model = settings.get("vision_model", "moondream")

    if provider == "ollama":
        print(f"[Vision] Routing to local provider (Ollama: {model})")
        analysis = _get_ollama_vision(image_path, query, model)
        return f"--- Local Vision Analysis (Ollama: {model}) ---\n{analysis}"

    # Default to Google Cloud Vision
    print("[Vision] Routing to Google Cloud Vision")
    client = _get_vision_client()
    if not client:
        return ("Error: Google Cloud Vision client initialization failed. "
                "Please go to the Agent Settings UI ⚙️ and ensure the 'Google Vision Key Path' is set to a valid Service Account JSON file.")

    try:
        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        features = [
            vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION),
            vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION),
            vision.Feature(type_=vision.Feature.Type.LANDMARK_DETECTION),
            vision.Feature(type_=vision.Feature.Type.WEB_DETECTION),
            vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION),
        ]
        
        request = vision.AnnotateImageRequest(image=image, features=features)
        response = client.annotate_image(request=request)

        findings = {
            "labels": [label.description for label in response.label_annotations],
            "text": response.full_text_annotation.text if response.full_text_annotation else "No text detected.",
            "landmarks": [lm.description for lm in response.landmark_annotations],
            "objects": [obj.name for obj in response.localized_object_annotations],
            "web_entities": [entity.description for entity in response.web_detection.web_entities if entity.description]
        }

        summary = f"--- Google Cloud Vision Analysis: {os.path.basename(image_path)} ---\n"
        summary += f"Objects: {', '.join(findings['objects']) or 'None'}\n"
        summary += f"Labels: {', '.join(findings['labels'][:10])}\n"
        if findings['landmarks']:
            summary += f"Landmarks: {', '.join(findings['landmarks'])}\n"
        summary += f"OCR Text:\n{findings['text']}\n"
        
        if query:
            from core.deepseek_client import chat_completion_with_tools
            reasoning_prompt = f"""
            You are analyzing results from Google Cloud Vision for an image.
            USER QUERY: {query}
            
            VISION DATA:
            - Labels: {findings['labels']}
            - OCR Text: {findings['text']}
            - Objects: {findings['objects']}
            - Landmarks: {findings['landmarks']}
            - Web Context: {findings['web_entities']}
            
            Explain the image to the user and answer their specific question based on this data.
            """
            ai_resp = chat_completion_with_tools([{"role": "user", "content": reasoning_prompt}], allow_tools=False)
            summary += f"\n--- AI Understanding (DeepSeek) ---\n{ai_resp['reply']}"

        return summary

    except Exception as e:
        return f"Error during Cloud Vision analysis: {str(e)}"
