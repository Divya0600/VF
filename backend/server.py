from flask import Flask, request, jsonify, send_file, Response, make_response
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

@app.route('/api/forms/preview-filled', methods=['GET'])
def preview_filled_form():
    file_name = request.args.get('file')
    batch_id = request.args.get('batchId')
    
    if not file_name or not batch_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Use the same file finding logic from the download endpoint
    potential_paths = [
        os.path.join('output', 'pdf', batch_id, file_name),
        os.path.join('output', batch_id, file_name),
        os.path.join('output', file_name)
    ]
    
    # Find first existing file path
    file_path = None
    for path in potential_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        return jsonify({'error': 'File not found'}), 404
    
    # Return the PDF with correct headers for preview
    try:
        response = send_file(
            file_path, 
            mimetype='application/pdf',
            as_attachment=False,
            download_name=file_name
        )
        
        # Add headers to prevent caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Error serving PDF preview: {str(e)}")
        return jsonify({'error': f'Error serving PDF: {str(e)}'}), 500


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
    
    # Create new directory structure based on file type
    file_type = "pdf"  # Default to PDF
    output_type_dir = os.path.join('output', file_type)
    output_dir = os.path.join(output_type_dir, batch_id)
    
    # Ensure output directories exist
    if not os.path.exists(output_type_dir):
        os.makedirs(output_type_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save to a more reliable temporary location
    temp_dir = os.path.join('temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    temp_csv_path = os.path.join(temp_dir, f"upload_{batch_id}.csv")
    
    try:
        # Save the file
        file.save(temp_csv_path)
        
        # Verify the file exists before processing
        if not os.path.exists(temp_csv_path):
            return jsonify({'error': 'Failed to save uploaded file'}), 500
        
        # Process the batch with updated output directory
        success = process_batch(form_type, temp_csv_path, output_dir)
        
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
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        
        return jsonify({
            'success': success,
            'batchId': batch_id,
            'successCount': success_count,
            'successRate': "100%" if success_count > 0 else "0%",
            'files': files
        })
        
    except Exception as e:
        import traceback
        print(f"Error processing forms: {str(e)}")
        print(traceback.format_exc())
        
        # Clean up temporary CSV file
        if os.path.exists(temp_csv_path):
            try:
                os.remove(temp_csv_path)
            except:
                pass
                
        return jsonify({'error': f'Error processing forms: {str(e)}'}), 500

def count_csv_rows(csv_file):
    """Count the number of rows in a CSV file"""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header if it exists
            count = sum(1 for _ in reader)
        return max(1, count)  # Ensure we never divide by zero
    except Exception as e:
        print(f"Error counting CSV rows: {e}")
        return 1  # Return 1 to avoid division by zero
    



@app.route('/api/forms/download', methods=['GET'])
def download_form():
    file_name = request.args.get('file')
    batch_id = request.args.get('batchId')
    
    if not file_name:
        return jsonify({'error': 'No filename specified'}), 400
    
    if not batch_id:
        return jsonify({'error': 'No batch ID specified'}), 400
    
    print(f"Download request: file={file_name}, batchId={batch_id}")
    
    # Extract the base name (without extension) to help with flexible matching
    base_name, ext = os.path.splitext(file_name)
    
    # Build list of possible file locations to check
    potential_paths = [
        # Exact filename
        os.path.join('output', 'pdf', batch_id, file_name),
        os.path.join('output', batch_id, file_name),
        os.path.join('output', file_name),
        
        # New ID-based naming scheme (if file included processed_ prefix)
        os.path.join('output', 'pdf', batch_id, file_name.replace('processed_', '')),
        os.path.join('output', batch_id, file_name.replace('processed_', ''))
    ]
    
    # Add additional search for template_ID naming pattern
    if os.path.exists(os.path.join('output', 'pdf', batch_id)):
        # Search for files matching the template name (before "_") and extension
        template_name = base_name.split('_')[0] if '_' in base_name else base_name
        for f in os.scandir(os.path.join('output', 'pdf', batch_id)):
            if f.is_file() and f.name.startswith(template_name) and f.name.endswith(ext):
                potential_paths.append(os.path.join('output', 'pdf', batch_id, f.name))
    
    if os.path.exists(os.path.join('output', batch_id)):
        # Do the same for the regular output/batch_id directory
        template_name = base_name.split('_')[0] if '_' in base_name else base_name
        for f in os.scandir(os.path.join('output', batch_id)):
            if f.is_file() and f.name.startswith(template_name) and f.name.endswith(ext):
                potential_paths.append(os.path.join('output', batch_id, f.name))
    
    # Find first existing file path
    file_path = None
    for path in potential_paths:
        print(f"Checking path: {path}")
        if os.path.exists(path):
            file_path = path
            print(f"Found file at: {file_path}")
            break
    
    if not file_path:
        return jsonify({
            'error': 'File not found',
            'details': {
                'requested_file': file_name,
                'batch_id': batch_id,
                'checked_paths': potential_paths
            }
        }), 404
    
    try:
        # Force file download with explicit headers
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),  # Use actual filename
            mimetype='application/pdf'
        )
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error sending file: {str(e)}")
        return jsonify({'error': f'Error sending file: {str(e)}'}), 500

