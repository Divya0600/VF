import os
import shutil
from pathlib import Path

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
        
        # Make the replacements - keeping it simple
        original_content = content
        replacements_made = 0
        
        for old_text, new_text in replacements.items():
            count = content.count(old_text)
            if count > 0:
                content = content.replace(old_text, new_text)
                replacements_made += count
                print(f"Replaced '{old_text}' with '{new_text}': {count} times")
        
        if content != original_content:
            # Write the modified content back to the file with the same encoding
            with open(output_file, 'wb') as f:
                f.write(content.encode(detected_encoding))
            print(f"Success: Made {replacements_made} replacements in {os.path.basename(input_file)}")
            return True
        else:
            print(f"No replacements made in {os.path.basename(input_file)}")
            shutil.copy2(input_file, output_file)
            return False
    
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False

def main():
    # Define input and output directories
    input_dir = r"C:\Users\divya.eesarla\Desktop\VODAFONE\email\input"
    output_dir = r"C:\Users\divya.eesarla\Desktop\VODAFONE\email\output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the replacement mappings
    replacements = {
        'paul.schneider@example.com': 'divya.eesarla@cgi.com',
        'Paul Schneider': 'Divya Sree',
        '23.10.1982': '01.01.1990',
        '0304494487': '0123456789',
        '432546506': '987654321',
        'Felix Schneider': 'Jane'
    }
    
    # Gather all .eml files in the input directory
    eml_files = [os.path.join(input_dir, file) for file in os.listdir(input_dir) if file.lower().endswith('.eml')]
    
    if not eml_files:
        print(f"No .eml files found in {input_dir}")
        return
    
    print(f"Found {len(eml_files)} .eml files to process")
    
    # Process each .eml file
    success_count = 0
    for eml_file in eml_files:
        output_file = os.path.join(output_dir, os.path.basename(eml_file))
        print(f"\nProcessing: {os.path.basename(eml_file)}")
        
        if replace_in_eml(eml_file, output_file, replacements):
            success_count += 1
    
    print(f"\nProcessing complete: {success_count} of {len(eml_files)} files modified")
    print(f"All output files saved to: {output_dir}")

if __name__ == "__main__":
    main()
