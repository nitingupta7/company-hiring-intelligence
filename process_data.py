import json
import html
import re
import os

def process_company(name, file_path):
    with open(file_path, 'r') as f:
        data = f.read()
    
    # Decode HTML entities
    decoded_data = html.unescape(data)
    
    try:
        page_json = json.loads(decoded_data)
        company = page_json.get('props', {}).get('company', {})
        
        # Save prettified JSON
        output_file = f'{name}_full.json'
        with open(output_file, 'w') as f:
            json.dump(company, f, indent=2)
        
        print(f"--- {name.capitalize()} URL Fields ---")
        url_fields = []
        
        def find_urls(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    find_urls(v, f"{prefix}{k}." if prefix else f"{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_urls(item, f"{prefix}[{i}]")
            elif isinstance(obj, str):
                if obj.startswith('http://') or obj.startswith('https://'):
                    field_name = prefix.rstrip('.')
                    print(f"{field_name}: {obj}")
                    url_fields.append((field_name, obj))
        
        find_urls(company)
        print("\n")
        
    except Exception as e:
        print(f"Error processing {name}: {e}")

process_company('stripe', 'stripe_data_page.txt')
process_company('algolia', 'algolia_data_page.txt')
