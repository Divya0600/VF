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

# Replace the existing preview_form endpoint in server.py

@app.route('/api/forms/preview', methods=['GET'])
def preview_form():
    form_type = request.args.get('formType')
    raw_mode = request.args.get('raw', 'false').lower() == 'true'
    
    if not form_type:
        return jsonify({'error': 'Form type not specified'}), 400
    
    # Load form configuration
    config = load_form_config(form_type)
    
    if not config or 'empty_form_file' not in config:
        return jsonify({'error': 'Form not found or missing empty_form_file in config'}), 404
    
    # Check if the file exists
    pdf_path = config['empty_form_file']
    if not os.path.exists(pdf_path):
        print(f"PDF file not found at: {pdf_path}")
        print(f"Current working directory: {os.getcwd()}")
        return jsonify({
            'error': 'Form template file not found', 
            'path': pdf_path,
            'cwd': os.getcwd()
        }), 404
    
    # Log the path for debugging
    print(f"Serving PDF: {pdf_path}")
    
    # Return the empty form PDF with correct headers
    try:
        # Explicitly read the file and return its contents
        if raw_mode:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            
            response = Response(pdf_data, mimetype='application/pdf')
            response.headers['Content-Disposition'] = f'inline; filename="{form_type}.pdf"'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            # Standard send_file approach
            response = send_file(
                pdf_path, 
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f"{form_type}.pdf"
            )
            
            # Add headers to prevent caching issues
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Content-Type'] = 'application/pdf'
            return response
            
    except Exception as e:
        print(f"Error serving PDF: {str(e)}")
        # Return more detailed error information
        return jsonify({
            'error': 'Error serving PDF',
            'message': str(e),
            'path': pdf_path,
            'file_exists': os.path.exists(pdf_path),
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        }), 500


# Add this function to help you debug the PDF file locations
@app.route('/api/forms/file-check', methods=['GET'])
def check_form_files():
    """Debug endpoint to check all form files and their existence"""
    form_files = {}
    forms = list_available_forms()
    
    # First check configuration directory
    config_dir = os.path.join(os.getcwd(), 'forms')
    if os.path.exists(config_dir):
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    else:
        config_files = []
    
    for form_id in forms:
        config = load_form_config(form_id)
        if not config:
            form_files[form_id] = {
                'config_found': False,
                'pdf_path': None,
                'pdf_exists': False
            }
            continue
            
        pdf_path = config.get('empty_form_file', None)
        pdf_exists = pdf_path and os.path.exists(pdf_path)
        
        form_files[form_id] = {
            'config_found': True,
            'pdf_path': pdf_path,
            'pdf_exists': pdf_exists,
            'pdf_size': os.path.getsize(pdf_path) if pdf_exists else 0
        }
    
    return jsonify({
        'working_directory': os.getcwd(),
        'config_directory': config_dir,
        'config_directory_exists': os.path.exists(config_dir),
        'config_files': config_files if os.path.exists(config_dir) else [],
        'form_files': form_files
    })
    
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



@app.route('/api/forms/pdf-debug', methods=['GET'])
def debug_pdf_serving():
    """Debug endpoint to test PDF serving capabilities"""
    form_type = request.args.get('formType')
    
    if not form_type:
        return jsonify({
            'status': 'error',
            'message': 'Form type not specified',
            'available_forms': list_available_forms()
        }), 400
    
    # Load form configuration
    config = load_form_config(form_type)
    
    if not config:
        return jsonify({
            'status': 'error',
            'message': 'Form config not found',
            'form_type': form_type,
            'available_forms': list_available_forms()
        }), 404
        
    if 'empty_form_file' not in config:
        return jsonify({
            'status': 'error',
            'message': 'Form template file path not defined in config',
            'config_keys': list(config.keys())
        }), 404
    
    # Check if the file exists
    pdf_path = config['empty_form_file']
    file_exists = os.path.exists(pdf_path)
    
    if not file_exists:
        return jsonify({
            'status': 'error',
            'message': 'PDF file not found at specified path',
            'pdf_path': pdf_path,
            'working_directory': os.getcwd(),
            'file_exists': file_exists
        }), 404
    
    # Return file info instead of the actual file
    file_size = os.path.getsize(pdf_path)
    
    return jsonify({
        'status': 'success',
        'message': 'PDF file found and accessible',
        'pdf_path': pdf_path,
        'file_size': f"{file_size / 1024:.2f} KB",
        'mime_type': 'application/pdf',
        'preview_url': f"/api/forms/preview?formType={form_type}"
    })
if __name__ == '__main__':
    # Ensure output directory exists
    if not os.path.exists('output'):
        os.makedirs('output')
    
    app.run(debug=True, port=5000)