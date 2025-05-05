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
import pdfplumber
import re
import logging
from reportlab.lib.colors import white

# Constants
CONFIG_DIR = "forms_config"
FORMS_DIR = "forms"
OUTPUT_DIR = "output"
DATA_DIR = "data"
TEMP_OVERLAY = "temp_overlay.pdf"

# Default configuration
DEFAULT_CONFIG = {
    "font_size": 5,
    "default_letter_spacing": 13
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_path_exists(path, message=None):
    """Check if a path exists and log message if not"""
    if not os.path.exists(path):
        error_msg = message or f"Path not found: {path}"
        logger.error(error_msg)
        return False
    return True

def ensure_dir_exists(directory):
    """Ensure a directory exists, create if it doesn't"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created {directory} directory")
    return True

def load_form_config(form_type):
    """Load form configuration from JSON file"""
    config_path = os.path.join(CONFIG_DIR, f"{form_type}.json")
    
    if not check_path_exists(config_path):
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
        logger.error(f"Error loading configuration: {e}")
        return None

def list_available_forms():
    """List all available form configurations"""
    if not check_path_exists(CONFIG_DIR, "Forms config directory not found"):
        return []
    
    forms = []
    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith('.json'):
            forms.append(filename.split('.')[0])
    
    return forms

def convert_coords(orig, page_height):
    """Convert coordinates from top-left to bottom-left origin"""
    new_y0 = page_height - orig["y1"]
    new_y1 = page_height - orig["y0"]
    return new_y0, new_y1

def extract_text_with_positions(pdf_path):
    """Extract text with positions from PDF"""
    if not check_path_exists(pdf_path):
        return []
        
    text_positions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                for word in words:
                    text_positions.append({
                        'text': word['text'],
                        'x0': word['x0'],
                        'y0': word['top'],
                        'x1': word['x1'],
                        'y1': word['bottom'],
                        'page': i
                    })
        return text_positions
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return []

def find_field_positions(pdf_path, field_names):
    """Find positions of fields in the PDF based on common field labels"""
    text_positions = extract_text_with_positions(pdf_path)
    field_positions = {}
    
    # Common field labels and their associated field names
    field_labels = {
        'name': ['name:', 'nachname:', 'last name:', 'surname:'],
        'vorname': ['vorname:', 'first name:', 'given name:'],
        'strasse': ['straße:', 'street:', 'strasse:'],
        'hausnummer': ['nr:', 'no:', 'number:', 'hausnummer:'],
        'postleitzahl': ['plz:', 'zip:', 'postal code:'],
        'ort': ['ort:', 'city:', 'town:'],
        'geburtsdatum': ['geburtsdatum:', 'birthdate:', 'birth date:', 'date of birth:'],
        'datum': ['datum:', 'date:'],
        'kundennummer': ['kundennummer:', 'customer number:', 'client number:', 'id:']
    }
    
    # Find label positions in the PDF
    for i, pos in enumerate(text_positions):
        text = pos['text'].lower()
        for field, labels in field_labels.items():
            if any(label == text for label in labels) and i < len(text_positions) - 1:
                # The field value is likely to be after the label
                next_pos = text_positions[i+1]
                field_positions[field] = {
                    'x0': next_pos['x0'],
                    'y0': next_pos['y0'],
                    'x1': next_pos['x1'],
                    'y1': next_pos['y1'],
                    'page': next_pos['page']
                }
                logger.info(f"Found position for {field}: {field_positions[field]}")
    
    return field_positions

def find_id_position(text_positions, id_pattern=None):
    """Always return None to force using exact coordinates"""
    return None

def process_multi_char_field(mapping, field_name, field_value, position_keys, default_spacing):
    """Process a field with multiple character positions"""
    logger.info(f"Processing {field_name} field with value: {field_value}")
    letters_input = list(field_value)
    
    # Check if position_keys is empty, create a new position if needed
    if not position_keys:
        logger.info(f"No position keys found for {field_name}, creating default position")
        # Create a default position based on existing mappings
        key_name = f"default_{field_name}"
        
        # Find other fields with valid positions to use as reference
        reference_position = None
        for key, pos in mapping.items():
            if all(coord in pos for coord in ["x0", "y0", "x1", "y1", "page"]):
                reference_position = pos
                break
        
        # Use reference or create generic position
        if reference_position:
            mapping[key_name] = {
                "x0": reference_position["x0"],
                "y0": reference_position["y0"] + 30,  # Offset vertically
                "x1": reference_position["x1"],
                "y1": reference_position["y1"] + 30,
                "page": reference_position["page"]
            }
        else:
            # Fallback to generic position
            mapping[key_name] = {
                "x0": 100.0,
                "y0": 400.0,
                "x1": 110.0,
                "y1": 410.0,
                "page": 0
            }
        position_keys = [key_name]
    
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
            # Get field type from configuration or infer from field name
            field_type = field_conf.get("field_type", "")
            
            # If field type is not specified, try to infer from field name
            if not field_type:
                if any(digit_field in field_name.lower() for digit_field in ["zip", "plz", "postleitzahl", "code"]):
                    field_type = "digit"
                else:
                    field_type = "alpha"
            
            # Select keys based on field type
            if field_type == "digit":
                keys = [k for k in mapping if len(k) == 1 and k.isdigit() and 
                        abs(mapping[k]["y0"] - field_conf["y_coord"]) < field_conf["tolerance"]]
            else:
                # Default to character field
                keys = [k for k in mapping if len(k) == 1 and k.isalpha() and 
                        abs(mapping[k]["y0"] - field_conf["y_coord"]) < field_conf["tolerance"]]
                
            # Sort the keys by x-coordinate (left to right)
            field_keys[field_name] = sorted(keys, key=lambda k: mapping[k]["x0"])
            
            # Log details for debugging
            logger.info(f"Found {len(field_keys[field_name])} positions for {field_name} field")
        elif "prefix" in field_conf:
            # Field identified by prefix
            prefix_keys = [k for k in mapping if k.startswith(field_conf["prefix"])]
            field_keys[field_name] = sorted(prefix_keys, key=lambda k: mapping[k]["x0"])
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
    if "font_path" not in config or not check_path_exists(config["font_path"], 
                                                         f"Font file not found: {config.get('font_path', 'No path specified')}"):
        raise ValueError(f"Font file not found: {config.get('font_path', 'No path specified')}")
        
    try:
        font_file = os.path.basename(config["font_path"])
        font_name = os.path.splitext(font_file)[0]
        pdfmetrics.registerFont(TTFont(font_name, config["font_path"]))
        logger.info(f"{font_name} font registered successfully")
        
        # Try to register bold font if it exists
        bold_font_path = config.get("bold_font_path")
        bold_font_name = None
        
        if bold_font_path and check_path_exists(bold_font_path):
            bold_font_file = os.path.basename(bold_font_path)
            bold_font_name = os.path.splitext(bold_font_file)[0]
            pdfmetrics.registerFont(TTFont(bold_font_name, bold_font_path))
            logger.info(f"{bold_font_name} bold font registered successfully")
        
        return font_name, bold_font_name
    except Exception as e:
        raise ValueError(f"Failed to register font: {e}")

def draw_bold_text(c, x, y, text, font_size):
    """Draw text with simulated bold effect by drawing it multiple times with slight offsets"""
    # Original position
    c.drawString(x, y, text)
    
    # Small offsets to make it appear bold
    offsets = [0.5, 0.5]
    for dx in offsets:
        c.drawString(x + dx, y, text)

def prepare_overlay_canvas(empty_form, temp_overlay, font_name, font_size):
    """Prepare canvas for overlay"""
    # Open empty form to get dimensions
    reader = PdfReader(empty_form)
    page0 = reader.pages[0]
    width = float(page0.mediabox.width)
    height = float(page0.mediabox.height)
    
    # Create canvas for overlay
    c = canvas.Canvas(temp_overlay, pagesize=(width, height))
    c.setFont(font_name, font_size)
    
    return c, reader, width, height

def draw_character_fields(c, mapping, field_keys, form_data, height):
    """Draw character fields like name and vorname"""
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

def draw_datum_fields(c, mapping, field_keys, form_data, height):
    """Draw datum fields"""
    for field_name in field_keys:
        if not field_name.startswith("datum") and field_name != "geburtsdatum":
            continue
            
        # Skip if datum is not in form_data
        if field_name == "geburtsdatum":
            if field_name not in form_data:
                continue
            datum_rect = mapping[field_keys[field_name]]
            datum_new_y0, _ = convert_coords(datum_rect, height)
            c.drawString(datum_rect["x0"], datum_new_y0, form_data[field_name])
        elif field_name in form_data:  # Changed to check if the specific datum field exists
            # Use the actual field name from form_data rather than hardcoded "datum"
            datum_rect = mapping[field_keys[field_name]]
            datum_new_y0, _ = convert_coords(datum_rect, height)
            c.drawString(datum_rect["x0"], datum_new_y0, form_data[field_name])


def draw_checkbox_fields(c, mapping, field_keys, height):
    """Draw checkbox fields (x markers)"""
    for field_name in field_keys:
        if not field_name.startswith("x"):
            continue
            
        x_rect = mapping[field_keys[field_name]]
        x_new_y0, _ = convert_coords(x_rect, height)
        c.drawString(x_rect["x0"], x_new_y0, "x")

def draw_exact_key_fields(c, mapping, field_keys, field_config, form_data, height, id_position, bold_font_name, font_name, font_size):
    """Draw fields with exact keys like hausnummer and ID"""
    for field_name in field_config:
        # Skip if the field is not in form_data
        if field_name not in form_data:
            continue
        
        # Special handling for ID field with exact coordinates
        if field_name == "ID" and "id_field" in mapping:
            # Use exact coordinates from configuration
            rect = mapping["id_field"]
            new_y0, _ = convert_coords(rect, height)
            
            # Draw white rectangle to cover existing ID
            padding = 2
            c.setFillColor(white)
            c.rect(
                rect["x0"] - padding, 
                new_y0 - padding,
                (rect["x1"] - rect["x0"]) + (padding * 2), 
                (rect["y1"] - rect["y0"]) + (padding * 2),
                fill=True, stroke=False
            )
            
            # Reset to black color for text
            c.setFillColorRGB(0, 0, 0)
            
            # Draw ID with bold effect
            if bold_font_name:
                c.setFont(bold_font_name, font_size)
                c.drawString(rect["x0"], new_y0, form_data[field_name])
                # Reset back to normal font
                c.setFont(font_name, font_size)
            else:
                draw_bold_text(c, rect["x0"], new_y0, form_data[field_name], font_size)
            
            continue
            
        # Handle other exact key fields
        if "exact_key" in field_config[field_name] and field_name not in ["geburtsdatum"]:
            exact_key = field_config[field_name]["exact_key"]
            if exact_key in mapping:
                rect = mapping[exact_key]
                new_y0, _ = convert_coords(rect, height)
                c.drawString(rect["x0"], new_y0, form_data[field_name])

def merge_overlay_with_base(temp_overlay, empty_form, output_path):
    """Merge overlay with base PDF"""
    writer = PdfWriter()
    base_reader = PdfReader(empty_form)
    overlay_reader = PdfReader(temp_overlay)
    
    for i in range(len(base_reader.pages)):
        base_page = base_reader.pages[i]
        if i < len(overlay_reader.pages):
            overlay_page = overlay_reader.pages[i]
            base_page.merge_page(overlay_page)
        writer.add_page(base_page)

    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir:
        ensure_dir_exists(output_dir)

    # Save filled form
    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    logger.info(f"PDF saved as {output_path}")
    
    # Clean up temporary files
    if os.path.exists(temp_overlay):
        os.remove(temp_overlay)

def fill_pdf_form(form_type, form_data, output_file=None):
    """Fill a PDF form with the provided data"""
    # Load form configuration
    config = load_form_config(form_type)
    if not config:
        return False
    
    try:
        # Setup font
        font_name, bold_font_name = setup_font(config)
        
        # Define paths
        empty_form = config.get("empty_form_file", os.path.join(FORMS_DIR, "empty_form.pdf"))
        temp_overlay = config.get("temp_overlay_file", TEMP_OVERLAY)
        
        # Use custom output file if provided, otherwise use config
        if output_file:
            output_path = output_file
        else:
            output_path = config.get("output_file", os.path.join(OUTPUT_DIR, "filled_form.pdf"))
        
        # Rest of the function...
        
        # Check if empty form exists
        if not check_path_exists(empty_form, f"Empty form file not found: {empty_form}"):
            return False
        
        # Get mapping and field keys
        mapping = config["field_coordinates"]
        field_keys = get_field_keys(config)
        
        # Try to find missing field positions in the PDF
        missing_fields = [field for field in form_data if field not in field_keys 
                         and not any(field.startswith(p) for p in ["x", "checkbox"])]
        
        if missing_fields:
            logger.info(f"Searching for positions of missing fields: {missing_fields}")
            found_positions = find_field_positions(empty_form, missing_fields)
            
            # Add found positions to mapping
            for field, position in found_positions.items():
                if field in missing_fields:
                    key_name = f"found_{field}"
                    mapping[key_name] = position
                    field_keys[field] = key_name
                    logger.info(f"Added position for {field} from PDF analysis")
        
        # Process multi-character fields
        for field_name in config["field_config"]:
            if field_name in form_data and isinstance(field_keys.get(field_name), list):
                field_keys[field_name] = process_multi_char_field(
                    mapping, 
                    field_name, 
                    form_data[field_name], 
                    field_keys[field_name],
                    config["default_letter_spacing"]
                )
        
        # Extract text and find ID position if needed - ID position will be None due to patched function
        id_position = None
        
        # Prepare canvas
        c, reader, width, height = prepare_overlay_canvas(
            empty_form, temp_overlay, font_name, config["font_size"]
        )
        
        # Draw various field types
        draw_character_fields(c, mapping, field_keys, form_data, height)
        draw_datum_fields(c, mapping, field_keys, form_data, height)
        draw_checkbox_fields(c, mapping, field_keys, height)
        draw_exact_key_fields(
            c, mapping, field_keys, config["field_config"], form_data, 
            height, id_position, bold_font_name, font_name, config["font_size"]
        )
        
        # Save overlay
        c.save()
        
        # Merge overlay with base PDF
        merge_overlay_with_base(temp_overlay, empty_form, output_path)
        
        return True
        
    except Exception as e:
        logger.exception(f"Error filling PDF form: {e}")
        return False


def read_csv_input(csv_file):
    """Read form data from a CSV file"""
    if not check_path_exists(csv_file, f"CSV file not found: {csv_file}"):
        return []

    form_data_list = []
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            form_data_list = list(reader)
        
        if not form_data_list:
            logger.warning("No data found in CSV file")
            return []
        
        logger.info(f"Successfully read {len(form_data_list)} records from CSV file")
        return form_data_list
        
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return []

def process_batch(form_type, csv_file, output_dir=None):
    """Process multiple forms from a CSV file"""
    # Load form data from CSV
    form_data_list = read_csv_input(csv_file)
    if not form_data_list:
        return False
    
    # Create output directory if specified
    if output_dir:
        ensure_dir_exists(output_dir)
    
    # Process each row
    success_count = 0
    for i, form_data in enumerate(form_data_list):
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if output_dir:
            output_file = os.path.join(output_dir, f"filled_form.pdf")
        else:
            output_file = os.path.join(OUTPUT_DIR, f"filled_form_{i+1}_{timestamp}.pdf")
        
        logger.info(f"\nProcessing form {i+1} of {len(form_data_list)}")
        logger.info(f"Data: {form_data}")
        
        # Fill the form
        if fill_pdf_form(form_type, form_data, output_file):
            success_count += 1
    
    logger.info(f"\nBatch processing completed. {success_count} of {len(form_data_list)} forms processed successfully.")
    return success_count > 0

def main():
    """Main function - Non-interactive, requires command line parameters"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="PDF Form Filler")
    parser.add_argument("-c", "--csv", required=True, help="Input CSV file for batch processing")
    parser.add_argument("-f", "--form", required=True, help="Form type to use")
    parser.add_argument("-o", "--output", help="Output directory for batch processing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create required directories
    for directory in [CONFIG_DIR, FORMS_DIR, OUTPUT_DIR, DATA_DIR]:
        ensure_dir_exists(directory)
    
    # Get available form types
    available_forms = list_available_forms()
    
    if not available_forms:
        logger.error("No form configurations found. Please add a JSON configuration file to the forms_config directory.")
        return 1
    
    # Validate form type
    if args.form not in available_forms:
        logger.error(f"Invalid form type: {args.form}")
        logger.error(f"Available form types: {', '.join(available_forms)}")
        return 1
    
    # Validate CSV file
    if not check_path_exists(args.csv, f"CSV file not found: {args.csv}"):
        return 1
    
    # Process the batch
    logger.info(f"Processing with form type: {args.form}, CSV file: {args.csv}")
    output_dir = args.output if args.output else OUTPUT_DIR
    success = process_batch(args.form, args.csv, output_dir)
    
    # Return appropriate exit code
    if not success:
        logger.error("Processing failed. Check the error messages above for details.")
        
        # Extract expected fields from form configuration
        config = load_form_config(args.form)
        if config and "field_config" in config:
            expected_fields = [field for field in config["field_config"] 
                              if not field.startswith("x")]  # Skip checkbox fields
            header = ",".join(expected_fields)
            logger.error(f"Make sure your CSV file has the correct format with headers: {header}")
        
        return 1
    
    logger.info("Processing completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())