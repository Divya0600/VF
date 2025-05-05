from flask import Flask, request, jsonify, send_file, Response
import os
import json
import tempfile
import zipfile
import io
import csv
from pdf_form_filler import load_form_config, list_available_forms, fill_pdf_form, process_batch

app = Flask(__name__)

# API endpoints for form operations
@app.route('/api/forms/types', methods=['GET'])
def get_form_types():
    # List available form configurations
    forms = list_available_forms()
    form_types = []
    
    for form_id in forms:
        config = load_form_config(form_id)
        if config:
            form_types.append({
                'id': form_id,
                'name': config.get('name', form_id),
                'type': 'pdf'  # You could determine this based on the form config
            })
    
    return jsonify({'formTypes': form_types})


# Make sure your preview_form endpoint in server.py properly serves PDF files:

@app.route('/api/forms/preview', methods=['GET'])
def preview_form():
    form_type = request.args.get('formType')
    
    if not form_type:
        return jsonify({'error': 'Form type not specified'}), 400
    
    # Load form configuration
    config = load_form_config(form_type)
    
    if not config or 'empty_form_file' not in config:
        return jsonify({'error': 'Form not found'}), 404
    
    # Check if the file exists
    pdf_path = config['empty_form_file']
    if not os.path.exists(pdf_path):
        return jsonify({'error': f'Form template file not found: {pdf_path}'}), 404
    
    # Log the path for debugging
    print(f"Serving PDF: {pdf_path}")
    
    # Return the empty form PDF with correct headers
    try:
        return send_file(
            pdf_path, 
            mimetype='application/pdf',
            as_attachment=False,  # Important: set to False to display in browser
            download_name=f"{form_type}.pdf"  # Set a proper file name
        )
    except Exception as e:
        print(f"Error serving PDF: {str(e)}")
        return jsonify({'error': f'Error serving PDF: {str(e)}'}), 500


@app.route('/api/forms/templates', methods=['GET'])
def get_templates():
    forms = list_available_forms()
    templates = []
    
    for form_id in forms:
        config = load_form_config(form_id)
        if config:
            templates.append({
                'id': form_id,
                'name': config.get('name', form_id),
                'description': config.get('description', ''),
                'type': 'pdf',  # You could determine this based on the form config
                'lastModified': '2025-03-18'  # You could get this from the file
            })
    
    return jsonify({'templates': templates})



@app.route('/api/forms/preview-csv', methods=['POST'])
def preview_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    # Parse CSV
    try:
        # Save to a temporary file
        temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        file.save(temp_csv.name)
        temp_csv.close()
        
        with open(temp_csv.name, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = []
            for row in reader:
                rows.append(row)
        
        os.unlink(temp_csv.name)  # Clean up
        
        return jsonify({
            'headers': headers,
            'rows': rows
        })
    except Exception as e:
        return jsonify({'error': f'Error parsing CSV: {str(e)}'}), 400

@app.route('/api/forms/process', methods=['POST'])
def process_forms():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    form_type = request.form.get('formType')
    
    if not form_type:
        return jsonify({'error': 'Form type not specified'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Create a unique batch ID
    import time
    batch_id = f"batch_{int(time.time())}"
    output_dir = os.path.join('output', batch_id)
    
    # Save to a temporary file
    temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
    file.save(temp_csv.name)
    temp_csv.close()
    
    try:
        # Process the batch
        success = process_batch(form_type, temp_csv.name, output_dir)
        
        # Count the number of files in the output directory
        files = []
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(output_dir, filename)
                    file_size = os.path.getsize(file_path)
                    files.append({
                        'name': filename,
                        'size': f"{file_size / 1024:.2f} KB",
                        'date': time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(file_path)))
                    })
        
        success_count = len(files)
        
        # Clean up temporary CSV file
        os.unlink(temp_csv.name)
        
        return jsonify({
            'success': success,
            'batchId': batch_id,
            'successCount': success_count,
            'successRate': f"{success_count / count_csv_rows(temp_csv.name) * 100:.0f}%" if success_count > 0 else "0%",
            'files': files
        })
        
    except Exception as e:
        # Clean up temporary CSV file
        if os.path.exists(temp_csv.name):
            os.unlink(temp_csv.name)
        return jsonify({'error': f'Error processing forms: {str(e)}'}), 500

def count_csv_rows(csv_file):
    """Count the number of rows in a CSV file"""
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        return sum(1 for _ in reader)

@app.route('/api/forms/download', methods=['GET'])
def download_form():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name not specified'}), 400
    
    # Check if the file exists in any batch directory
    for batch_dir in os.listdir('output'):
        batch_path = os.path.join('output', batch_dir)
        if os.path.isdir(batch_path):
            file_path = os.path.join(batch_path, file_name)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/forms/download-all', methods=['GET'])
def download_all_forms():
    batch_id = request.args.get('batchId')
    if not batch_id:
        return jsonify({'error': 'Batch ID not specified'}), 400
    
    batch_dir = os.path.join('output', batch_id)
    if not os.path.exists(batch_dir):
        return jsonify({'error': 'Batch not found'}), 404
    
    # Create a ZIP file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for file_name in os.listdir(batch_dir):
            file_path = os.path.join(batch_dir, file_name)
            if os.path.isfile(file_path):
                zf.write(file_path, file_name)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{batch_id}.zip'
    )

if __name__ == '__main__':
    # Ensure output directory exists
    if not os.path.exists('output'):
        os.makedirs('output')
    
    app.run(debug=True, port=5000)