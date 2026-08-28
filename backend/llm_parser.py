import json
import re
import streamlit as st
import google.generativeai as genai

# Initialize the Gemini client
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Directly connect to the newest model, bypassing auto-discovery
model = genai.GenerativeModel('gemini-3.6-flash')

def extract_json_from_text(text):
    """Aggressively hunts for JSON in the LLM response to prevent formatting crashes."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # If direct parsing fails, use regex to find JSON blocks
    text = text.strip()
    match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    if match:
        clean_text = match.group(1).strip()
    else:
        # Fallback: find the first [ or { and last ] or }
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        clean_text = match.group(1).strip() if match else text
        
    try:
        return json.loads(clean_text)
    except Exception:
        raise ValueError(f"Could not parse JSON. Raw LLM output: {text[:100]}...")

def extract_items_llm(raw_text):
    """Uses Gemini to extract line items using a strict JSON template."""
    prompt = f"""
    You are a data extraction assistant for an automotive claims ERP.
    Extract all car parts, consumables, and labour charges from the OCR text.
    
    Return ONLY a JSON array. Do NOT wrap it in any markdown.
    You MUST match this exact structure and key names for every item:
    [
      {{
        "Select": true,
        "Item Type": "Part", 
        "Description": "FRONT BUMPER",
        "Part No. / Labour Code": "87089900",
        "HSN / SAC": "8708",
        "PMG": "",
        "Qty": 1.0,
        "Unit": "NOS",
        "Rate (₹)": 1500.0,
        "Taxable Amount (₹)": 1500.0,
        "GST %": 18.0,
        "GST Amount (₹)": 270.0
      }}
    ]

    OCR Text:
    {raw_text}
    """
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0)
        )
        data = extract_json_from_text(response.text)
        
        # Unwrap if wrapped in a dict
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    return v
            return []
        return data
    except Exception as e:
        st.error(f"Item Extraction Error: {e}") 
        return []

def extract_rc_details_llm(raw_text):
    """Uses Gemini to extract RC details across ANY state or smart-card format."""
    prompt = f"""
    You are an expert data extraction assistant for an automotive claims ERP. 
    Extract vehicle registration details from the OCR text of an Indian Registration Certificate (RC). 
    
    CRITICAL INSTRUCTIONS:
    1. Look for common abbreviations (REGN DT, CH NO, NAME, etc).
    2. Correct obvious OCR typos (e.g. 't4-Jul' -> '14-Jul', 'Chassis Na' -> 'Chassis No').
    3. Ignore relational text like "S/W/D". Extract ONLY the primary owner's name.
    
    Return ONLY a JSON object matching this EXACT structure and key names:
    {{
        "Registration No.": "UP16FA7290",
        "Owner / Customer": "RAJ KUMAR",
        "Registration Date": "14/07/2025",
        "Chassis No.": "MA3JMT31SKG189864"
    }}

    OCR Text:
    {raw_text}
    """
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0)
        )
        data = extract_json_from_text(response.text)
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
            
        if "Registration No" in data and "Registration No." not in data:
            data["Registration No."] = data.pop("Registration No")
        if "Chassis No" in data and "Chassis No." not in data:
            data["Chassis No."] = data.pop("Chassis No")
            
        return data
    except Exception as e:
        st.error(f"RC Extraction Error: {e}")
        return {}