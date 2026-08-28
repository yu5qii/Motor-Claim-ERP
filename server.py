import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd

# Import your existing backend engine
from backend.extractor import process_image, pdf_text
from backend.llm_parser import extract_items_llm, extract_rc_details_llm
from backend.exporter import make_excel

app = Flask(__name__)
CORS(app)  # Unlocks cross-origin requests for your frontend

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "message": "Motor Claim ERP API is running!"
    }), 200

@app.route('/api/extract', methods=['POST'])
def extract_documents():
    """Receives files, runs OCR & LLM, returns JSON."""
    invoice_file = request.files.get('invoice')
    rc_file = request.files.get('rc')
    
    response_data = {"invoice_items": [], "rc_details": {}}

    try:
        # 1. Process Invoice
        if invoice_file:
            # Basic check to route to the correct extractor
            if invoice_file.filename.lower().endswith('.pdf'):
                raw_text, _ = pdf_text(invoice_file)
            else:
                raw_text, _ = process_image(invoice_file)
            
            response_data['invoice_items'] = extract_items_llm(raw_text)

        # 2. Process RC
        if rc_file:
            if rc_file.filename.lower().endswith('.pdf'):
                rc_text, _ = pdf_text(rc_file)
            else:
                rc_text, _ = process_image(rc_file)
                
            response_data['rc_details'] = extract_rc_details_llm(rc_text)

        return jsonify({"status": "success", "data": response_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export', methods=['POST'])
def export_excel():
    """Receives final JSON from the frontend UI, returns an Excel file."""
    try:
        payload = request.json
        
        # Unpack the JSON sent from the browser
        items = payload.get("items", [])
        header = payload.get("header", {})
        rc_data = payload.get("rc_data", {})
        metal_rate = payload.get("metal_rate", 0)
        doc_type = payload.get("doc_type", "Other")
        age_text = payload.get("age_text", "")

        # Your exporter expects a Pandas DataFrame, so we convert the JSON back
        df = pd.DataFrame(items)

        # Generate Excel bytes
        excel_bytes = make_excel(df, header, rc_data, metal_rate, doc_type, age_text)

        # Stream the file back to the browser for download
        return send_file(
            io.BytesIO(excel_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Motor_Claim_AI_Assessment.xlsx'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)