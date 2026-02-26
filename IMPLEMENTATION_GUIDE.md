# AR Laparoscopy Implementation Guide

This guide covers the complete implementation of the AR Laparoscopy system with displacement metadata from CSV files.

## Overview

The system consists of:
- **Backend**: FastAPI server with DICOM processing, STL generation, and displacement metadata
- **Unity Client**: Upload, visualization, and displacement vector display
- **CSV Integration**: Displacement data from measurement system (not DICOM-aligned)
- **Cleanup**: Automatic TTL-based cleanup (24 hours) + aggressive input cleanup

## Backend Implementation

### 1. New Components

#### Displacement Parser (`app/services/displacement_parser.py`)
- Parses CSV files with kidney displacement data
- Maps "трети" (upper/middle/lower) to anchors (upper_pole/hilum/lower_pole)
- Calculates displacement vectors: `displacement = coord(on_side) - coord(on_back)`
- Generates metadata.json with MEASUREMENT_XYZ coordinate system

#### Metadata API (`app/api/metadata.py`)
- `GET /api/v1/metadata/{job_id}` - Returns displacement metadata
- `POST /api/v1/metadata/{job_id}/link-patient` - Links patient FIO to job
- Automatically generates metadata.json from CSV data

#### Cleanup System
- `cleanup_jobs.py` - TTL cleanup script (24 hours default)
- `laprascope-cleanup.service` - systemd service
- `laprascope-cleanup.timer` - systemd timer (runs every 6 hours)
- `setup_cleanup_timer.sh` - Installation script

### 2. Updated Components

#### Pipeline (`app/services/pipeline.py`)
- Added metadata generation step after STL conversion
- Automatic metadata.json creation with displacement data
- Integration with CSV parser

#### Upload API (`app/api/upload.py`)
- Added optional `patient_fio` parameter
- Links patient to job for displacement metadata generation

#### Main App (`app/main.py`)
- Added metadata router
- Updated endpoint documentation

### 3. Data Flow

```
DICOM Upload → Pipeline:
1. Extract DICOM
2. Segment kidneys (TotalSegmentator)
3. Convert to STL
4. Generate metadata.json (from CSV displacement data)
5. Aggressive cleanup (remove DICOM/NIfTI)
6. Return job completed

Metadata Generation:
1. Check job status for patient_fio
2. Find CSV files with displacement data
3. Parse CSV for patient displacement
4. Generate metadata.json with MEASUREMENT_XYZ
5. Save to job directory
```

### 4. Installation

#### Backend Setup
```bash
# Install dependencies
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Setup cleanup timer (Linux)
chmod +x setup_cleanup_timer.sh
./setup_cleanup_timer.sh

# Start server
python main.py
```

#### CSV Files
Place CSV displacement files in the project root:
- `Смещение почек 15.01 - Лист1.csv`
- `Смещение почек - 2 - Лист1.csv`

The parser automatically finds files matching `*Смещение почек*.csv`.

## Unity Implementation

### 1. New Scripts

#### LaparoscopyAPI.cs
- Handles HTTP communication with backend
- Upload DICOM ZIP files
- Poll job status until completion
- Download STL files and metadata
- Local caching (24 hours TTL)
- Patient linking functionality

#### DisplacementVisualizer.cs
- Loads STL meshes (placeholder implementation)
- Creates anchor points (upper_pole, hilum, lower_pole)
- Visualizes displacement vectors as arrows
- Handles MEASUREMENT_XYZ coordinate system conversion
- Toggle controls for anchors/arrows

#### LaparoscopyUI.cs
- File selection and upload interface
- Job status monitoring
- Progress indication
- Visualization controls
- Error handling

### 2. Data Structures

#### Metadata Format
```json
{
  "job_id": "job_20240226_123456_1234",
  "generated_at": "2024-02-26T12:00:00Z",
  "units": "mm",
  "coordinate_system": "MEASUREMENT_XYZ",
  "axis_meaning": {
    "x": "measurement_x",
    "y": "measurement_y",
    "z": "measurement_z"
  },
  "coordinate_system_note": "Axes are from external measurement methodology; not aligned to DICOM",
  "organs": {
    "kidney_left": {
      "anchors": {
        "upper_pole": {
          "point": [42.7, 12.8, -51.9],
          "displacement": [3.2, -1.7, 6.7]
        },
        "hilum": {
          "point": [66.8, 26.5, -103.4],
          "displacement": [-1.1, 1.7, 19.5]
        },
        "lower_pole": {
          "point": [65.5, 32.7, -149.5],
          "displacement": [19.5, -5.5, 19.4]
        }
      }
    },
    "kidney_right": {
      "anchors": { /* similar structure */ }
    }
  }
}
```

