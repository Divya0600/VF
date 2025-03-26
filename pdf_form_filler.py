"""
PDF Form Filler
Fills PDF forms with provided data using coordinates from JSON configurations.
Supports both interactive input and CSV batch processing.
"""
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import json
import csv
import sys
import argparse
from datetime import datetime

# Default configuration
DEFAULT_CONFIG = {
    "font_size": 12,
    "default_font": "Helvetica",
    "default_letter_spacing": 13
}

def load_form_config(form_type):
    """Load form configuration from JSON file"""
    config_path = os.path.join("forms_config", f"{form_type}.json")
    
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Apply defaults if needed
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def list_available_forms():
    """List all available form configurations"""
    if not os.path.exists("forms_config"):
        print("Forms config directory not found")
        return []
    
    forms = []
    for filename in os.listdir("forms_config"):
        if filename.endswith('.json'):
            forms.append(filename.split('.')[0])
    
    return forms

def convert_coords(orig, page_height):
    """Convert coordinates from top-left to bottom-left origin"""
    new_y0 = page_height - orig["y1"]
    new_y1 = page_height - orig["y0"]
    return new_y0, new_y1

def process_multi_char_field(mapping, field_name, field_value, position_keys, default_spacing):
    """Process a field with multiple character positions"""
    print(f"Processing {field_name} field with value: {field_value}")
    letters_input = list(field_value)
    
    if len(letters_input) > len(position_keys):
        # Calculate average spacing between letters
        deltas = []
        if len(position_keys) > 1:
            for i in range(1, len(position_keys)):
                delta = mapping[position_keys[i]]["x0"] - mapping[position_keys[i-1]]["x0"]
                deltas.append(delta)
            
            # Use average spacing for consistency
            if deltas:
                delta = sum(deltas) / len(deltas)
            else:
                delta = default_spacing
        else:
            delta = default_spacing
        
        # Extend positions for additional letters
        for i in range(len(position_keys), len(letters_input)):
            last_key = position_keys[-1]
            new_x0 = mapping[last_key]["x0"] + delta
            new_x1 = mapping[last_key]["x1"] + delta
            
            new_key = f"auto_{field_name}_{i}"
            mapping[new_key] = {
                "x0": new_x0,
                "y0": mapping[last_key]["y0"],
                "x1": new_x1,
                "y1": mapping[last_key]["y1"],
                "page": mapping[last_key]["page"]
            }
            position_keys.append(new_key)
            
            # Update the last key for next iteration
            last_key = new_key
        
        position_keys = sorted(position_keys, key=lambda k: mapping[k]["x0"])
    
    return position_keys

def get_field_keys(config):
    """Extract field keys based on the form configuration"""
    mapping = config["field_coordinates"]
    field_config = config["field_config"]
    field_keys = {}
    
    # Process fields according to their configuration
    for field_name, field_conf in field_config.items():
        if "y_coord" in field_conf:
            # Character field identified by y-coordinate
            keys = [k for k in mapping if len(k) == 1 and k.isalpha() and 
                    abs(mapping[k]["y0"] - field_conf["y_coord"]) < field_conf["tolerance"]]
            field_keys[field_name] = sorted(keys, key=lambda k: mapping[k]["x0"])
        elif "prefix" in field_conf:
            # Field identified by prefix
            field_keys[field_name] = sorted(
                [k for k in mapping if k.startswith(field_conf["prefix"])],
                key=lambda k: mapping[k]["x0"]
            )
        elif "exact_key" in field_conf:
            # Field with an exact key
            field_keys[field_name] = field_conf["exact_key"]
    
    # Get datum keys based on identifiers
    if "datum_identifiers" in config:
        for datum_field, identifiers in config["datum_identifiers"].items():
            if "exact_key" in identifiers:
                field_keys[datum_field] = identifiers["exact_key"]
            else:
                # Find key based on contains conditions
                for k in mapping:
                    matches = True
                    for condition, value in identifiers.items():
                        if condition == "contains" and value not in k:
                            matches = False
                        elif condition == "not_equals" and k == value:
                            matches = False
                        elif condition == "contains_also" and value not in k:
                            matches = False
                    if matches:
                        field_keys[datum_field] = k
                        break
    
    return field_keys

