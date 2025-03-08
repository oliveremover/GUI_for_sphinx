from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import subprocess
import shutil
import json
from itertools import zip_longest

app = Flask(__name__)

SPHINX_DOCS_PATH = "C:\\VsCode Projects\\Medusa\\Docs\\"  # Adjust if needed
CONTENT_PATH = os.path.join(SPHINX_DOCS_PATH, "content")
STARTED_PATH = os.path.join(SPHINX_DOCS_PATH, "gettingstarted")
BUILD_PATH = os.path.join(SPHINX_DOCS_PATH, "_build", "html")
INDEX_RST_PATH = os.path.join(SPHINX_DOCS_PATH, "index.rst")

if not os.path.exists(CONTENT_PATH):
    os.makedirs(CONTENT_PATH)
if not os.path.exists(STARTED_PATH):
    os.makedirs(STARTED_PATH)

def read_toctree_order():
    with open(INDEX_RST_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    toctree_indices = []
    orders = {'content': [], 'gettingstarted': []}
    captions = {'content': [], 'gettingstarted': []}
    classes = {'content': [], 'gettingstarted': []}
    section_for_index = {}  # Map toctree index -> 'content' or 'gettingStarted'

    i = 0
    while i < len(lines):
        line = lines[i]
        if '.. toctree::' in line:
            # Temporarily store the toctree line index
            toctree_index = i
            j = i + 1
            found_section = None

            # Read following lines until next block or similar
            while j < len(lines) and (lines[j].strip().startswith(':') or not lines[j].strip()):
                # If we see the class directive, figure out the correct section
                if ':class:' in lines[j]:
                    if 'toctreeContent' in lines[j]:
                        found_section = 'content'
                    elif 'toctreeGettingstarted' in lines[j]:
                        found_section = 'gettingstarted'
                j += 1

            if found_section:
                toctree_indices.append(toctree_index)
                section_for_index[toctree_index] = found_section
                orders[found_section].append([])
                captions[found_section].append(None)
                classes[found_section].append(None)

            i = j
        else:
            i += 1

    for toctree_index in toctree_indices:
        this_section = section_for_index[toctree_index]
        indent = ' ' * 4
        block_idx = orders[this_section].index([])  # The last appended block for that section
        for i in range(toctree_index + 1, len(lines)):
            if lines[i].startswith(indent):
                orders[this_section][block_idx].append(
                    lines[i].strip().replace('content/', '').replace('gettingstarted/', '')
                )
            elif lines[i].strip() == '' or lines[i].startswith(':'):
                if lines[i].startswith(':caption:'):
                    captions[this_section][block_idx] = lines[i].replace(':caption:', '').strip()
                if lines[i].startswith(':class:'):
                    classes[this_section][block_idx] = lines[i].replace(':class:', '').strip()
                continue
            else:
                break

    print("Found toctree_indices:", toctree_indices)
    return orders, captions, classes

def generate_tree(path, order, class_name):
    tree = []
    items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x))
    items = sorted(items, key=lambda x: order.index(x) if x in order else len(order))
    for item in items:
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            tree.append({
                'text': item,
                'children': generate_tree(item_path, order, class_name)
            })
        else:
            tree.append({
                'text': item,
                'icon': 'jstree-file',
                'a_attr': {'href': url_for('edit', filename=os.path.relpath(item_path, SPHINX_DOCS_PATH).replace("\\", "/"))},
                'li_attr': {'class': f'file-item {class_name}', 'data-filepath': os.path.relpath(item_path, SPHINX_DOCS_PATH).replace("\\", "/")}
            })
    return tree

@app.route('/')
def index():
    orders, captions, classes = read_toctree_order()
    content_tree_data = [generate_tree(CONTENT_PATH, order, class_name)
                         for order, class_name in zip(orders['content'], classes['content'])]
    started_tree_data = [generate_tree(STARTED_PATH, order, class_name)
                         for order, class_name in zip(orders['gettingstarted'], classes['gettingstarted'])]
    content_data = list(zip(content_tree_data, captions['content'], classes['content']))
    started_data = list(zip(started_tree_data, captions['gettingstarted'], classes['gettingstarted']))
    return render_template(
        'index.html',
        content_tree_data=content_tree_data,
        started_tree_data=started_tree_data,
        content_data=content_data,
        started_data=started_data
    )

