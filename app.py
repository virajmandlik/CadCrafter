from flask import Flask, render_template, request, send_file
import os
import tempfile
import math
import ezdxf  # Library for DWG/DXF file generation
from ezdxf.math import Vec2
import random

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_floorplan():
    # Get basic input parameters from form
    width = float(request.form.get('width', 10.0))
    length = float(request.form.get('length', 10.0))
    wall_thickness = float(request.form.get('wall_thickness', 0.15))
    rooms = int(request.form.get('rooms', 1))
    
    # Create temporary file for DWG
    temp_dir = tempfile.gettempdir()
    dwg_file = os.path.join(temp_dir, 'floorplan.dxf')
    
    # Generate floor plan using ezdxf
    doc = ezdxf.new('R2010')  # AutoCAD 2010 format
    
    # Setup layers with different colors
    doc.layers.new(name='WALLS', dxfattribs={'color': 5})  # Blue (5)
    doc.layers.new(name='DOORS', dxfattribs={'color': 1})  # Red (1)
    doc.layers.new(name='WINDOWS', dxfattribs={'color': 3})  # Green (3)
    doc.layers.new(name='FIXTURES', dxfattribs={'color': 4})  # Cyan (4)
    doc.layers.new(name='DIMENSIONS', dxfattribs={'color': 7})  # White (7)
    doc.layers.new(name='TEXT', dxfattribs={'color': 2})  # Yellow (2)
    doc.layers.new(name='WALL_THICKNESS', dxfattribs={'color': 6})  # Magenta (6)
    
    msp = doc.modelspace()
    
    # Collect room configurations
    room_configs = []
    for i in range(1, rooms + 1):
        room_name = request.form.get(f'room_name_{i}', f'Room {i}')
        room_doors = int(request.form.get(f'room_doors_{i}', 1))
        door_width = float(request.form.get(f'door_width_{i}', 0.9))
        room_windows = int(request.form.get(f'room_windows_{i}', 1))
        window_width = float(request.form.get(f'window_width_{i}', 1.2))
        
        room_configs.append({
            'name': room_name,
            'doors': room_doors,
            'door_width': door_width,
            'windows': room_windows,
            'window_width': window_width,
        })
    
    # Calculate room layout
    if rooms == 1:
        # Simple single room
        room_layout = [
            {
                'x': 0,
                'y': 0,
                'width': width,
                'length': length,
                'config': room_configs[0]
            }
        ]
    elif rooms <= 3:
        # Horizontal layout for 2-3 rooms
        rooms_processed = []
        current_y = 0
        for i in range(rooms):
            room_length = length / rooms
            room = {
                'x': 0,
                'y': current_y,
                'width': width,
                'length': room_length,
                'config': room_configs[i]
            }
            rooms_processed.append(room)
            current_y += room_length
        room_layout = rooms_processed
    else:
        # Grid layout for more rooms
        rows = math.ceil(math.sqrt(rooms))
        cols = math.ceil(rooms / rows)
        
        room_width = width / cols
        room_length = length / rows
        
        rooms_processed = []
        for row in range(rows):
            for col in range(cols):
                room_index = row * cols + col
                if room_index < rooms:  # Don't create more rooms than requested
                    room = {
                        'x': col * room_width,
                        'y': row * room_length,
                        'width': room_width,
                        'length': room_length,
                        'config': room_configs[room_index]
                    }
                    rooms_processed.append(room)
        room_layout = rooms_processed
    
    # Draw outer walls with specified thickness (use double lines to represent thickness)
    # Outer boundary
    outer_boundary = [
        (0, 0),
        (width, 0),
        (width, length),
        (0, length),
        (0, 0)
    ]
    msp.add_lwpolyline(outer_boundary, dxfattribs={'layer': 'WALLS', 'lineweight': 35})
    
    # Inner boundary (to represent wall thickness)
    inner_boundary = [
        (wall_thickness, wall_thickness),
        (width - wall_thickness, wall_thickness),
        (width - wall_thickness, length - wall_thickness),
        (wall_thickness, length - wall_thickness),
        (wall_thickness, wall_thickness)
    ]
    msp.add_lwpolyline(inner_boundary, dxfattribs={'layer': 'WALLS', 'lineweight': 35})
    
    # Add wall fill patterns with hatch lines
    for i in range(len(outer_boundary) - 1):
        x1, y1 = outer_boundary[i]
        x2, y2 = outer_boundary[i + 1]
        x3, y3 = inner_boundary[i]
        x4, y4 = inner_boundary[i + 1]
        
        # Skip if this is just closing the loop
        if i == len(outer_boundary) - 1:
            continue
            
        # Create wall thickness polyline
        wall_points = [(x1, y1), (x2, y2), (x4, y4), (x3, y3), (x1, y1)]
        msp.add_lwpolyline(wall_points, dxfattribs={'layer': 'WALL_THICKNESS', 'lineweight': 15})
    
    # Add overall building dimensions
    # Horizontal dimension at the top
    msp.add_linear_dim(
        base=(0, length + 0.5), 
        p1=(0, length), 
        p2=(width, length), 
        dimstyle='STANDARD', 
        override={'dimtxt': 0.25}, 
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    
    # Vertical dimension at the right
    msp.add_linear_dim(
        base=(width + 0.5, 0), 
        p1=(width, 0), 
        p2=(width, length), 
        dimstyle='STANDARD', 
        angle=90, 
        override={'dimtxt': 0.25}, 
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    
    # Add wall thickness dimension
    wall_dim_text = f"Wall Thickness: {wall_thickness}m"
    wall_text = msp.add_text(wall_dim_text, dxfattribs={'layer': 'TEXT', 'height': 0.2})
    wall_text.set_pos((width/2, length + 0.9), align='MIDDLE_CENTER')
    
    # Create a small wall thickness indicator
    msp.add_line(
        (width/2 - 0.5, length + 0.7),
        (width/2 + 0.5, length + 0.7),
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    msp.add_line(
        (width/2 - 0.5 + wall_thickness, length + 0.7 - wall_thickness),
        (width/2 + 0.5 - wall_thickness, length + 0.7 - wall_thickness),
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    msp.add_line(
        (width/2 - 0.5, length + 0.7),
        (width/2 - 0.5 + wall_thickness, length + 0.7 - wall_thickness),
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    msp.add_line(
        (width/2 + 0.5, length + 0.7),
        (width/2 + 0.5 - wall_thickness, length + 0.7 - wall_thickness),
        dxfattribs={'layer': 'DIMENSIONS'}
    )
    
    for i, room in enumerate(room_layout):
        # Add room name text
        text_x = room['x'] + room['width'] / 2
        text_y = room['y'] + room['length'] / 2
        room_text = msp.add_text(room['config']['name'], dxfattribs={'layer': 'TEXT', 'height': min(room['width'], room['length']) / 10})
        room_text.set_pos((text_x, text_y), align='MIDDLE_CENTER')
        
        # Add room dimensions
        # Width dimension
        msp.add_linear_dim(
            base=(room['x'], room['y'] - 0.3), 
            p1=(room['x'], room['y']), 
            p2=(room['x'] + room['width'], room['y']), 
            dimstyle='STANDARD', 
            override={'dimtxt': 0.15}, 
            dxfattribs={'layer': 'DIMENSIONS'}
        )
        
        # Length dimension
        msp.add_linear_dim(
            base=(room['x'] - 0.3, room['y']), 
            p1=(room['x'], room['y']), 
            p2=(room['x'], room['y'] + room['length']), 
            dimstyle='STANDARD', 
            angle=90,
            override={'dimtxt': 0.15}, 
            dxfattribs={'layer': 'DIMENSIONS'}
        )
        
        # Add room area text
        area = room['width'] * room['length']
        area_text = f"Area: {area:.2f}m²"
        area_label = msp.add_text(area_text, dxfattribs={'layer': 'TEXT', 'height': min(room['width'], room['length']) / 15})
        area_label.set_pos((text_x, text_y - min(room['width'], room['length']) / 7), align='MIDDLE_CENTER')
    
    # Process each room to add walls, doors, and windows
    for i, room in enumerate(room_layout):
        x, y = room['x'], room['y']
        w, l = room['width'], room['length']
        config = room['config']
        
        # Add interior walls for the room if it's not the outer boundary
        if rooms > 1:
            # Draw room walls based on position with double lines to show thickness
            if x > 0:  # Not leftmost room, draw left wall
                # Outer line
                msp.add_line((x, y), (x, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                # Inner line
                msp.add_line((x + wall_thickness, y + wall_thickness), 
                             (x + wall_thickness, y + l - wall_thickness), 
                             dxfattribs={'layer': 'WALLS', 'lineweight': 35})
            
            if y > 0:  # Not topmost room, draw top wall
                # Outer line
                msp.add_line((x, y), (x + w, y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                # Inner line
                msp.add_line((x + wall_thickness, y + wall_thickness), 
                             (x + w - wall_thickness, y + wall_thickness), 
                             dxfattribs={'layer': 'WALLS', 'lineweight': 35})
            
            if x + w < width:  # Not rightmost room, draw right wall
                # Outer line
                msp.add_line((x + w, y), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                # Inner line
                msp.add_line((x + w - wall_thickness, y + wall_thickness), 
                             (x + w - wall_thickness, y + l - wall_thickness), 
                             dxfattribs={'layer': 'WALLS', 'lineweight': 35})
            
            if y + l < length:  # Not bottommost room, draw bottom wall
                # Outer line
                msp.add_line((x, y + l), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                # Inner line
                msp.add_line((x + wall_thickness, y + l - wall_thickness), 
                             (x + w - wall_thickness, y + l - wall_thickness), 
                             dxfattribs={'layer': 'WALLS', 'lineweight': 35})
        
        # Add doors with improved representation
        door_positions = []
        door_width = config['door_width']
        
        # Get available walls for this room
        walls = []
        if x > 0:  # has left wall
            walls.append('left')
        if y > 0:  # has top wall
            walls.append('top')
        if x + w < width or x + w >= width - 0.01:  # has right wall
            walls.append('right')
        if y + l < length or y + l >= length - 0.01:  # has bottom wall
            walls.append('bottom')
        
        # Add requested number of doors
        for d in range(min(config['doors'], len(walls))):
            wall = walls[d % len(walls)]
            
            if wall == 'left':
                door_x = x
                door_y = y + l/2 - door_width/2 + random.uniform(-l/4, l/4)
                # Create door opening (no wall in door location)
                # Draw wall segments around the door
                if door_y > y:
                    msp.add_line((x, y), (x, door_y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if door_y + door_width < y + l:
                    msp.add_line((x, door_y + door_width), (x, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Add door arc symbol
                center = (x - door_width/4, door_y + door_width/2)
                radius = door_width/2
                start_angle = 270
                end_angle = 90
                msp.add_arc(center=center, radius=radius, start_angle=start_angle, 
                            end_angle=end_angle, dxfattribs={'layer': 'DOORS', 'lineweight': 30})
                
                # Add door line
                door_line_x = x - door_width/4 + radius * math.cos(math.radians(270))
                door_line_y = door_y + door_width/2 + radius * math.sin(math.radians(270))
                msp.add_line(
                    (door_line_x, door_line_y), 
                    (x, door_y + door_width/2), 
                    dxfattribs={'layer': 'DOORS', 'lineweight': 30}
                )
                
                # Add door dimension
                if door_y + door_width + 0.5 < y + l:
                    msp.add_linear_dim(
                        base=(x - 0.3, door_y), 
                        p1=(x, door_y), 
                        p2=(x, door_y + door_width), 
                        dimstyle='STANDARD', 
                        angle=90,
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add door label
                    door_label = f"D{i+1}-{d+1}"
                    label = msp.add_text(door_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((x - 0.2, door_y + door_width/2), align='BOTTOM_CENTER')
            
            elif wall == 'top':
                door_x = x + w/2 - door_width/2 + random.uniform(-w/4, w/4)
                door_y = y
                # Create door opening (no wall in door location)
                # Draw wall segments around the door
                if door_x > x:
                    msp.add_line((x, y), (door_x, y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if door_x + door_width < x + w:
                    msp.add_line((door_x + door_width, y), (x + w, y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Add door arc symbol
                center = (door_x + door_width/2, y - door_width/4)
                radius = door_width/2
                start_angle = 0
                end_angle = 180
                msp.add_arc(center=center, radius=radius, start_angle=start_angle, 
                            end_angle=end_angle, dxfattribs={'layer': 'DOORS', 'lineweight': 30})
                
                # Add door line
                door_line_x = door_x + door_width/2 + radius * math.cos(math.radians(0))
                door_line_y = y - door_width/4 + radius * math.sin(math.radians(0))
                msp.add_line(
                    (door_line_x, door_line_y), 
                    (door_x + door_width/2, y), 
                    dxfattribs={'layer': 'DOORS', 'lineweight': 30}
                )
                
                # Add door dimension
                if door_x - 0.5 > x:
                    msp.add_linear_dim(
                        base=(door_x, y - 0.3), 
                        p1=(door_x, y), 
                        p2=(door_x + door_width, y), 
                        dimstyle='STANDARD', 
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add door label
                    door_label = f"D{i+1}-{d+1}"
                    label = msp.add_text(door_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((door_x + door_width/2, y - 0.2), align='BOTTOM_CENTER')
            
            elif wall == 'right':
                door_x = x + w
                door_y = y + l/2 - door_width/2 + random.uniform(-l/4, l/4)
                # Create door opening (no wall in door location)
                # Draw wall segments around the door
                if door_y > y:
                    msp.add_line((x + w, y), (x + w, door_y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if door_y + door_width < y + l:
                    msp.add_line((x + w, door_y + door_width), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Add door arc symbol
                center = (x + w + door_width/4, door_y + door_width/2)
                radius = door_width/2
                start_angle = 90
                end_angle = 270
                msp.add_arc(center=center, radius=radius, start_angle=start_angle, 
                            end_angle=end_angle, dxfattribs={'layer': 'DOORS', 'lineweight': 30})
                
                # Add door line
                door_line_x = x + w + door_width/4 + radius * math.cos(math.radians(90))
                door_line_y = door_y + door_width/2 + radius * math.sin(math.radians(90))
                msp.add_line(
                    (door_line_x, door_line_y), 
                    (x + w, door_y + door_width/2), 
                    dxfattribs={'layer': 'DOORS', 'lineweight': 30}
                )
                
                # Add door dimension
                if door_y + door_width + 0.5 < y + l:
                    msp.add_linear_dim(
                        base=(x + w + 0.3, door_y), 
                        p1=(x + w, door_y), 
                        p2=(x + w, door_y + door_width), 
                        dimstyle='STANDARD', 
                        angle=90,
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add door label
                    door_label = f"D{i+1}-{d+1}"
                    label = msp.add_text(door_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((x + w + 0.2, door_y + door_width/2), align='LEFT')
            
            elif wall == 'bottom':
                door_x = x + w/2 - door_width/2 + random.uniform(-w/4, w/4)
                door_y = y + l
                # Create door opening (no wall in door location)
                # Draw wall segments around the door
                if door_x > x:
                    msp.add_line((x, y + l), (door_x, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if door_x + door_width < x + w:
                    msp.add_line((door_x + door_width, y + l), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Add door arc symbol
                center = (door_x + door_width/2, y + l + door_width/4)
                radius = door_width/2
                start_angle = 180
                end_angle = 0
                msp.add_arc(center=center, radius=radius, start_angle=start_angle, 
                            end_angle=end_angle, dxfattribs={'layer': 'DOORS', 'lineweight': 30})
                
                # Add door line
                door_line_x = door_x + door_width/2 + radius * math.cos(math.radians(180))
                door_line_y = y + l + door_width/4 + radius * math.sin(math.radians(180))
                msp.add_line(
                    (door_line_x, door_line_y), 
                    (door_x + door_width/2, y + l), 
                    dxfattribs={'layer': 'DOORS', 'lineweight': 30}
                )
                
                # Add door dimension
                if door_x - 0.5 > x:
                    msp.add_linear_dim(
                        base=(door_x, y + l + 0.3), 
                        p1=(door_x, y + l), 
                        p2=(door_x + door_width, y + l), 
                        dimstyle='STANDARD', 
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add door label
                    door_label = f"D{i+1}-{d+1}"
                    label = msp.add_text(door_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((door_x + door_width/2, y + l + 0.2), align='TOP_CENTER')
        
        # Add Windows with improved representation
        window_positions = []
        window_width = config['window_width']
        
        # Get exterior walls for this room (walls that are part of the outer boundary)
        exterior_walls = []
        if x <= 0.01:  # left exterior wall
            exterior_walls.append('left')
        if y <= 0.01:  # top exterior wall
            exterior_walls.append('top')
        if x + w >= width - 0.01:  # right exterior wall
            exterior_walls.append('right')
        if y + l >= length - 0.01:  # bottom exterior wall
            exterior_walls.append('bottom')
        
        # Add requested number of windows on exterior walls
        for w_idx in range(min(config['windows'], len(exterior_walls))):
            wall = exterior_walls[w_idx % len(exterior_walls)]
            
            if wall == 'left':
                window_x = x
                window_y = y + random.uniform(l*0.2, l*0.8) - window_width/2
                
                # Create window opening (break in wall)
                if window_y > y:
                    msp.add_line((x, y), (x, window_y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if window_y + window_width < y + l:
                    msp.add_line((x, window_y + window_width), (x, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Inner wall line should also have a break
                if window_y > y + wall_thickness:
                    msp.add_line(
                        (x + wall_thickness, y + wall_thickness), 
                        (x + wall_thickness, window_y), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                if window_y + window_width < y + l - wall_thickness:
                    msp.add_line(
                        (x + wall_thickness, window_y + window_width), 
                        (x + wall_thickness, y + l - wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                
                # Window frame
                msp.add_line(
                    (x, window_y), 
                    (x + wall_thickness, window_y), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                msp.add_line(
                    (x, window_y + window_width), 
                    (x + wall_thickness, window_y + window_width), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                
                # Window glass (center line)
                window_center_y = window_y + window_width/2
                msp.add_line(
                    (x, window_center_y), 
                    (x + wall_thickness, window_center_y), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 15}
                )
                
                # Add window dimension
                if window_y + window_width + 0.5 < y + l:
                    msp.add_linear_dim(
                        base=(x - 0.3, window_y), 
                        p1=(x, window_y), 
                        p2=(x, window_y + window_width), 
                        dimstyle='STANDARD', 
                        angle=90,
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add window label
                    window_label = f"W{i+1}-{w_idx+1}"
                    label = msp.add_text(window_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((x - 0.4, window_y + window_width/2), align='RIGHT')
            
            elif wall == 'top':
                window_x = x + random.uniform(room['width']*0.2, room['width']*0.8) - window_width/2
                window_y = y
                
                # Create window opening (break in wall)
                if window_x > x:
                    msp.add_line((x, y), (window_x, y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if window_x + window_width < x + w:
                    msp.add_line((window_x + window_width, y), (x + w, y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Inner wall line should also have a break
                if window_x > x + wall_thickness:
                    msp.add_line(
                        (x + wall_thickness, y + wall_thickness), 
                        (window_x, y + wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                if window_x + window_width < x + w - wall_thickness:
                    msp.add_line(
                        (window_x + window_width, y + wall_thickness), 
                        (x + w - wall_thickness, y + wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                
                # Window frame
                msp.add_line(
                    (window_x, y), 
                    (window_x, y + wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                msp.add_line(
                    (window_x + window_width, y), 
                    (window_x + window_width, y + wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                
                # Window glass (center line)
                window_center_x = window_x + window_width/2
                msp.add_line(
                    (window_center_x, y), 
                    (window_center_x, y + wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 15}
                )
                
                # Add window dimension
                if window_x - 0.5 > x:
                    msp.add_linear_dim(
                        base=(window_x, y - 0.3), 
                        p1=(window_x, y), 
                        p2=(window_x + window_width, y), 
                        dimstyle='STANDARD', 
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add window label
                    window_label = f"W{i+1}-{w_idx+1}"
                    label = msp.add_text(window_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((window_x + window_width/2, y - 0.4), align='BOTTOM_CENTER')
            
            elif wall == 'right':
                window_x = x + room['width']
                window_y = y + random.uniform(l*0.2, l*0.8) - window_width/2
                
                # Create window opening (break in wall)
                if window_y > y:
                    msp.add_line((x + w, y), (x + w, window_y), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if window_y + window_width < y + l:
                    msp.add_line((x + w, window_y + window_width), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Inner wall line should also have a break
                if window_y > y + wall_thickness:
                    msp.add_line(
                        (x + w - wall_thickness, y + wall_thickness), 
                        (x + w - wall_thickness, window_y), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                if window_y + window_width < y + l - wall_thickness:
                    msp.add_line(
                        (x + w - wall_thickness, window_y + window_width), 
                        (x + w - wall_thickness, y + l - wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                
                # Window frame
                msp.add_line(
                    (x + w, window_y), 
                    (x + w - wall_thickness, window_y), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                msp.add_line(
                    (x + w, window_y + window_width), 
                    (x + w - wall_thickness, window_y + window_width), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                
                # Window glass (center line)
                window_center_y = window_y + window_width/2
                msp.add_line(
                    (x + w, window_center_y), 
                    (x + w - wall_thickness, window_center_y), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 15}
                )
                
                # Add window dimension
                if window_y + window_width + 0.5 < y + l:
                    msp.add_linear_dim(
                        base=(x + w + 0.3, window_y), 
                        p1=(x + w, window_y), 
                        p2=(x + w, window_y + window_width), 
                        dimstyle='STANDARD', 
                        angle=90,
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add window label
                    window_label = f"W{i+1}-{w_idx+1}"
                    label = msp.add_text(window_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((x + w + 0.4, window_y + window_width/2), align='LEFT')
            
            elif wall == 'bottom':
                window_x = x + random.uniform(room['width']*0.2, room['width']*0.8) - window_width/2
                window_y = y + l
                
                # Create window opening (break in wall)
                if window_x > x:
                    msp.add_line((x, y + l), (window_x, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                if window_x + window_width < x + w:
                    msp.add_line((window_x + window_width, y + l), (x + w, y + l), dxfattribs={'layer': 'WALLS', 'lineweight': 35})
                
                # Inner wall line should also have a break
                if window_x > x + wall_thickness:
                    msp.add_line(
                        (x + wall_thickness, y + l - wall_thickness), 
                        (window_x, y + l - wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                if window_x + window_width < x + w - wall_thickness:
                    msp.add_line(
                        (window_x + window_width, y + l - wall_thickness), 
                        (x + w - wall_thickness, y + l - wall_thickness), 
                        dxfattribs={'layer': 'WALLS', 'lineweight': 35}
                    )
                
                # Window frame
                msp.add_line(
                    (window_x, y + l), 
                    (window_x, y + l - wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                msp.add_line(
                    (window_x + window_width, y + l), 
                    (window_x + window_width, y + l - wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 25}
                )
                
                # Window glass (center line)
                window_center_x = window_x + window_width/2
                msp.add_line(
                    (window_center_x, y + l), 
                    (window_center_x, y + l - wall_thickness), 
                    dxfattribs={'layer': 'WINDOWS', 'lineweight': 15}
                )
                
                # Add window dimension
                if window_x - 0.5 > x:
                    msp.add_linear_dim(
                        base=(window_x, y + l + 0.3), 
                        p1=(window_x, y + l), 
                        p2=(window_x + window_width, y + l), 
                        dimstyle='STANDARD', 
                        override={'dimtxt': 0.1}, 
                        dxfattribs={'layer': 'DIMENSIONS'}
                    )
                    # Add window label
                    window_label = f"W{i+1}-{w_idx+1}"
                    label = msp.add_text(window_label, dxfattribs={'layer': 'TEXT', 'height': 0.1})
                    label.set_pos((window_x + window_width/2, y + l + 0.4), align='TOP_CENTER')

    # Add dimensions
    # Horizontal dimension
    msp.add_linear_dim(base=(0, -0.5), p1=(0, 0), p2=(width, 0), 
                       dimstyle='STANDARD', override={'dimtxt': 0.2}, 
                       dxfattribs={'layer': 'DIMENSIONS'})
    
    # Vertical dimension
    msp.add_linear_dim(base=(-0.5, 0), p1=(0, 0), p2=(0, length), 
                       dimstyle='STANDARD', angle=90, override={'dimtxt': 0.2}, 
                       dxfattribs={'layer': 'DIMENSIONS'})
    
    # Add some fixtures for common rooms
    for room in room_layout:
        x, y = room['x'], room['y']
        w, l = room['width'], room['length']
        name = room['config']['name'].lower()
        
        # Add fixtures based on room name
        if 'bathroom' in name or 'bath' in name or 'wc' in name or 'toilet' in name:
            # Add toilet, sink and bathtub
            toilet_x, toilet_y = x + w * 0.75, y + l * 0.3
            sink_x, sink_y = x + w * 0.25, y + l * 0.3
            tub_x, tub_y = x + w * 0.5, y + l * 0.7
            
            # Toilet (rectangle with rounded top)
            toilet_width, toilet_length = 0.4, 0.6
            msp.add_lwpolyline([
                (toilet_x - toilet_width/2, toilet_y - toilet_length/2),
                (toilet_x + toilet_width/2, toilet_y - toilet_length/2),
                (toilet_x + toilet_width/2, toilet_y + toilet_length/2),
                (toilet_x - toilet_width/2, toilet_y + toilet_length/2),
                (toilet_x - toilet_width/2, toilet_y - toilet_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add text label
            toilet_label = msp.add_text("WC", dxfattribs={'layer': 'TEXT', 'height': 0.2})
            toilet_label.set_pos((toilet_x, toilet_y), align='MIDDLE_CENTER')
            
            # Sink (circle)
            msp.add_circle((sink_x, sink_y), 0.3, dxfattribs={'layer': 'FIXTURES'})
            
            # Add text label
            sink_label = msp.add_text("SINK", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            sink_label.set_pos((sink_x, sink_y), align='MIDDLE_CENTER')
            
            # Bathtub (rectangle)
            tub_width, tub_length = min(w * 0.7, 1.8), min(l * 0.3, 0.8)
            msp.add_lwpolyline([
                (tub_x - tub_width/2, tub_y - tub_length/2),
                (tub_x + tub_width/2, tub_y - tub_length/2),
                (tub_x + tub_width/2, tub_y + tub_length/2),
                (tub_x - tub_width/2, tub_y + tub_length/2),
                (tub_x - tub_width/2, tub_y - tub_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add text label
            tub_label = msp.add_text("TUB", dxfattribs={'layer': 'TEXT', 'height': 0.2})
            tub_label.set_pos((tub_x, tub_y), align='MIDDLE_CENTER')
            
        elif 'kitchen' in name or 'dining' in name:
            # Add kitchen counter, sink, stove and dining table
            counter_x, counter_y = x + w * 0.8, y + l * 0.5
            counter_width, counter_length = 0.6, w * 0.6
            
            # Kitchen counter (rectangle)
            msp.add_lwpolyline([
                (counter_x - counter_width/2, counter_y - counter_length/2),
                (counter_x + counter_width/2, counter_y - counter_length/2),
                (counter_x + counter_width/2, counter_y + counter_length/2),
                (counter_x - counter_width/2, counter_y + counter_length/2),
                (counter_x - counter_width/2, counter_y - counter_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add counter label
            counter_label = msp.add_text("COUNTER", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            counter_label.set_pos((counter_x, counter_y), align='MIDDLE_CENTER')
            
            # Add sink in counter
            sink_x, sink_y = counter_x - counter_width/4, counter_y
            msp.add_circle((sink_x, sink_y), 0.2, dxfattribs={'layer': 'FIXTURES'})
            
            # Add stove in counter
            stove_x, stove_y = counter_x + counter_width/4, counter_y
            stove_size = 0.3
            msp.add_lwpolyline([
                (stove_x - stove_size, stove_y - stove_size),
                (stove_x + stove_size, stove_y - stove_size),
                (stove_x + stove_size, stove_y + stove_size),
                (stove_x - stove_size, stove_y + stove_size),
                (stove_x - stove_size, stove_y - stove_size)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add smaller circles for burners
            msp.add_circle((stove_x - stove_size/2, stove_y - stove_size/2), 0.05, dxfattribs={'layer': 'FIXTURES'})
            msp.add_circle((stove_x + stove_size/2, stove_y - stove_size/2), 0.05, dxfattribs={'layer': 'FIXTURES'})
            msp.add_circle((stove_x - stove_size/2, stove_y + stove_size/2), 0.05, dxfattribs={'layer': 'FIXTURES'})
            msp.add_circle((stove_x + stove_size/2, stove_y + stove_size/2), 0.05, dxfattribs={'layer': 'FIXTURES'})
            
            # Dining table
            table_x, table_y = x + w * 0.3, y + l * 0.5
            table_width, table_length = min(w * 0.4, 1.2), min(l * 0.4, 1.2)
            
            # Table (rectangle)
            msp.add_lwpolyline([
                (table_x - table_width/2, table_y - table_length/2),
                (table_x + table_width/2, table_y - table_length/2),
                (table_x + table_width/2, table_y + table_length/2),
                (table_x - table_width/2, table_y + table_length/2),
                (table_x - table_width/2, table_y - table_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add table label
            table_label = msp.add_text("TABLE", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            table_label.set_pos((table_x, table_y), align='MIDDLE_CENTER')
            
            # Add chairs (circles)
            chair_positions = [
                (table_x, table_y - table_length/2 - 0.2),  # Bottom
                (table_x, table_y + table_length/2 + 0.2),  # Top
                (table_x - table_width/2 - 0.2, table_y),   # Left
                (table_x + table_width/2 + 0.2, table_y)    # Right
            ]
            for pos in chair_positions:
                msp.add_circle(pos, 0.2, dxfattribs={'layer': 'FIXTURES'})
            
        elif 'bedroom' in name or 'bed' in name:
            # Add bed, nightstand, and wardrobe
            bed_x, bed_y = x + w * 0.6, y + l * 0.5
            bed_width, bed_length = min(w * 0.7, 1.8), min(l * 0.5, 2.0)
            
            # Bed (rectangle)
            msp.add_lwpolyline([
                (bed_x - bed_width/2, bed_y - bed_length/2),
                (bed_x + bed_width/2, bed_y - bed_length/2),
                (bed_x + bed_width/2, bed_y + bed_length/2),
                (bed_x - bed_width/2, bed_y + bed_length/2),
                (bed_x - bed_width/2, bed_y - bed_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add bed label
            bed_label = msp.add_text("BED", dxfattribs={'layer': 'TEXT', 'height': 0.25})
            bed_label.set_pos((bed_x, bed_y), align='MIDDLE_CENTER')
            
            # Add pillow
            pillow_x, pillow_y = bed_x, bed_y - bed_length/2 + 0.3
            pillow_width, pillow_length = bed_width * 0.8, 0.4
            msp.add_lwpolyline([
                (pillow_x - pillow_width/2, pillow_y - pillow_length/2),
                (pillow_x + pillow_width/2, pillow_y - pillow_length/2),
                (pillow_x + pillow_width/2, pillow_y + pillow_length/2),
                (pillow_x - pillow_width/2, pillow_y + pillow_length/2),
                (pillow_x - pillow_width/2, pillow_y - pillow_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add nightstand
            nightstand_x, nightstand_y = bed_x - bed_width/2 - 0.3, bed_y - bed_length/2 + 0.3
            nightstand_size = 0.4
            msp.add_lwpolyline([
                (nightstand_x - nightstand_size/2, nightstand_y - nightstand_size/2),
                (nightstand_x + nightstand_size/2, nightstand_y - nightstand_size/2),
                (nightstand_x + nightstand_size/2, nightstand_y + nightstand_size/2),
                (nightstand_x - nightstand_size/2, nightstand_y + nightstand_size/2),
                (nightstand_x - nightstand_size/2, nightstand_y - nightstand_size/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add wardrobe
            wardrobe_x, wardrobe_y = x + w * 0.2, y + l * 0.2
            wardrobe_width, wardrobe_length = 0.6, 1.5
            msp.add_lwpolyline([
                (wardrobe_x - wardrobe_width/2, wardrobe_y - wardrobe_length/2),
                (wardrobe_x + wardrobe_width/2, wardrobe_y - wardrobe_length/2),
                (wardrobe_x + wardrobe_width/2, wardrobe_y + wardrobe_length/2),
                (wardrobe_x - wardrobe_width/2, wardrobe_y + wardrobe_length/2),
                (wardrobe_x - wardrobe_width/2, wardrobe_y - wardrobe_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add wardrobe label
            wardrobe_label = msp.add_text("WARDROBE", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            wardrobe_label.set_pos((wardrobe_x, wardrobe_y), align='MIDDLE_CENTER')
            
        elif 'living' in name or 'lounge' in name or 'family' in name:
            # Add sofa, coffee table, TV and cabinet
            sofa_x, sofa_y = x + w * 0.3, y + l * 0.8
            sofa_width, sofa_length = min(w * 0.6, 2.5), min(l * 0.25, 1.0)
            
            # Sofa (rectangle with rounded corners)
            msp.add_lwpolyline([
                (sofa_x - sofa_width/2, sofa_y - sofa_length/2),
                (sofa_x + sofa_width/2, sofa_y - sofa_length/2),
                (sofa_x + sofa_width/2, sofa_y + sofa_length/2),
                (sofa_x - sofa_width/2, sofa_y + sofa_length/2),
                (sofa_x - sofa_width/2, sofa_y - sofa_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add sofa label
            sofa_label = msp.add_text("SOFA", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            sofa_label.set_pos((sofa_x, sofa_y), align='MIDDLE_CENTER')
            
            # Coffee table (rectangle)
            table_x, table_y = sofa_x, sofa_y - sofa_length - 0.5
            table_width, table_length = sofa_width * 0.6, 0.6
            msp.add_lwpolyline([
                (table_x - table_width/2, table_y - table_length/2),
                (table_x + table_width/2, table_y - table_length/2),
                (table_x + table_width/2, table_y + table_length/2),
                (table_x - table_width/2, table_y + table_length/2),
                (table_x - table_width/2, table_y - table_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add table label
            table_label = msp.add_text("TABLE", dxfattribs={'layer': 'TEXT', 'height': 0.1})
            table_label.set_pos((table_x, table_y), align='MIDDLE_CENTER')
            
            # TV cabinet
            tv_x, tv_y = x + w * 0.7, y + l * 0.2
            tv_width, tv_length = 1.2, 0.4
            msp.add_lwpolyline([
                (tv_x - tv_width/2, tv_y - tv_length/2),
                (tv_x + tv_width/2, tv_y - tv_length/2),
                (tv_x + tv_width/2, tv_y + tv_length/2),
                (tv_x - tv_width/2, tv_y + tv_length/2),
                (tv_x - tv_width/2, tv_y - tv_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # TV on the cabinet
            tv_screen_width, tv_screen_depth = 0.8, 0.1
            msp.add_lwpolyline([
                (tv_x - tv_screen_width/2, tv_y - tv_length/2 - tv_screen_depth),
                (tv_x + tv_screen_width/2, tv_y - tv_length/2 - tv_screen_depth),
                (tv_x + tv_screen_width/2, tv_y - tv_length/2),
                (tv_x - tv_screen_width/2, tv_y - tv_length/2),
                (tv_x - tv_screen_width/2, tv_y - tv_length/2 - tv_screen_depth)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add TV label
            tv_label = msp.add_text("TV", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            tv_label.set_pos((tv_x, tv_y), align='MIDDLE_CENTER')
            
        elif 'garage' in name:
            # Add car outline and workbench
            car_x, car_y = x + w * 0.5, y + l * 0.5
            car_width, car_length = min(w * 0.8, 2.2), min(l * 0.8, 4.5)
            
            # Car outline (simplified rectangle)
            msp.add_lwpolyline([
                (car_x - car_width/2, car_y - car_length/2),
                (car_x + car_width/2, car_y - car_length/2),
                (car_x + car_width/2, car_y + car_length/2),
                (car_x - car_width/2, car_y + car_length/2),
                (car_x - car_width/2, car_y - car_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add car label
            car_label = msp.add_text("CAR", dxfattribs={'layer': 'TEXT', 'height': 0.3})
            car_label.set_pos((car_x, car_y), align='MIDDLE_CENTER')
            
            # Add workbench along one wall
            bench_x, bench_y = x + w * 0.8, y + l * 0.2
            bench_width, bench_length = 0.6, w * 0.6
            msp.add_lwpolyline([
                (bench_x - bench_width/2, bench_y - bench_length/2),
                (bench_x + bench_width/2, bench_y - bench_length/2),
                (bench_x + bench_width/2, bench_y + bench_length/2),
                (bench_x - bench_width/2, bench_y + bench_length/2),
                (bench_x - bench_width/2, bench_y - bench_length/2)
            ], dxfattribs={'layer': 'FIXTURES'})
            
            # Add workbench label
            bench_label = msp.add_text("WORKBENCH", dxfattribs={'layer': 'TEXT', 'height': 0.15})
            bench_label.set_pos((bench_x, bench_y), align='MIDDLE_CENTER')

    # Add a scale and title at the bottom of the drawing
    title_y = -1.5
    scale_text = msp.add_text('SCALE 1:100', dxfattribs={'layer': 'TEXT', 'height': 0.3})
    scale_text.set_pos((width / 2, title_y), align='MIDDLE_CENTER')
    
    title_text = msp.add_text('FLOOR PLAN', dxfattribs={'layer': 'TEXT', 'height': 0.4})
    title_text.set_pos((width / 2, title_y - 0.8), align='MIDDLE_CENTER')
    
    # Save the drawing
    doc.saveas(dwg_file)
    
    # Return the file to the user
    return send_file(dwg_file, as_attachment=True, download_name='floorplan.dwg')

if __name__ == '__main__':
    app.run(debug=True)
