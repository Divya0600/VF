import os
import shutil
import csv
from pathlib import Path
import argparse
from datetime import datetime

def batch_process_emails(csv_path, template_dir, output_dir):
    """
    Process multiple email templates with multiple sets of replacements
    from a single CSV file.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        return False
        
    if not os.path.exists(template_dir):
        print(f"Error: Template directory not found: {template_dir}")
        return False
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the CSV data
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if not rows:
            print("No data found in CSV file")
            return False
            
        # Get all template files
        template_files = [f for f in os.listdir(template_dir) if f.lower().endswith('.eml')]
        if not template_files:
            print(f"No .eml template files found in {template_dir}")
            return False
            
        print(f"Found {len(template_files)} templates and {len(rows)} replacement sets")
        
        # Process each template with each row of replacement data
        successful_files = 0
        for template_file in template_files:
            template_path = os.path.join(template_dir, template_file)
            template_name = os.path.splitext(template_file)[0]
            
            for i, row in enumerate(rows):
                # Create a dictionary of replacements from the row
                replacements = {}
                for key, value in row.items():
                    if key.endswith('_old') and value:
                        new_key = key.replace('_old', '_new')
                        if new_key in row:
                            replacements[value] = row[new_key]
                
                if not replacements:
                    print(f"Warning: No valid replacements found for row {i+1}")
                    continue
                
                # Generate output filename
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_file = f"{template_name}_set{i+1}_{timestamp}.eml"
                output_path = os.path.join(output_dir, output_file)
                
                print(f"\nProcessing template: {template_file} with replacement set {i+1}")
                if replace_in_eml(template_path, output_path, replacements):
                    successful_files += 1
        
        print(f"\nBatch processing complete. Created {successful_files} email files.")
        return successful_files > 0
        
    except Exception as e:
        print(f"Error during batch processing: {e}")
        return False

def replace_in_eml(input_file, output_file, replacements):
    """
    Replace content in .eml file while preserving the exact format.
    """
    try:
        # Read the file in binary mode
        with open(input_file, 'rb') as f:
            content_bytes = f.read()
        
        # Detect encoding - try common email encodings
        encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
        detected_encoding = None
        
        for encoding in encodings:
            try:
                content = content_bytes.decode(encoding)
                detected_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if not detected_encoding:
            # Fallback with replacement for errors
            content = content_bytes.decode('utf-8', errors='replace')
            detected_encoding = 'utf-8'
        
        # Make the replacements
        original_content = content
        replacements_made = 0
        
        for old_text, new_text in replacements.items():
            count = content.count(old_text)
            if count > 0:
                content = content.replace(old_text, new_text)
                replacements_made += count
                print(f"  Replaced '{old_text}' with '{new_text}': {count} times")
        
        if content != original_content:
            # Write the modified content back to the file with the same encoding
            with open(output_file, 'wb') as f:
                f.write(content.encode(detected_encoding))
            print(f"  Success: Made {replacements_made} replacements in {os.path.basename(output_file)}")
            return True
        else:
            print(f"  No replacements made in {os.path.basename(output_file)}")
            shutil.copy2(input_file, output_file)
            return False
    
    except Exception as e:
        print(f"  Error processing {input_file}: {e}")
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Batch Email Content Replacer")
    parser.add_argument("-c", "--csv", required=True, help="CSV file with replacement data")
    parser.add_argument("-t", "--input", default="input/email", help="Directory with email templates")
    parser.add_argument("-o", "--output", default="output/email", help="Output directory for processed files")
    args = parser.parse_args()
    
    # Process the batch
    batch_process_emails(args.csv, args.input, args.output)

if __name__ == "__main__":
    main()