@app.route('/api/forms/debug-files', methods=['GET'])
def debug_files():
    """Debug endpoint to check processed files and their locations"""
    batch_id = request.args.get('batchId')
    
    output = {
        'cwd': os.getcwd(),
        'output_dir_exists': os.path.exists('output'),
        'directories': {}
    }
    
    # List main output directory
    if os.path.exists('output'):
        output['output_files'] = os.listdir('output')
        
        # Check subdirectories
        for subdir in ['pdf', 'email']:
            subdir_path = os.path.join('output', subdir)
            if os.path.exists(subdir_path):
                output['directories'][subdir] = {
                    'exists': True,
                    'contents': os.listdir(subdir_path)
                }
                
                # If batch_id provided, check that specific batch
                if batch_id and os.path.exists(os.path.join(subdir_path, batch_id)):
                    batch_dir = os.path.join(subdir_path, batch_id)
                    output['directories'][subdir]['batch'] = {
                        'id': batch_id,
                        'exists': True,
                        'files': [
                            {
                                'name': f,
                                'size': os.path.getsize(os.path.join(batch_dir, f)),
                                'modified': os.path.getmtime(os.path.join(batch_dir, f))
                            }
                            for f in os.listdir(batch_dir) if os.path.isfile(os.path.join(batch_dir, f))
                        ]
                    }
    
    return jsonify(output)


@app.route('/api/forms/download-all', methods=['GET'])
def download_all_forms():
    batch_id = request.args.get('batchId')
    if not batch_id:
        return jsonify({'error': 'Batch ID not specified'}), 400
    
    # Check multiple possible directory paths
    batch_paths = [
        os.path.join('output', 'pdf', batch_id),
        os.path.join('output', batch_id),
        os.path.join('output')
    ]
    
    # Find which path exists
    batch_dir = None
    for path in batch_paths:
        print(f"Checking batch path: {path}")
        if os.path.exists(path):
            batch_dir = path
            print(f"Found batch directory: {batch_dir}")
            break
    
    if not batch_dir:
        print(f"Batch directory not found. Checked paths: {batch_paths}")
        return jsonify({'error': f'Batch not found: {batch_id}'}), 404
    
    # Create a ZIP file in memory
    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w') as zf:
            file_count = 0
            for file_name in os.listdir(batch_dir):
                file_path = os.path.join(batch_dir, file_name)
                
                # Only include PDF files that are likely part of this batch
                if os.path.isfile(file_path) and file_name.endswith('.pdf'):
                    # If we're in the output root, only include files with batch_id in their name
                    if batch_dir == os.path.join('output') and batch_id not in file_name:
                        continue
                        
                    zf.write(file_path, file_name)
                    file_count += 1
                    print(f"Added to zip: {file_name}")
            
            if file_count == 0:
                return jsonify({'error': 'No PDF files found in batch directory'}), 404
        
        memory_file.seek(0)
        
        # Create response with the zip file
        response = make_response(memory_file.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="forms_{batch_id}.zip"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"Sending zip with {file_count} files from {batch_dir}")
        return response
    except Exception as e:
        print(f"Error creating ZIP file: {str(e)}")
        return jsonify({'error': f'Error creating ZIP file: {str(e)}'}), 500

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