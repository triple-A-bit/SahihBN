import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import requests
from docx import Document
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Smart Halal Scanner", page_icon="🤖")

# --- SIDEBAR: API SETUP ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    st.info("Get your free key at: aistudio.google.com")
    
    # Configure the AI if key is present
    if api_key:
        genai.configure(api_key=api_key)

# --- FUNCTIONS ---

def analyze_image_with_ai(image):
    """
    Uses Gemini AI to look at the image and extract data like a human would.
    """
    if not api_key:
        return None, "Please enter an API Key first."
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # We ask the AI to be a Halal Auditor
    prompt = """
    Analyze this product image for a Halal verification database. 
    Extract the following details into a strict pattern:
    Product Name: [Name]
    Ingredients: [List ingredients if visible, otherwise write 'Not Visible']
    Manufacturer: [Company Name]
    Country of Origin: [Country Name, look for 'Made in' or addresses]
    Halal Status: [Yes if 'Halal' logo/text is found, otherwise 'No']
    
    If the text is cut off or blurry, just infer what you can.
    """
    
    try:
        response = model.generate_content([prompt, image])
        return response.text, None
    except Exception as e:
        return None, str(e)

def search_openfoodfacts(product_name):
    """
    Searches the global OpenFoodFacts database for the product name.
    """
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['products']:
            product = data['products'][0] # Take the first best match
            return {
                "Ingredients": product.get('ingredients_text', 'Not found in DB'),
                "Country": product.get('countries', 'Unknown'),
                "Manufacturer": product.get('brands', 'Unknown')
            }
        return None
    except:
        return None

def parse_ai_response(text):
    """
    Converts the AI's text response into a dictionary.
    """
    data = {
        "Product Name": "",
        "Ingredients": "",
        "Manufacturer": "",
        "Country": "",
        "Halal Certified": False
    }
    
    lines = text.split('\n')
    for line in lines:
        if "Product Name:" in line:
            data["Product Name"] = line.split(":", 1)[1].strip()
        elif "Ingredients:" in line:
            data["Ingredients"] = line.split(":", 1)[1].strip()
        elif "Manufacturer:" in line:
            data["Manufacturer"] = line.split(":", 1)[1].strip()
        elif "Country of Origin:" in line:
            data["Country"] = line.split(":", 1)[1].strip()
        elif "Halal Status:" in line:
            if "Yes" in line:
                data["Halal Certified"] = True
            
    return data

# --- APP UI ---
st.title("🤖 AI Halal Auditor")
st.write("Upload a photo. The AI will read it, or we can search the database.")

uploaded_file = st.file_uploader("Take a picture of the product", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption='Product Image', use_column_width=True)

    if st.button("🚀 Analyze Product"):
        with st.spinner('AI is reading the image (Human-like scanning)...'):
            raw_text, error = analyze_image_with_ai(image)
            
            if error:
                st.error(f"Error: {error}")
            else:
                # 1. Parse AI Data
                extracted_data = parse_ai_response(raw_text)
                
                # 2. Database Fallback Logic
                # If ingredients are missing, try to find them online using the Product Name
                db_data = None
                if extracted_data["Ingredients"] == "Not Visible" or len(extracted_data["Ingredients"]) < 5:
                    st.warning(f"Ingredients not visible in photo. Searching database for '{extracted_data['Product Name']}'...")
                    db_data = search_openfoodfacts(extracted_data["Product Name"])
                    
                    if db_data:
                        st.success("Found details in OpenFoodFacts database!")
                        extracted_data["Ingredients"] = db_data["Ingredients"]
                        if not extracted_data["Country"]:
                            extracted_data["Country"] = db_data["Country"]
                
                # 3. Store in Session State so it doesn't disappear
                st.session_state['data'] = extracted_data

    # --- EDITING & SAVING ---
    if 'data' in st.session_state:
        data = st.session_state['data']
        
        st.divider()
        st.subheader("📝 Verify Details")
        
        with st.form("final_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Product Name", data["Product Name"])
                country = st.text_input("Country of Origin", data["Country"])
            with col2:
                manu = st.text_input("Manufacturer", data["Manufacturer"])
                halal = st.checkbox("Halal Certified?", value=data["Halal Certified"])
            
            ing = st.text_area("Ingredients", data["Ingredients"], height=150)
            
            save_btn = st.form_submit_button("💾 Save Data")
            
            if save_btn:
                # Prepare final DataFrame
                final_df = pd.DataFrame([{
                    "Product Name": name,
                    "Ingredients": ing,
                    "Manufacturer": manu,
                    "Country": country,
                    "Halal Certified": "Yes" if halal else "No"
                }])
                
                st.success("Data saved ready for download!")
                st.table(final_df)
                # (Download buttons code is the same as before)