### 3. Unity Setup

#### Required Components
1. Add `LaparoscopyAPI` component to scene
2. Add `DisplacementVisualizer` component to scene
3. Add `LaparoscopyUI` component to scene
4. Configure UI elements in inspector
5. Set API base URL in LaparoscopyAPI component

#### Dependencies
- Newtonsoft.Json for JSON serialization
- Standard Unity components (UI, Mesh, etc.)

## Usage Workflow

### 1. Backend
1. Start the FastAPI server
2. Ensure CSV files are in project root
3. Server automatically finds and parses CSV files

### 2. Unity
1. Select DICOM ZIP file
2. (Optional) Enter patient FIO for displacement data
3. Click Upload
4. Monitor progress (status polling)
5. View displacement visualization:
   - Blue spheres = anchor points
   - Red arrows = displacement vectors
   - Toggle visibility with UI controls

### 3. API Endpoints

#### Upload with Patient
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@dicom.zip" \
  -F "patient_fio=Плешкова"
```

#### Get Metadata
```bash
curl "http://localhost:8000/api/v1/metadata/{job_id}"
```

#### Link Patient Later
```bash
curl -X POST "http://localhost:8000/api/v1/metadata/{job_id}/link-patient" \
  -F "patient_fio=Плешкова"
```

## Coordinate System Notes

### MEASUREMENT_XYZ
- X/Y/Z axes are from external measurement system
- NOT aligned with DICOM LPS/RAS
- Unity visualization uses abstract coordinate space
- Future calibration needed for anatomical alignment

### Displacement Calculation
- `displacement = coord(on_side) - coord(on_back)`
- Vectors represent movement from back to side position
- Magnitude in millimeters

## Cleanup and Storage

### Aggressive Cleanup
- DICOM files deleted immediately after STL generation
- NIfTI files deleted after successful conversion
- Only STL and metadata retained

### TTL Cleanup
- Job directories deleted after 24 hours
- Runs every 6 hours via systemd timer
- Manual cleanup: `python cleanup_jobs.py --ttl 24`

### Unity Caching
- Downloads cached locally for 24 hours
- Automatic cleanup of old cache
- Reduces server load

## Troubleshooting

### Common Issues

#### No Displacement Data
- Check patient FIO spelling matches CSV exactly
- Verify CSV files are in project root
- Check CSV parsing logs in backend

#### Coordinate System Issues
- Displacement vectors may not align anatomically
- Use Unity coordinate system controls to adjust
- Future: implement calibration matrix

#### Memory Issues
- Reduce DICOM slice count in conversion
- Monitor GPU memory usage
- Use CPU fallback if needed

### Debug Commands

#### Backend
```bash
# Test CSV parsing
python -m app.services.displacement_parser

# Check cleanup
python cleanup_jobs.py --list
python cleanup_jobs.py --dry-run

# View logs
tail -f logs/app.log
```

#### Unity
- Use Unity Console for debug messages
- Check API base URL configuration
- Verify internet connectivity for server access

## Future Enhancements

### Post-MVP
1. DICOM coordinate system alignment
2. Calibration matrix for MEASUREMENT_XYZ → DICOM
3. Automatic patient matching (case_key)
4. Real AR integration (ARFoundation)
5. Advanced measurement tools
6. Database persistence (PostgreSQL)

### Performance
1. Parallel processing
2. GPU acceleration
3. Progressive STL loading
4. Compression for network transfer

## Security Notes

- No authentication in current MVP
- CORS enabled for all origins (development only)
- Input validation for file types and sizes
- Path traversal protection in file operations

## Support

For issues:
1. Check backend logs: `logs/app.log`
2. Verify CSV format matches expected structure
3. Test API endpoints with curl
4. Check Unity console for errors
5. Ensure network connectivity to backend server
