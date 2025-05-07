from flask import Flask, request, jsonify, send_file, Response, make_response
import os
import json
import tempfile
import zipfile
import io
import csv
import time
from pathlib import Path
from pdf_form_filler import load_form_config, list_available_forms, fill_pdf_form, process_batch
from email_replacer import batch_process_emails
from email_processor import process_email_with_attachments

app = Flask(__name__)

# Helper function to identify email templates
import os

def get_email_templates():
    """Get list of available email templates"""
    templates = []
    email_dir = os.path.join('input', 'email')  # Updated path
    if os.path.exists(email_dir):
        templates = [os.path.splitext(f)[0] for f in os.listdir(email_dir) if f.endswith('.eml')]
    return templates


# Ensure required directories exist
def ensure_directories():
    """Create necessary directories if they don't exist"""
    required_dirs = [
        'output',
        'output/pdf',
        'output/email',
        'forms_config'
    ]
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {directory} directory")

@app.route('/api/forms/types', methods=['GET'])
def get_form_types():
    # List available form configurations
    forms = list_available_forms()
    
    # Include proper categorized form types
    form_types = [
        {'id': 'all', 'name': 'All Forms'},
        {'id': 'pdf', 'name': 'PDF Forms'},
        {'id': 'email', 'name': 'Email Templates'},
        {'id': 'tif', 'name': 'TIF Images'}
    ]
    
    return jsonify({'formTypes': form_types})

@app.route('/api/forms/templates', methods=['GET'])
def get_templates():
    # First get all PDF forms from config files
    forms = list_available_forms()
    templates = []
    
    for form_id in forms:
        config = load_form_config(form_id)
        if config:
            templates.append({
                'id': form_id,
                'name': config.get('name', form_id),
                'description': config.get('description', ''),
                'type': 'pdf',  # All these are PDF forms
                'lastModified': '2025-03-18'
            })
    
    # Now add email templates (which don't have config files)
    email_dir = os.path.join('input', 'email')  # Updated path
    if os.path.exists(email_dir):
        for filename in os.listdir(email_dir):
            if filename.endswith('.eml'):
                template_id = os.path.splitext(filename)[0]
                templates.append({
                    'id': template_id,
                    'name': template_id.replace('_', ' ').title(),  # Create a name from the filename
                    'description': 'Email template',
                    'type': 'email',
                    'lastModified': '2025-03-18'
                })
    
    return jsonify({'templates': templates})

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

