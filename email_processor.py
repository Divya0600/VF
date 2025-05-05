import os
import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime
import shutil
import tempfile
import email.encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.parser import BytesParser
import mimetypes
from email.utils import decode_params

# Import functions from existing modules
from pdf_form_filler import fill_pdf_form, load_form_config
from email_replacer import replace_in_eml  # Updated import

def process_email_with_attachments(excel_path, template_dir, output_dir):
    """
    Process email templates with replacements and dynamic form attachments
    using data from an Excel file with Data and Attachments sheets.
    """
    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found: {excel_path}")
        return False
        
    if not os.path.exists(template_dir):
        print(f"Error: Template directory not found: {template_dir}")
        return False
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Read the Excel sheets
        email_data = pd.read_excel(excel_path, sheet_name='Data')
        
        # Check if Attachments sheet exists
        try:
            attachment_data = pd.read_excel(excel_path, sheet_name='Attachments')
            has_attachments = True
        except ValueError:
            print("No Attachments sheet found in Excel file. Processing emails without attachments.")
            has_attachments = False
            
        # Get all template files
        template_files = [f for f in os.listdir(template_dir) if f.lower().endswith('.eml')]
        if not template_files:
            print(f"No .eml template files found in {template_dir}")
            return False
            
        print(f"Found {len(template_files)} templates and {len(email_data)} email records")
        
        # Process each template with each row of email data
        successful_files = 0
        
        for template_file in template_files:
            template_path = os.path.join(template_dir, template_file)
            template_name = os.path.splitext(template_file)[0]
            
            # Process each email row
            for i, row in email_data.iterrows():
                if 'mail_ID' not in row:
                    print(f"Warning: 'mail_ID' column missing in row {i+1}. Skipping.")
                    continue
                    
                mail_id = row['mail_ID']
                print(f"\nProcessing template: {template_file} for mail_ID: {mail_id}")
                
                # Create a dictionary of replacements from the row
                replacements = {}
                for col in email_data.columns:
                    if col.endswith('_old') and not pd.isna(row[col]):
                        new_col = col.replace('_old', '_new')
                        if new_col in email_data.columns and not pd.isna(row[new_col]):
                            replacements[str(row[col])] = str(row[new_col])
                
                if not replacements:
                    print(f"Warning: No valid replacements found for mail_ID {mail_id}")
                    continue
                
                # Generate temp output filename for email before attachments
                temp_dir = tempfile.mkdtemp()
                temp_email_path = os.path.join(temp_dir, f"temp_email_{mail_id}.eml")
                
                # Process text replacements in email
                replace_in_eml(template_path, temp_email_path, replacements)
                
                # Check for and process attachments
                attachments_list = []
                if has_attachments:
                    # Filter attachments for this mail_ID
                    mail_attachments = attachment_data[attachment_data['mail_ID'] == mail_id]
                    
                    for j, att_row in mail_attachments.iterrows():
                        if 'form_ID' not in att_row or pd.isna(att_row['form_ID']):
                            print(f"Warning: Missing form_ID for attachment in mail_ID {mail_id}")
                            continue
                            
                        form_id = att_row['form_ID']
                        print(f"  Processing attachment: form_ID = {form_id}")
                        
                        # Extract form data from attachment row
                        form_data = {}
                        for col in attachment_data.columns:
                            if col not in ['mail_ID', 'form_ID'] and not pd.isna(att_row[col]):
                                form_data[col] = str(att_row[col])
                        
                        # Generate filled form
                        form_output = os.path.join(temp_dir, f"filled_form_{form_id}_{mail_id}.pdf")
                        if fill_pdf_form(form_id, form_data, form_output):
                            attachments_list.append((form_output, f"filled_form_{form_id}.pdf"))
                            print(f"  Successfully generated form attachment: {form_id}")
                        else:
                            print(f"  Failed to generate form attachment: {form_id}")
                
                # Final output filename
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_file = f"{template_name}_mail{mail_id}_{timestamp}.eml"
                output_path = os.path.join(output_dir, output_file)
                
                # If we have attachments, add them to the email
                if attachments_list:
                    add_attachments_to_email(temp_email_path, output_path, attachments_list)
                else:
                    # Just move the temp file to final destination
                    shutil.copy2(temp_email_path, output_path)
                
                print(f"  Email saved as: {output_file}")
                successful_files += 1
                
                # Clean up temp files
                shutil.rmtree(temp_dir)
        
        print(f"\nBatch processing complete. Created {successful_files} email files.")
        return successful_files > 0
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False