def setup_font(config):
    """Set up and register fonts"""
    try:
        if "font_path" in config and os.path.exists(config["font_path"]):
            pdfmetrics.registerFont(TTFont('Calibri', config["font_path"]))
            font_to_use = 'Calibri'
            print("Calibri font registered successfully")
        else:
            font_to_use = config["default_font"]
            print(f"Using default font: {font_to_use}")
    except:
        font_to_use = config["default_font"]
        print(f"Could not register Calibri font, using {config['default_font']} instead")
    
    return font_to_use

def fill_pdf_form(form_type, form_data, output_file=None):
    """Fill a PDF form with the provided data"""
    # Load form configuration
    config = load_form_config(form_type)
    if not config:
        return False
    
    try:
        # Setup font
        font_name = setup_font(config)
        
        # Get mapping and field keys
        mapping = config["field_coordinates"]
        field_keys = get_field_keys(config)
        
        # Process multi-character fields
        for field_name in config["field_config"]:
            if field_name in form_data and isinstance(field_keys[field_name], list):
                field_keys[field_name] = process_multi_char_field(
                    mapping, 
                    field_name, 
                    form_data[field_name], 
                    field_keys[field_name],
                    config["default_letter_spacing"]
                )
        
        # Create the overlay
        empty_form = config.get("empty_form_file", "forms/empty_form.pdf")
        temp_overlay = config.get("temp_overlay_file", "temp_overlay.pdf")
        
        # Use custom output file if provided, otherwise use config
        if output_file:
            output_path = output_file
        else:
            output_path = config.get("output_file", "output/filled_form.pdf")
        
        # Check if empty form exists
        if not os.path.exists(empty_form):
            print(f"Empty form file not found: {empty_form}")
            return False
        
        # Open empty form to get dimensions
        reader = PdfReader(empty_form)
        page0 = reader.pages[0]
        width = float(page0.mediabox.width)
        height = float(page0.mediabox.height)
        
        # Create canvas for overlay
        c = canvas.Canvas(temp_overlay, pagesize=(width, height))
        c.setFont(font_name, config["font_size"])
        
        # Draw character fields (name and vorname fields)
        for field_name, keys in field_keys.items():
            if not isinstance(keys, list) or field_name.startswith("datum"):
                continue
                
            # Skip if field is not in form_data
            if field_name not in form_data:
                continue
                
            for idx, key in enumerate(keys):
                if idx >= len(form_data[field_name]):
                    continue
                orig = mapping[key]
                new_y0, _ = convert_coords(orig, height)
                x = orig["x0"]
                c.drawString(x, new_y0, form_data[field_name][idx])
        
        # Draw datum fields
        for field_name in field_keys:
            if not field_name.startswith("datum"):
                continue
                
            # Skip if datum is not in form_data
            if "datum" not in form_data:
                continue
                
            datum_rect = mapping[field_keys[field_name]]
            datum_new_y0, _ = convert_coords(datum_rect, height)
            c.drawString(datum_rect["x0"], datum_new_y0, form_data["datum"])
        
        # Draw special character fields (like 'x' markers)
        for field_name in field_keys:
            if not field_name.startswith("x"):
                continue
                
            x_rect = mapping[field_keys[field_name]]
            x_new_y0, _ = convert_coords(x_rect, height)
            c.drawString(x_rect["x0"], x_new_y0, "x")

        # Save overlay
        c.save()
        
        # Merge overlay with base PDF
        writer = PdfWriter()
        overlay_reader = PdfReader(temp_overlay)
        
        for i in range(len(reader.pages)):
            base_page = reader.pages[i]
            overlay_page = overlay_reader.pages[i]
            base_page.merge_page(overlay_page)
            writer.add_page(base_page)

        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save filled form
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        print(f"PDF saved as {output_path}")
        
        # Clean up temporary files
        if os.path.exists(temp_overlay):
            os.remove(temp_overlay)
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error filling PDF form: {e}")
        return False