# Update existing preview-email endpoint or add this new one
@app.route('/api/forms/preview-email', methods=['GET'])
def preview_email_template():
    template_id = request.args.get('templateId')
    
    if not template_id:
        return jsonify({'error': 'Email template ID not specified'}), 400
    
    # Find the email template file
    template_path = os.path.join('input','email', f"{template_id}.eml")
    
    if not os.path.exists(template_path):
        return jsonify({'error': 'Email template not found'}), 404
    
    # Parse the email template content using the same logic as processed emails
    try:
        from email import message_from_bytes
        import email.utils
        from email.header import decode_header
        
        # Helper function to try multiple encodings
        def try_decode_with_encodings(content, encodings=['utf-8', 'iso-8859-1', 'windows-1252']):
            if not content:
                return ""
            
            for encoding in encodings:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            # Fallback with replacements
            return content.decode('utf-8', errors='replace')
        
        # Read file as binary
        with open(template_path, 'rb') as f:
            file_content = f.read()
        
        # Parse email from bytes
        msg = message_from_bytes(file_content)
        
        # Extract and decode subject
        subject = msg.get('Subject', '(No Subject)')
        decoded_subject = []
        for part, encoding in decode_header(subject):
            if isinstance(part, bytes):
                decoded_subject.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_subject.append(part)
        subject = ''.join(decoded_subject)
        
        # Extract date
        date_str = msg.get('Date', '')
        if date_str:
            try:
                date_tuple = email.utils.parsedate_tz(date_str)
                formatted_date = email.utils.formatdate(email.utils.mktime_tz(date_tuple), localtime=True)
            except:
                formatted_date = date_str
        else:
            formatted_date = ''
        
        # Decode From field
        from_field = msg.get('From', '')
        decoded_from = []
        for part, encoding in decode_header(from_field):
            if isinstance(part, bytes):
                decoded_from.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_from.append(part)
        from_field = ''.join(decoded_from)
        
        # Decode To field
        to_field = msg.get('To', '')
        decoded_to = []
        for part, encoding in decode_header(to_field):
            if isinstance(part, bytes):
                decoded_to.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_to.append(part)
        to_field = ''.join(decoded_to)
        
        # Get body content and attachments
        body = ''
        html_body = ''
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                
                # Check if this part is an attachment
                if disposition and disposition.lower() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        decoded_filename = []
                        for fname_part, fname_encoding in decode_header(filename):
                            if isinstance(fname_part, bytes):
                                decoded_filename.append(try_decode_with_encodings(
                                    fname_part, [fname_encoding] if fname_encoding else None))
                            else:
                                decoded_filename.append(fname_part)
                        decoded_filename = ''.join(decoded_filename)
                        
                        # Add attachment info to list
                        attachments.append({
                            'name': decoded_filename,
                            'size': f"{len(part.get_payload(decode=True) or b'') / 1024:.1f} KB",
                            'type': content_type
                        })
                elif content_type == 'text/plain':
                    # Plain text body
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
                elif content_type == 'text/html':
                    # HTML body - preferred for display
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
        else:
            # Not multipart, just get the payload
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
        
        # If we have HTML body, prefer that over plain text
        display_body = html_body or body
        
        return jsonify({
            'templateId': template_id,
            'fileName': f"{template_id}.eml",
            'subject': subject,
            'date': formatted_date,
            'from': from_field,
            'to': to_field,
            'body': display_body,
            'plainBody': body if html_body else '',
            'attachments': attachments,
            'isHtml': bool(html_body),
            'rawContent': try_decode_with_encodings(file_content)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error parsing email template: {str(e)}")
        print(error_details)
        return jsonify({
            'error': f'Error parsing email template: {str(e)}',
            'details': error_details
        }), 500

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
    file_type = request.args.get('type', None)  # Optional type parameter
    
    if not file_name or not batch_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Determine file type based on extension if not provided
    if not file_type:
        _, ext = os.path.splitext(file_name)
        file_type = "email" if ext.lower() == ".eml" else "pdf"
    
    # Build potential paths based on file type
    potential_paths = [
        os.path.join('output', file_type, batch_id, file_name),
        os.path.join('output', batch_id, file_name),
        os.path.join('output', file_name)
    ]
    
    # Add email-specific paths if needed
    if file_type == "email":
        potential_paths.extend([
            os.path.join('output', 'email', batch_id, file_name),
            os.path.join('output', 'email', file_name)
        ])
    
    # Find first existing file path
    file_path = None
    for path in potential_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        return jsonify({'error': 'File not found'}), 404
    
    # Return the file with correct headers for preview
    try:
        # Determine MIME type based on extension
        if file_path.endswith('.eml'):
            mime_type = 'message/rfc822'
        else:
            mime_type = 'application/pdf'
            
        response = send_file(
            file_path, 
            mimetype=mime_type,
            as_attachment=False,
            download_name=file_name
        )
        
        # Add headers to prevent caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Error serving file preview: {str(e)}")
        return jsonify({'error': f'Error serving file: {str(e)}'}), 500

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
    
    # Ensure required directories exist
    ensure_directories()
    
    # Create a unique batch ID
    batch_id = f"batch_{int(time.time())}"
    
    # Determine if this is an email template
    email_templates = get_email_templates()
    is_email = form_type in email_templates
    
    # Set file type and create directory structure
    file_type = "email" if is_email else "pdf"
    output_type_dir = os.path.join('output', file_type)
    output_dir = os.path.join(output_type_dir, batch_id)
    
    # Ensure output directories exist
    if not os.path.exists(output_type_dir):
        os.makedirs(output_type_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save to a temporary location
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
        
        success = False
        files = []
        
        # Process based on file type
        if is_email:
            # Email processing
            try:
                # Check if it's an Excel file for email with attachments
                if file.filename.endswith('.xlsx'):
                    success = process_email_with_attachments(temp_csv_path, 'input/email', output_dir)
                else:
                    # Regular CSV for email replacements
                    success = batch_process_emails(temp_csv_path, 'input/email', output_dir)
                
                # List generated email files
                if os.path.exists(output_dir):
                    for filename in os.listdir(output_dir):
                        if filename.endswith('.eml'):
                            file_path = os.path.join(output_dir, filename)
                            file_size = os.path.getsize(file_path)
                            files.append({
                                'name': filename,
                                'size': f"{file_size / 1024:.2f} KB",
                                'date': time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(file_path)))
                            })
            except Exception as e:
                print(f"Error in email processing: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error processing emails: {str(e)}'}), 500
        else:
            # PDF form processing (use existing code)
            success = process_batch(form_type, temp_csv_path, output_dir)
            
            # Count the number of files in the output directory
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
            'fileType': file_type,
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

@app.route('/api/forms/download', methods=['GET'])
def download_form():
    file_name = request.args.get('file')
    batch_id = request.args.get('batchId')
    file_type = request.args.get('type', None)  # Optional type parameter
    
    if not file_name:
        return jsonify({'error': 'No filename specified'}), 400
    
    if not batch_id:
        return jsonify({'error': 'No batch ID specified'}), 400
    
    print(f"Download request: file={file_name}, batchId={batch_id}, type={file_type}")
    
    # Determine file type based on extension if not provided
    if not file_type:
        _, ext = os.path.splitext(file_name)
        file_type = "email" if ext.lower() == ".eml" else "pdf"
    
    # Build list of possible file locations to check
    potential_paths = [
        # Primary paths based on file type
        os.path.join('output', file_type, batch_id, file_name),
        # Legacy paths
        os.path.join('output', batch_id, file_name),
        os.path.join('output', file_name)
    ]
    
    # Add email-specific paths if needed
    if file_type == "email":
        potential_paths.extend([
            os.path.join( 'output','email', batch_id, file_name),
            os.path.join('output', 'email',file_name)
        ])
    
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
                'file_type': file_type,
                'checked_paths': potential_paths
            }
        }), 404
    
    try:
        # Determine MIME type based on extension
        if file_path.endswith('.eml'):
            mime_type = 'message/rfc822'
        else:
            mime_type = 'application/pdf'
            
        # Force file download with explicit headers
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),  # Use actual filename
            mimetype=mime_type
        )
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error sending file: {str(e)}")
        return jsonify({'error': f'Error sending file: {str(e)}'}), 500

