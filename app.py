import pandas as pd
import streamlit as st
from datetime import date, datetime

# --- Local Module Imports ---
from config.settings import COLUMNS
from backend.extractor import pdf_text, process_image
from backend.parsers import detect_document_type, extract_header, extract_items, extract_rc_details
from backend.calculator import vehicle_age, metal_dep, depreciation_for_row
from backend.exporter import make_excel

# --- Page Setup ---
st.set_page_config(page_title="Motor Claim AI Report System", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem; max-width: 1600px;}
h1,h2,h3 {color:#0b2a4a;}
.small-note {font-size:0.85rem;color:#667085;}
</style>
""", unsafe_allow_html=True)

st.title("Motor Claim AI Report System")
st.caption("Version 0.1 — Upload Document + RC → Extract → Edit → Select → Assess → Excel")

# --- Session State Initialization (FIXED NAMING) ---
if "df_items" not in st.session_state:
    st.session_state["df_items"] = pd.DataFrame(columns=COLUMNS)
if "header" not in st.session_state:
    st.session_state["header"] = {}
if "rc" not in st.session_state:
    st.session_state["rc"] = {}
if "doc_type" not in st.session_state:
    st.session_state["doc_type"] = "Other"
if "raw_text" not in st.session_state:
    st.session_state["raw_text"] = "No extraction performed yet."
if "raw_text" not in st.session_state:
    st.session_state["raw_text"] = "No extraction performed yet."
# Add this new line:
if "rc_raw_text" not in st.session_state:
    st.session_state["rc_raw_text"] = "No RC extraction performed yet."

# --- Main Layout ---
left, mid, right = st.columns([1.1, 1.2, 1.4])

# Column 1: File Upload & Extraction
with left:
    st.subheader("1. Upload Documents")
    docs = st.file_uploader("Upload PDF / image / scanned document", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True)
    rc = st.file_uploader("Registration Certificate (optional)", type=["pdf","png","jpg","jpeg"], accept_multiple_files=False)
    
    if docs:
        st.success(f"{len(docs)} document(s) uploaded")
        if st.button("Extract Data", type="primary"):
            # --- 1. EXTRACT INVOICE DATA ---
            all_text = []
            pages = 0
            for f in docs:
                if f.type == "application/pdf":
                    t, p = pdf_text(f)
                    pages += p
                elif f.type in ["image/png", "image/jpeg", "image/jpg"]:
                    t, p = process_image(f)
                    pages += p
                else:
                    t = ""
                all_text.append(t)
            
            combined = "\n".join(all_text)
            
            st.session_state["header"] = extract_header(combined)
            st.session_state["doc_type"] = detect_document_type(combined, docs[0].name)
            rows = extract_items(combined)
            
            st.session_state["df_items"] = pd.DataFrame(rows, columns=COLUMNS)
            st.session_state["raw_text"] = combined
            st.session_state["page_count"] = pages
            
            # --- 2. EXTRACT RC DATA (NEW) ---
            if rc:
                if rc.type == "application/pdf":
                    rc_text, _ = pdf_text(rc)
                elif rc.type in ["image/png", "image/jpeg", "image/jpg"]:
                    rc_text, _ = process_image(rc)
                else:
                    rc_text = ""
                
                # ADD THIS LINE to save the raw text for debugging:
                st.session_state["rc_raw_text"] = rc_text
                
                # Parse the OCR text using the new backend function
                st.session_state["rc"] = extract_rc_details(rc_text)
                st.success("RC successfully scanned and extracted!")
            else:
                # Clear previous RC data if no file is uploaded this time
                st.session_state["rc"] = {}
                st.session_state["rc_raw_text"] = "No RC extraction performed yet."

            st.success(f"Invoice Extraction complete. {len(rows)} line item(s) found from {pages} document page(s).")
            
    st.caption("Prototype extraction is intentionally transparent; production AI/OCR will replace/extend these parsers.")

# Column 2: Header Editing
with mid:
    st.subheader("2. Document Information")
    h = st.session_state["header"]
    st.write("**Detected document type**")
    
    doc_options = [
        "Repair Estimate", "Repair Invoice", "Revised Estimate", "Supplementary Estimate",
        "Supplementary Invoice", "Parts Invoice", "Labour Invoice", "Other"
    ]
    
    current_index = doc_options.index(st.session_state["doc_type"]) if st.session_state["doc_type"] in doc_options else 7
    st.session_state["doc_type"] = st.selectbox("Document Type", doc_options, index=current_index)
    
    header_keys = ["Invoice No.", "Invoice Date", "Workshop / Supplier", "GSTIN", "Registration No.", "Model", "Chassis No.", "VIN", "Mileage", "Owner / Customer"]
    
    for k in header_keys:
        st.text_input(k, value=h.get(k, ""), key="hdr_"+k)
        
    if st.button("Apply Header Edits"):
        for k in header_keys:
            st.session_state["header"][k] = st.session_state.get("hdr_"+k, "")

# Column 3: Depreciation Calculation
with right:
    st.subheader("3. Vehicle / Owner & Depreciation")
    rc_data = st.session_state["rc"]
    
    reg_no = st.text_input("Registration No.", value=rc_data.get("Registration No.") or h.get("Registration No.", ""), key="rc_reg")
    owner = st.text_input("Owner Name", value=rc_data.get("Owner / Customer") or h.get("Owner / Customer", ""), key="rc_owner")
    reg_date_str = st.text_input("Registration Date (DD/MM/YYYY)", value=rc_data.get("Registration Date", ""), key="rc_date")
    
    asof = date.today()
    reg_date = None
    mrate = 0
    
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            reg_date = datetime.strptime(reg_date_str.strip(), fmt).date()
            break
        except:
            pass
            
    if reg_date:
        ag = vehicle_age(reg_date, asof)
        if ag:
            years, months = ag
            st.session_state["age_text"] = f"{years} Years {months} Months"
            mrate = metal_dep(years, months)
            st.success(f"Vehicle age: {years} years {months} months")
            st.metric("Metal depreciation", f"{mrate}%")
    else:
        st.warning("Enter/verify RC registration date to calculate metal depreciation.")
        
    st.write("**Rules**")
    st.write("Metal (M): age based • Plastic (P): 50% • Glass (G): 0%")

st.divider()

# --- Editable Data Table ---
# --- Editable Data Table ---
st.subheader("4. Extracted Items — Editable")
df = st.session_state.get("df_items")

if isinstance(df, pd.DataFrame) and not df.empty:
    df_copy = df.copy()
    
    # Safely ensure 'Select' column is boolean
    if "Select" in df_copy.columns:
        df_copy["Select"] = df_copy["Select"].fillna(True).astype(bool)
        
    tabs = st.tabs(["All Items", "Parts", "Labour", "Consumables", "Other"])
    
    with tabs[0]:
        try:
            # Try to render the editable table
            edited = st.data_editor(
                df_copy, 
                use_container_width=True, 
                num_rows="dynamic", 
                hide_index=True
            )
            st.session_state["df_items"] = edited
            
        except Exception as e:
            # If PyArrow crashes, catch the error and show it
            st.error(f"Streamlit Data Editor crashed: {e}")
            st.warning("Rendering raw string table as a fallback:")
            # Convert everything to strings so it is guaranteed to render
            st.dataframe(df_copy.astype(str), use_container_width=True)
            
else:
    st.info("Upload a document and click Extract Data.")

# --- Financial Summary & Export ---
st.subheader("5. Assessment Summary")
df_assess = st.session_state["df_items"]

if isinstance(df_assess, pd.DataFrame) and not df_assess.empty:
    selected = df_assess[df_assess["Select"] == True].copy()
    part_amt = selected.loc[selected["Item Type"].eq("Part"), "Taxable Amount (₹)"].fillna(0).sum()
    labour_amt = selected.loc[selected["Item Type"].eq("Labour"), "Taxable Amount (₹)"].fillna(0).sum()
    
    dep_total = 0
    if reg_date:
        ag = vehicle_age(reg_date, asof)
        mrate = metal_dep(*ag) if ag else 0
    else:
        mrate = 0
        
    for _, row in selected.iterrows():
        dep = depreciation_for_row(row, mrate)
        dep_total += float(row.get("Taxable Amount (₹)", 0) or 0) * dep / 100
        
    st.columns(4)[0].metric("Selected Parts", f"₹{part_amt:,.2f}")
    st.columns(4)[1].metric("Selected Labour", f"₹{labour_amt:,.2f}")
    st.columns(4)[2].metric("Depreciation", f"₹{dep_total:,.2f}")
    st.columns(4)[3].metric("Net after depreciation", f"₹{(part_amt + labour_amt - dep_total):,.2f}")

    rc_export_data = {"Registration No.": reg_no, "Owner / Customer": owner, "Registration Date": reg_date_str}
    
    # Export File Generation 
    xlsx = make_excel(
        st.session_state["df_items"], 
        st.session_state["header"], 
        rc_export_data, 
        mrate,
        st.session_state.get("doc_type", ""),
        st.session_state.get("age_text", "")
    )
    
    st.download_button(
            label="Generate Assessment Excel", 
            data=xlsx, 
            file_name="Motor_Claim_AI_Assessment.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            type="primary",
            key="download_excel_btn"  # <--- This unique key prevents the crash
        )
else:
    st.caption("Assessment will appear after extraction.")

# --- Debugging ---
with st.expander("Raw Invoice extracted text (debug / verification)"):
    st.text(st.session_state.get("raw_text", "No extraction performed yet."))

with st.expander("Raw RC extracted text (debug / verification)"):
    st.text(st.session_state.get("rc_raw_text", "No RC extraction performed yet."))