@app.route('/edit/<path:filename>', methods=['GET', 'POST'])
def edit(filename):
    # Keep the original filename for the form action
    original_filename = filename
    
    # Strip folder prefix from the filename if present
    if filename.startswith('content/'):
        section = 'content'
        filepath = os.path.join(CONTENT_PATH, filename[len('content/'):])
    elif filename.startswith('gettingstarted/'):
        section = 'gettingstarted'
        filepath = os.path.join(STARTED_PATH, filename[len('gettingstarted/'):])
    else:
        # Try to determine section from the path
        if os.path.exists(os.path.join(CONTENT_PATH, filename)):
            section = 'content'
            filepath = os.path.join(CONTENT_PATH, filename)
        elif os.path.exists(os.path.join(STARTED_PATH, filename)):
            section = 'gettingstarted'
            filepath = os.path.join(STARTED_PATH, filename)
        else:
            # Fallback
            section = 'content'
            filepath = os.path.join(CONTENT_PATH, filename)

    if request.method == 'POST':
        content = request.form['content']
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return redirect(url_for('index'))

    file_content = ""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()

    # Pass the original filename (with section prefix) to the template
    return render_template('edit.html', filename=original_filename, content=file_content)

@app.route('/new', methods=['POST'])
def new():
    filename = request.form['filename'].lower()
    folder = request.form['folder'].lower()
    section = request.form['section'].lower()
    if not filename.endswith('.md') and not filename.endswith('.rst'):
        filename += '.md'
    if section == 'content':
        filepath = os.path.join(CONTENT_PATH, folder.strip('/'), filename)
    else:
        filepath = os.path.join(STARTED_PATH, folder.strip('/'), filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Instead of creating an empty file, add a header
    with open(filepath, 'w', encoding='utf-8') as f:
        # Use the filename (without extension) as the header title
        header_title = os.path.splitext(filename)[0].capitalize()
        f.write(f"# {header_title}\n\nEnter your content here.\n")
    
    # Add the new file to the toctree
    relative_path = os.path.relpath(filepath, SPHINX_DOCS_PATH).replace("\\", "/")
    add_to_toctree(relative_path, section)
    
    return redirect(url_for('edit', filename=os.path.relpath(filepath, SPHINX_DOCS_PATH).replace("\\", "/")))

def add_to_toctree(relative_path, section):
    # Map the known sections explicitly
    if section == 'content':
        class_directive = ':class: toctreeContent'
    elif section == 'gettingstarted':
        class_directive = ':class: toctreeGettingstarted'
    else:
        class_directive = ':class: toctreeContent'
    print("Looking for directive:", class_directive)

    # Fix the path - use case-insensitive comparison
    # Plus ensure prefix doesn't get duplicated
    relative_path_lower = relative_path.lower()
    prefix_lower = f"{section.lower()}/"
    if relative_path_lower.startswith(prefix_lower):
        # Remove the prefix keeping the original case of the remaining part
        relative_path = relative_path[len(prefix_lower):]
    
    # Now create the entry with correct section name
    new_entry = f"   {section}/{relative_path}\n"

    with open(INDEX_RST_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find all the toctree blocks
    i = 0
    while i < len(lines):
        if '.. toctree::' in lines[i]:
            start_index = i
            j = i + 1
            found_section = None
            directive_end = j
            
            # Look for the class directive and capture last directive line
            while j < len(lines) and (lines[j].strip().startswith(':') or not lines[j].strip()):
                # Use EXACT match for the class directive
                if lines[j].strip() == class_directive:
                    found_section = section
                    print(f"Found matching directive at line {j}: '{lines[j].strip()}'")
                directive_end = j
                j += 1
            
            if found_section:
                # Found our target section, insert after the last directive
                print(f"Inserting {new_entry.strip()} at line {directive_end + 1}")
                lines.insert(directive_end + 1, new_entry)
                
                with open(INDEX_RST_PATH, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print("Wrote changes to index.rst:", INDEX_RST_PATH)
                return True
            
            i = j  # Skip to after this toctree block
        else:
            i += 1
    
    print("No matching toctree section found for", section)
    return False

def remove_from_toctree(relative_path, section):
    print(f"Removing {relative_path} from {section} toctree")
    
    # Standardize path format for comparison
    if relative_path.startswith(f"{section}/"):
        path_to_find = relative_path
    else:
        path_to_find = f"{section}/{relative_path}"
    
    with open(INDEX_RST_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = False
    new_lines = []
    
    for line in lines:
        # Check for match after removing whitespace
        line_stripped = line.strip()
        if line_stripped == path_to_find:
            found = True
            print(f"Found and removing: {line_stripped}")
            continue
        new_lines.append(line)
    
    if not found:
        print(f"Warning: Could not find {path_to_find} in toctree")
    
    with open(INDEX_RST_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

@app.route('/new_folder', methods=['POST'])
def new_folder():
    foldername = request.form['foldername'].lower()
    parent_folder = request.form['parent_folder'].lower()
    folderpath = os.path.join(CONTENT_PATH, parent_folder.strip('/'), foldername)
    os.makedirs(folderpath, exist_ok=True)
    return redirect(url_for('index'))

@app.route('/delete/<path:filename>', methods=['POST'])
def delete(filename):
    filepath = os.path.join(SPHINX_DOCS_PATH, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        # Remove the file from the toctree
        relative_path = os.path.relpath(filepath, SPHINX_DOCS_PATH).replace("\\", "/")
        section = 'content' if 'content/' in relative_path else 'gettingstarted'
        remove_from_toctree(relative_path, section)
    return redirect(url_for('index'))

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder = request.form['folder'].lower()
    folderpath = os.path.join(CONTENT_PATH, folder.strip('/'))
    if os.path.exists(folderpath):
        shutil.rmtree(folderpath)
    return redirect(url_for('index'))

@app.route('/save_order', methods=['POST'])
def save_order():
    new_order = request.get_json()
    section = request.args.get('section', 'content')  # Get section from query params
    update_toctree(new_order, section)
    return jsonify({'status': 'success'})

def update_toctree(new_order, section):
    # Map the known sections to their class directives
    if section == 'content':
        class_directive = ':class: toctreeContent'
    elif section == 'gettingstarted':
        class_directive = ':class: toctreeGettingstarted'
    else:
        class_directive = ':class: toctreeContent'
    
    with open(INDEX_RST_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the correct toctree blocks by class directive
    toctree_blocks = {}
    i = 0
    while i < len(lines):
        if '.. toctree::' in lines[i]:
            toctree_start = i
            j = i + 1
            found_section = None
            directive_end = j
            
            # Identify which section this toctree belongs to
            while j < len(lines) and (lines[j].strip().startswith(':') or not lines[j].strip()):
                if lines[j].strip() == class_directive:
                    found_section = section
                directive_end = j
                j += 1
            
            # If this is our target section, collect info about this block
            if found_section:
                # Find the end of this toctree (entries are indented)
                entries_start = directive_end + 1
                entries_end = entries_start
                while entries_end < len(lines) and (
                    lines[entries_end].startswith('   ') or 
                    lines[entries_end].strip() == ''
                ):
                    entries_end += 1
                
                # Store the block info
                toctree_blocks[toctree_start] = {
                    'entries_start': entries_start,
                    'entries_end': entries_end
                }
            
            i = j
        else:
            i += 1
    
    # For each toctree block found, update its entries
    for toctree_start, block_info in toctree_blocks.items():
        # Construct the new file list with updated order
        new_entries = []
        for item in new_order:
            # Extract filepath and ensure it has the section prefix
            if 'id' in item and item['id']:
                filepath = item['id']
                
                # First, remove any section prefix that might already be there
                if filepath.startswith(f"{section}/"):
                    actual_file = filepath[len(f"{section}/"):]
                else:
                    actual_file = filepath
                
                # Now create the correctly formatted entry
                new_entries.append(f"   {section}/{actual_file}\n")
        
        # Replace the old entries with the new ones
        new_lines = (
            lines[:block_info['entries_start']] + 
            new_entries + 
            lines[block_info['entries_end']:]
        )
        
        # Write the updated file
        with open(INDEX_RST_PATH, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"Updated order for {section} toctree")
        return  # Only update the first matching toctree block

@app.route('/build')
def build():
    subprocess.run(["sphinx-build", "-b", "html", SPHINX_DOCS_PATH, BUILD_PATH])
    return redirect(url_for('preview'))

@app.route('/preview')
def preview():
    return send_from_directory(BUILD_PATH, "index.html")

if __name__ == '__main__':
    app.run(debug=True)