@app.route('/api/forms/download-all', methods=['GET'])
def download_all_forms():
    batch_id = request.args.get('batchId')
    file_type = request.args.get('type', None)  # Optional type parameter
    
    if not batch_id:
        return jsonify({'error': 'Batch ID not specified'}), 400
    
    # Check multiple possible directory paths
    batch_paths = []
    
    if file_type == "email":
        # Email-specific paths
        batch_paths = [
            os.path.join('output', 'email', batch_id),
            os.path.join( 'output','email', batch_id)
        ]
    elif file_type == "pdf":
        # PDF-specific paths
        batch_paths = [
            os.path.join('output', 'pdf', batch_id)
        ]
    else:
        # Check all possible paths if type not specified
        batch_paths = [
            os.path.join('output', 'pdf', batch_id),
            os.path.join('output', 'email', batch_id),
            os.path.join('output', batch_id),
            os.path.join( 'output','email', batch_id)
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
            
            # Determine appropriate extensions based on directory
            if 'email' in batch_dir:
                extensions = ['.eml']
                zip_prefix = 'email'
            else:
                extensions = ['.pdf']
                zip_prefix = 'pdf'
            
            for file_name in os.listdir(batch_dir):
                file_path = os.path.join(batch_dir, file_name)
                
                # Only include files with the correct extension
                if os.path.isfile(file_path) and any(file_name.endswith(ext) for ext in extensions):
                    # If we're in the output root, only include files with batch_id in their name
                    if (batch_dir == os.path.join('output') or 
                        batch_dir == os.path.join( 'output','email',)) and batch_id not in file_name:
                        continue
                        
                    zf.write(file_path, file_name)
                    file_count += 1
                    print(f"Added to zip: {file_name}")
            
            if file_count == 0:
                return jsonify({'error': f'No {zip_prefix.upper()} files found in batch directory'}), 404
        
        memory_file.seek(0)
        
        # Create response with the zip file
        response = make_response(memory_file.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="{zip_prefix}_{batch_id}.zip"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"Sending zip with {file_count} files from {batch_dir}")
        return response
    except Exception as e:
        print(f"Error creating ZIP file: {str(e)}")
        return jsonify({'error': f'Error creating ZIP file: {str(e)}'}), 500

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

@app.route('/api/forms/file-check', methods=['GET'])
def check_form_files():
    """Debug endpoint to check all form files and their existence"""
    form_files = {}
    forms = list_available_forms()
    
    # First check PDF configuration directory
    config_dir = os.path.join(os.getcwd(), 'forms_config')
    if os.path.exists(config_dir):
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    else:
        config_files = []
    
    # Check email templates directory
    email_dir = os.path.join(os.getcwd(), 'email', 'input')
    if os.path.exists(email_dir):
        email_files = [f for f in os.listdir(email_dir) if f.endswith('.eml')]
    else:
        email_files = []
    
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
    
    # Add email template info
    for email_file in email_files:
        template_id = os.path.splitext(email_file)[0]
        email_path = os.path.join(email_dir, email_file)
        
        form_files[template_id] = {
            'config_found': False,  # Emails don't use config
            'email_path': email_path,
            'email_exists': os.path.exists(email_path),
            'email_size': os.path.getsize(email_path) if os.path.exists(email_path) else 0,
            'type': 'email'
        }
    
    return jsonify({
        'working_directory': os.getcwd(),
        'config_directory': config_dir,
        'config_directory_exists': os.path.exists(config_dir),
        'config_files': config_files if os.path.exists(config_dir) else [],
        'email_directory': email_dir,
        'email_directory_exists': os.path.exists(email_dir),
        'email_files': email_files if os.path.exists(email_dir) else [],
        'form_files': form_files
    })

# Add this new route to server.py

@app.route('/api/forms/preview-processed-email', methods=['GET'])
def preview_processed_email():
    file_name = request.args.get('file')
    batch_id = request.args.get('batchId')
    
    if not file_name or not batch_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Find the email file in output directories
    potential_paths = [
        os.path.join('output', 'email', batch_id, file_name),
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
        return jsonify({'error': 'Email file not found'}), 404
    
    # Parse the email file to extract subject and body
    try:
        from email import message_from_bytes
        import email.utils
        from email.header import decode_header
        
        # Helper function to try multiple encodings
        def try_decode_with_encodings(content, encodings=['utf-8', 'iso-8859-1', 'windows-1252']):
            if not content:
                return ""
            
            for encoding in encodings:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            # Fallback with replacements
            return content.decode('utf-8', errors='replace')
        
        # Read file as binary
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Parse email from bytes
        msg = message_from_bytes(file_content)
        
        # Extract and decode subject
        subject = msg.get('Subject', '(No Subject)')
        decoded_subject = []
        for part, encoding in decode_header(subject):
            if isinstance(part, bytes):
                decoded_subject.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_subject.append(part)
        subject = ''.join(decoded_subject)
        
        # Extract date
        date_str = msg.get('Date', '')
        if date_str:
            try:
                date_tuple = email.utils.parsedate_tz(date_str)
                formatted_date = email.utils.formatdate(email.utils.mktime_tz(date_tuple), localtime=True)
            except:
                formatted_date = date_str
        else:
            formatted_date = ''
        
        # Decode From field
        from_field = msg.get('From', '')
        decoded_from = []
        for part, encoding in decode_header(from_field):
            if isinstance(part, bytes):
                decoded_from.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_from.append(part)
        from_field = ''.join(decoded_from)
        
        # Decode To field
        to_field = msg.get('To', '')
        decoded_to = []
        for part, encoding in decode_header(to_field):
            if isinstance(part, bytes):
                decoded_to.append(try_decode_with_encodings(part, [encoding] if encoding else None))
            else:
                decoded_to.append(part)
        to_field = ''.join(decoded_to)
        
        # Get body content and attachments
        body = ''
        html_body = ''
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                
                # Check if this part is an attachment
                if disposition and disposition.lower() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        decoded_filename = []
                        for fname_part, fname_encoding in decode_header(filename):
                            if isinstance(fname_part, bytes):
                                decoded_filename.append(try_decode_with_encodings(
                                    fname_part, [fname_encoding] if fname_encoding else None))
                            else:
                                decoded_filename.append(fname_part)
                        decoded_filename = ''.join(decoded_filename)
                        
                        # Add attachment info to list
                        attachments.append({
                            'name': decoded_filename,
                            'size': f"{len(part.get_payload(decode=True) or b'') / 1024:.1f} KB",
                            'type': content_type
                        })
                elif content_type == 'text/plain':
                    # Plain text body
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
                elif content_type == 'text/html':
                    # HTML body - preferred for display
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
        else:
            # Not multipart, just get the payload
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = try_decode_with_encodings(payload, [charset, 'utf-8', 'iso-8859-1', 'windows-1252'])
        
        # If we have HTML body, prefer that over plain text
        display_body = html_body or body
        
        return jsonify({
            'fileName': file_name,
            'subject': subject,
            'date': formatted_date,
            'from': from_field,
            'to': to_field,
            'body': display_body,
            'plainBody': body if html_body else '',
            'attachments': attachments,
            'isHtml': bool(html_body)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error parsing email file: {str(e)}")
        print(error_details)
        return jsonify({
            'error': f'Error parsing email: {str(e)}',
            'details': error_details
        }), 500

if __name__ == '__main__':
    # Create necessary directories at startup
    ensure_directories()
    app.run(debug=True, port=5000)