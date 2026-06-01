import os
import json
import pandas as pd
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def save_results(data: List[Dict]):
    """
    Saves the list of company dictionaries to output/companies.xlsx and output/companies.json.
    """
    output_dir = "output"
    if not os.path.exists(output_dir):
        logger.info(f"Creating directory: {output_dir}")
        os.makedirs(output_dir)

    # File paths
    excel_path = os.path.join(output_dir, "companies.xlsx")
    json_path = os.path.join(output_dir, "companies.json")

    try:
        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved data to {json_path}")

        # Save to Excel
        df = pd.DataFrame(data)
        df.to_excel(excel_path, index=False, engine='openpyxl')
        logger.info(f"Successfully saved data to {excel_path}")

    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise
