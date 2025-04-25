# AutoCAD Floor Plan Generator

A web application that generates professional AutoCAD floor plans and exports them as DWG-compatible files. This tool is designed for architects, civil engineers, and construction professionals who need quick drafts of floor plans.

## Features

- Generate floor plans with customizable dimensions
- Create multiple room layouts automatically
- Export as DWG-compatible files for use in AutoCAD
- Includes doors, windows, and basic fixtures
- Automatic dimensioning
- Professional layer organization

## About DWG Format

The DWG (Drawing) format is a proprietary binary file format used for CAD (Computer-Aided Design) data. It was developed by Autodesk for use with AutoCAD and has become an industry standard for architectural and engineering drawings.

### Technical Details:
- **File Structure**: DWG files contain vector image data, including 2D and 3D design objects
- **Precision**: Supports high precision for accurate representation of real-world measurements
- **Object Types**: Supports lines, arcs, circles, text, dimensions, and complex objects
- **Layering**: Allows organization of elements into layers for better management
- **Metadata**: Can include title blocks, revision history, and other project information

### Common Uses in Civil Engineering:
- Architectural floor plans
- Structural drawings
- Mechanical system layouts
- Electrical schematics
- Plumbing diagrams
- Site plans and topography

## Civil Engineering Drawing Standards

This application follows standard civil engineering drawing practices:
- Wall thickness proportionate to scale
- Standard door and window sizes
- Proper dimensioning techniques
- Layer organization for different element types
- Color coding based on element type

## Setup Instructions (Step by Step)

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the Flask application:
   ```
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

6. Use the form to set dimensions and the number of rooms, then click "Generate DWG File" to download your floor plan.

## Requirements

- Python 3.7 or higher
- Flask 2.0.1
- Werkzeug 2.0.3
- ezdxf 0.17.2 (for DWG/DXF file generation)

## Technical Implementation

The application uses:
- **Flask**: For the web application backend
- **ezdxf**: For creating and manipulating DXF/DWG files
- **HTML/CSS**: For the user interface
- **Python**: Core programming language

## Notes

- The generated file is in DXF format (compatible with AutoCAD)
- The application creates a basic floor plan with walls, doors, windows, and fixtures based on your specifications
- All measurements are in meters
- For advanced editing, open the generated file in AutoCAD or any compatible CAD software "# CadCrafter" 