def add_attachments_to_email(input_email, output_email, attachments):
    """
    Replace attachments in an email with new ones while preserving original formats.
    """
    try:
        # Import necessary libraries
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import io
            pdf_conversion_available = True
        except ImportError:
            print("  Warning: Required libraries not installed. Install with: pip install PyMuPDF Pillow")
            pdf_conversion_available = False

        # Parse the original email
        with open(input_email, 'rb') as f:
            parser = BytesParser()
            original_msg = parser.parse(f)
        
        # Extract original attachments with improved detection
        original_attachments = []
        
        # Debug: Print all message parts and headers to diagnose the issue
        print("  Analyzing email structure:")
        
        # More robust attachment detection
        if original_msg.is_multipart():
            for i, part in enumerate(original_msg.get_payload()):
                print(f"  Part {i} headers: {part.keys()}")
                
                # Try multiple methods to find attachment filename
                filename = None
                
                # Method 1: Check Content-Disposition header
                if 'Content-Disposition' in part:
                    content_disp = part.get('Content-Disposition', '')
                    print(f"  Content-Disposition: {content_disp}")
                    
                    if 'attachment' in content_disp:
                        # Parse using more robust method
                        for param in content_disp.split(';'):
                            param = param.strip()
                            if param.startswith('filename='):
                                filename = param.split('=', 1)[1].strip('"\'')
                                print(f"  Found filename in Content-Disposition: {filename}")
                                break
                
                # Method 2: Check Content-Type header
                if not filename and 'Content-Type' in part:
                    content_type = part.get('Content-Type', '')
                    print(f"  Content-Type: {content_type}")
                    
                    for param in content_type.split(';'):
                        param = param.strip()
                        if param.startswith('name='):
                            filename = param.split('=', 1)[1].strip('"\'')
                            print(f"  Found filename in Content-Type: {filename}")
                            break
                
                # Method 3: Check if there are any image attachments based on Content-Type
                if not filename and 'Content-Type' in part:
                    content_type = part.get('Content-Type', '').lower()
                    if content_type.startswith('image/'):
                        image_type = content_type.split('/', 1)[1].split(';')[0].strip()
                        if image_type == 'jpeg' or image_type == 'jpg':
                            filename = f"attachment.jpeg"
                            print(f"  Detected image attachment of type: {image_type}")
                        elif image_type:
                            filename = f"attachment.{image_type}"
                            print(f"  Detected image attachment of type: {image_type}")
                
                # If we found an attachment filename, add it
                if filename or ('Content-Disposition' in part and 'attachment' in part.get('Content-Disposition', '')):
                    if not filename:
                        # Try to determine extension from Content-Type
                        if 'Content-Type' in part:
                            content_type = part.get('Content-Type', '').lower()
                            if 'image/jpeg' in content_type:
                                filename = "attachment.jpeg"
                            elif 'image/' in content_type:
                                ext = content_type.split('image/')[1].split(';')[0].strip()
                                filename = f"attachment.{ext}"
                            elif 'application/pdf' in content_type:
                                filename = "attachment.pdf"
                            else:
                                filename = "attachment.dat"
                        else:
                            filename = "attachment.dat"
                    
                    original_attachments.append(filename)
                    print(f"  Added attachment: {filename}")
        
        # If no attachments were found but we're expecting some, use JPEG as default
        if not original_attachments and attachments:
            print("  No attachments detected in original email, assuming JPEG")
            original_attachments = ["attachment.jpeg"]
        
        print(f"  Original attachment filenames: {original_attachments}")
        
        # Create a new message without original attachments
        new_msg = MIMEMultipart()
        
        # Copy headers from original
        for key, value in original_msg.items():
            if key.lower() not in ('content-type', 'mime-version'):
                new_msg[key] = value
        
        # Copy non-attachment parts
        if original_msg.is_multipart():
            for part in original_msg.get_payload():
                content_disp = part.get('Content-Disposition', '')
                if 'attachment' not in content_disp:
                    new_msg.attach(part)
        else:
            # Add original content as first part
            new_msg.attach(original_msg)
        
        # Add new attachments with matching original formats
        for i, (file_path, _) in enumerate(attachments):
            # Get original filename or default
            orig_filename = original_attachments[i] if i < len(original_attachments) else f"attachment_{i}.pdf"
            _, orig_ext = os.path.splitext(orig_filename)
            orig_ext = orig_ext.lower()
            
            print(f"  Using original filename: {orig_filename} with extension {orig_ext}")
            
            # Handle format conversion if needed
            converted_file = None
            
            # Convert PDF to image if necessary using PyMuPDF
            if pdf_conversion_available and file_path.lower().endswith('.pdf') and orig_ext in ('.jpg', '.jpeg', '.png', '.gif'):
                try:
                    print(f"  Converting PDF to {orig_ext[1:].upper()} format")
                    
                    # Create temp directory
                    temp_dir = tempfile.mkdtemp()
                    temp_file = os.path.join(temp_dir, f"converted{orig_ext}")
                    
                    # Open PDF with PyMuPDF
                    pdf_document = fitz.open(file_path)
                    if pdf_document.page_count > 0:
                        # Get first page
                        page = pdf_document[0]
                        # Get pixmap with higher resolution
                        zoom = 4.0
                        matrix = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        
                        # Convert to PIL Image for better format control
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Save with proper format
                        if orig_ext in ('.jpg', '.jpeg'):
                            img.save(temp_file, "JPEG", quality=95)
                        elif orig_ext == '.png':
                            img.save(temp_file, "PNG")
                        elif orig_ext == '.gif':
                            img.save(temp_file, "GIF")
                        
                        pdf_document.close()
                        converted_file = temp_file
                        print(f"  Successfully converted PDF to image: {temp_file}")
                except Exception as e:
                    print(f"  Error in PDF conversion: {e}")
                    # Fall back to PDF
                    orig_filename = os.path.splitext(orig_filename)[0] + ".pdf"
                    converted_file = None
            
            # Use the file path if no conversion happened
            if converted_file is None:
                converted_file = file_path
            
            # Determine correct MIME type
            if orig_ext == '.jpg' or orig_ext == '.jpeg':
                main_type, sub_type = 'image', 'jpeg'
            elif orig_ext == '.png':
                main_type, sub_type = 'image', 'png'
            elif orig_ext == '.gif':
                main_type, sub_type = 'image', 'gif'
            elif orig_ext == '.pdf':
                main_type, sub_type = 'application', 'pdf'
            else:
                # Try to guess MIME type or use a default
                mime_type, _ = mimetypes.guess_type(orig_filename)
                if mime_type:
                    main_type, sub_type = mime_type.split('/')
                else:
                    main_type, sub_type = 'application', 'octet-stream'
            
            print(f"  Using MIME type: {main_type}/{sub_type}")
            
            # Create attachment
            with open(converted_file, 'rb') as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
            
            # Encode attachment
            email.encoders.encode_base64(part)
            
            # Use original filename
            part.add_header('Content-Disposition', 'attachment', filename=orig_filename)
            # Also add Content-Type header with filename
            part.add_header('Content-Type', f'{main_type}/{sub_type}', name=orig_filename)
            
            new_msg.attach(part)
            
            # Clean up temp files
            if converted_file != file_path and os.path.exists(converted_file):
                try:
                    os.remove(converted_file)
                    shutil.rmtree(os.path.dirname(converted_file), ignore_errors=True)
                except:
                    pass
        
        # Write final email
        with open(output_email, 'wb') as f:
            f.write(new_msg.as_bytes())
        
        print(f"  Successfully replaced attachments")
        return True
    except Exception as e:
        print(f"Error processing email attachments: {e}")
        import traceback
        traceback.print_exc()
        return False    


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Email Processor with Form Attachments")
    parser.add_argument("-e", "--excel", required=True, help="Excel file with email and attachment data")
    parser.add_argument("-t", "--templates", default="email/input", help="Directory with email templates")
    parser.add_argument("-o", "--output", default="email/output", help="Output directory for processed files")
    args = parser.parse_args()
    
    # Process the batch
    process_email_with_attachments(args.excel, args.templates, args.output)

if __name__ == "__main__":
    main()