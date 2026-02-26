#!/usr/bin/env python3
"""
Displacement data parser from CSV files.
Extracts kidney displacement vectors for upper_pole, hilum, lower_pole.
Coordinate system: MEASUREMENT_XYZ (measurement system axes, not DICOM).
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Mapping from CSV column names to our anchor names
THIRD_TO_ANCHOR = {
    "Верхняя треть": "upper_pole",
    "Средняя треть": "hilum",  # Approximation for MVP
    "Нижняя треть": "lower_pole",
}

# Position columns we care about
POSITIONS = ["На спине", "На боку"]


def parse_csv_file(csv_path: Path) -> Dict[str, Dict]:
    """
    Parse displacement CSV file and return structured data.
    
    Returns:
        Dict mapping patient name to displacement data
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    displacement_data = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        # Find header rows (skip empty rows at start)
        header_rows = []
        for row in reader:
            if any(cell.strip() for cell in row):
                header_rows.append(row)
            else:
                continue
            if len(header_rows) >= 6:  # We have enough headers
                break
        
        # Find the column indices we need
        # Row 5 (0-indexed) should contain the actual column headers
        if len(header_rows) < 6:
            raise ValueError("CSV file doesn't have expected header structure")
        
        headers = header_rows[5]
        
        # Find important column indices
        fio_col = None
        position_start_col = None
        
        for i, header in enumerate(headers):
            header = header.strip()
            if header == "ФИО":
                fio_col = i
            elif header == "Ось Х (мм)" and i > 5:  # Make sure we're past the basic columns
                position_start_col = i
                break
        
        if fio_col is None or position_start_col is None:
            raise ValueError("Could not find required columns in CSV")
        
        # Process data rows
        for row in reader:
            if not row or len(row) <= fio_col:
                continue
                
            fio = row[fio_col].strip()
            if not fio or fio.startswith("№") or fio == "ФИО":
                continue
            
            # Extract coordinates for each position and third
            patient_data = {
                "fio": fio,
                "kidneys": {}
            }
            
            # Process right kidney then left kidney
            for kidney_idx, kidney_name in enumerate(["kidney_right", "kidney_left"]):
                # Each kidney has 3 positions (На спине, На боку) with 3 coordinates each
                # Structure: [На спине: X,Y,Z], [На боку: X,Y,Z] for each third
                kidney_data = {}
                
                # For each third (upper, middle, lower)
                for third_idx, (third_name, anchor_name) in enumerate(THIRD_TO_ANCHOR.items()):
                    # Calculate column offset for this third and kidney
                    # Each third has 3 coordinates (X,Y,Z) for each position
                    # Structure: Right kidney coords, then Left kidney coords
                    col_offset = position_start_col + (kidney_idx * 18) + (third_idx * 6)  # 6 cols per third (3 coords * 2 positions)
                    
                    try:
                        # Extract coordinates for both positions
                        back_coords = []
                        side_coords = []
                        
                        # На спине (first position)
                        for axis_idx in range(3):
                            val = row[col_offset + axis_idx].strip()
                            if val:
                                # Replace comma with dot for decimal
                                val = val.replace(',', '.')
                                back_coords.append(float(val))
                            else:
                                back_coords.append(0.0)
                        
                        # На боку (second position) 
                        for axis_idx in range(3):
                            val = row[col_offset + 3 + axis_idx].strip()
                            if val:
                                val = val.replace(',', '.')
                                side_coords.append(float(val))
                            else:
                                side_coords.append(0.0)
                        
                        # Calculate displacement vector
                        displacement = [
                            side_coords[0] - back_coords[0],  # dx
                            side_coords[1] - back_coords[1],  # dy
                            side_coords[2] - back_coords[2],  # dz
                        ]
                        
                        kidney_data[anchor_name] = {
                            "point": back_coords,  # Use back position as anchor point
                            "displacement": displacement,
                        }
                        
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Failed to parse coordinates for {fio}, {kidney_name}, {anchor_name}: {e}")
                        # Skip this anchor if we can't parse it
                        continue
                
                patient_data["kidneys"][kidney_name] = kidney_data
            
            displacement_data[fio] = patient_data
    
    return displacement_data


def get_displacement_for_patient(csv_path: Path, patient_fio: str) -> Optional[Dict]:
    """
    Get displacement data for a specific patient by name.
    
    Args:
        csv_path: Path to CSV file
        patient_fio: Patient name to search for
        
    Returns:
        Displacement data dict or None if not found
    """
    try:
        data = parse_csv_file(csv_path)
        return data.get(patient_fio)
    except Exception as e:
        logger.error(f"Error parsing displacement CSV: {e}")
        return None


def generate_metadata(displacement_data: Dict, job_id: str) -> Dict:
    """
    Generate metadata.json structure from displacement data.
    
    Args:
        displacement_data: Output from get_displacement_for_patient
        job_id: Job ID for this processing
        
    Returns:
        Metadata dict ready for JSON serialization
    """
    if not displacement_data:
        return {
            "job_id": job_id,
            "generated_at": "",
            "error": "No displacement data available",
            "organs": {}
        }
    
    from datetime import datetime
    import json
    
    metadata = {
        "job_id": job_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "units": "mm",
        "coordinate_system": "MEASUREMENT_XYZ",
        "axis_meaning": {
            "x": "measurement_x",
            "y": "measurement_y", 
            "z": "measurement_z"
        },
        "coordinate_system_note": "Axes are from external measurement methodology; not aligned to DICOM",
        "organs": {}
    }
    
    # Convert kidney data to expected format
    for kidney_name, kidney_data in displacement_data.get("kidneys", {}).items():
        organ_data = {
            "anchors": {}
        }
        
        for anchor_name, anchor_data in kidney_data.items():
            organ_data["anchors"][anchor_name] = {
                "point": anchor_data.get("point", [0, 0, 0]),
                "displacement": anchor_data.get("displacement", [0, 0, 0])
            }
        
        metadata["organs"][kidney_name] = organ_data
    
    return metadata


def find_csv_files(base_dir: Path) -> List[Path]:
    """
    Find all CSV displacement files in the given directory.
    
    Args:
        base_dir: Base directory to search
        
    Returns:
        List of CSV file paths
    """
    csv_files = []
    for pattern in ["*Смещение почек*.csv", "*смещение почек*.csv"]:
        csv_files.extend(base_dir.glob(pattern))
    
    return sorted(csv_files)


if __name__ == "__main__":
    # Test parsing
    base_dir = Path(__file__).parent.parent.parent
    csv_files = find_csv_files(base_dir)
    
    for csv_file in csv_files:
        print(f"\n=== Parsing {csv_file} ===")
        try:
            data = parse_csv_file(csv_file)
            print(f"Found {len(data)} patients")
            
            # Show first patient as example
            if data:
                first_patient = list(data.keys())[0]
                print(f"\nExample data for {first_patient}:")
                print(json.dumps(data[first_patient], indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")