def get_form_data():
    """Get form data from user input"""
    form_data = {}
    
    form_data["name1"] = input("Enter first name (bisheriger Vertragspartner): ") or "Fischer"
    form_data["name2"] = input("Enter second name (neuer Vertragspartner): ") or "Divyar"
    form_data["vorname1"] = input("Enter first vorname (bisheriger Vertragspartner): ") or "Lukas"
    form_data["vorname2"] = input("Enter second vorname (neuer Vertragspartner): ") or "Simon"
    form_data["datum"] = input("Enter date (format: DD.MM.YYYY): ") or "20.03.2025"
    
    return form_data

def read_csv_input(csv_file):
    """Read form data from a CSV file"""
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        return []

    form_data_list = []
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                form_data_list.append(row)
        
        if not form_data_list:
            print("No data found in CSV file")
            return []
        
        print(f"Successfully read {len(form_data_list)} records from CSV file")
        return form_data_list
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

def process_batch(form_type, csv_file, output_dir=None):
    """Process multiple forms from a CSV file"""
    # Load form data from CSV
    form_data_list = read_csv_input(csv_file)
    if not form_data_list:
        return False
    
    # Create output directory if specified
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process each row
    success_count = 0
    for i, form_data in enumerate(form_data_list):
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if output_dir:
            output_file = os.path.join(output_dir, f"filled_form_{i+1}_{timestamp}.pdf")
        else:
            output_file = os.path.join("output", f"filled_form_{i+1}_{timestamp}.pdf")
        
        print(f"\nProcessing form {i+1} of {len(form_data_list)}")
        print(f"Data: {form_data}")
        
        # Fill the form
        if fill_pdf_form(form_type, form_data, output_file):
            success_count += 1
    
    print(f"\nBatch processing completed. {success_count} of {len(form_data_list)} forms processed successfully.")
    return success_count > 0

def main():
    """Main function"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="PDF Form Filler")
    parser.add_argument("-c", "--csv", help="Input CSV file for batch processing")
    parser.add_argument("-f", "--form", help="Form type to use")
    parser.add_argument("-o", "--output", help="Output directory for batch processing")
    
    args = parser.parse_args()
    
    # Create required directories if they don't exist
    for directory in ["forms_config", "forms", "output", "data"]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {directory} directory")
    
    # List available forms
    available_forms = list_available_forms()
    
    if not available_forms:
        print("No form configurations found. Please add a JSON configuration file to the forms_config directory.")
        return
    
    # Determine form type
    if args.form and args.form in available_forms:
        selected_form = args.form
    else:
        print("Available form types:")
        for i, form in enumerate(available_forms, 1):
            print(f"  {i}. {form}")
        
        # Get form type from user
        if len(available_forms) == 1:
            selected_form = available_forms[0]
            print(f"Using the only available form type: {selected_form}")
        else:
            try:
                choice = input(f"Select form type (1-{len(available_forms)}): ")
                if not choice:
                    selected_form = available_forms[0]
                    print(f"Using default form type: {selected_form}")
                else:
                    index = int(choice) - 1
                    if 0 <= index < len(available_forms):
                        selected_form = available_forms[index]
                    else:
                        print(f"Invalid selection. Using default form type: {available_forms[0]}")
                        selected_form = available_forms[0]
            except ValueError:
                print(f"Invalid input. Using default form type: {available_forms[0]}")
                selected_form = available_forms[0]
    
    # Batch processing mode if CSV file specified
    if args.csv:
        print(f"\nBatch processing with CSV file: {args.csv}")
        
        # Check if CSV file exists
        if not os.path.exists(args.csv):
            print(f"ERROR: CSV file not found: {args.csv}")
            print("Please check the file path and try again.")
            return
            
        # Try to process the batch
        output_dir = args.output if args.output else "output"
        success = process_batch(selected_form, args.csv, output_dir)
        
        # If batch processing failed, inform the user
        if not success:
            print("Batch processing failed. Check the error messages above for details.")
            print("Make sure your CSV file has the correct format with headers: name1,name2,vorname1,vorname2,datum")
    else:
        # Interactive mode
        print("\nEnter form data (press Enter for default values):")
        form_data = get_form_data()
        
        print("\nFilling form...")
        success = fill_pdf_form(selected_form, form_data)
        
        if success:
            print("\nForm filled successfully!")
        else:
            print("\nError filling form. Check logs for details.")

if __name__ == "__main__":
    main()