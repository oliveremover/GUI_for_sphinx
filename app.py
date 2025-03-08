from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import subprocess
import shutil
import json
from itertools import zip_longest
from werkzeug.utils import secure_filename

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
    
    # Add the new file to the parent folder's toctree
    relative_path = os.path.relpath(filepath, SPHINX_DOCS_PATH).replace("\\", "/")
    add_to_parent_toctree(relative_path, section, folder)
    
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

def add_to_parent_toctree(relative_path, section, parent_folder=''):
    """Add a path to the index.rst in the parent folder if it exists, otherwise to root index.rst."""
    print(f"Adding {relative_path} to parent_folder='{parent_folder}' in section='{section}'")
    
    # If no parent folder specified, use the root index.rst
    if not parent_folder:
        print("No parent_folder specified, using root index.rst")
        return add_to_toctree(relative_path, section)
    
    # Always strip any leading and trailing slashes from parent_folder
    parent_folder = parent_folder.strip('/')
    
    # First try the primary section path
    if section == 'content':
        primary_path = os.path.join(CONTENT_PATH, parent_folder)
        secondary_path = os.path.join(STARTED_PATH, parent_folder)
    else:
        primary_path = os.path.join(STARTED_PATH, parent_folder)
        secondary_path = os.path.join(CONTENT_PATH, parent_folder)
    
    # Try primary path first
    parent_index_path = os.path.join(primary_path, 'index.rst')
    print(f"Looking for parent index at: {parent_index_path}")
    
    # If primary doesn't exist, try secondary path
    if not os.path.exists(parent_index_path):
        parent_index_path = os.path.join(secondary_path, 'index.rst')
        print(f"Primary path not found, trying secondary path: {parent_index_path}")
        
        # If still not found, use root index
        if not os.path.exists(parent_index_path):
            print(f"No index.rst found in any parent folder {parent_folder}, using root index.rst")
            return add_to_toctree(relative_path, section)
        else:
            # Secondary path exists, adjust parent_path for later use
            parent_path = secondary_path
            # Also adjust section based on the working path
            section = 'gettingstarted' if secondary_path.startswith(STARTED_PATH) else 'content'
    else:
        # Primary path exists
        parent_path = primary_path
    
    # Determine parent folder's path and its index.rst
    if section == 'content':
        parent_path = os.path.join(CONTENT_PATH, parent_folder)
    else:
        parent_path = os.path.join(STARTED_PATH, parent_folder)
    
    parent_index_path = os.path.join(parent_path, 'index.rst')
    print(f"Looking for parent index at: {parent_index_path}")
    
    # If parent doesn't have an index.rst, fall back to root index.rst
    if not os.path.exists(parent_index_path):
        print(f"No index.rst found in parent folder {parent_folder}, using root index.rst")
        return add_to_toctree(relative_path, section)
    
    # Calculate relative path from parent folder to target file
    if section == 'content':
        base_path = CONTENT_PATH
    else:
        base_path = STARTED_PATH
        
    # Get the path relative to the parent folder
    file_full_path = os.path.join(SPHINX_DOCS_PATH, relative_path)
    rel_to_parent = os.path.relpath(file_full_path, parent_path).replace('\\', '/')
    
    print(f"Relative path from parent: {rel_to_parent}")
    
    # Add to the parent's index.rst
    with open(parent_index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the toctree directive
    toctree_index = -1
    for i, line in enumerate(lines):
        if '.. toctree::' in line:
            toctree_index = i
            break
    
    if toctree_index == -1:
        # No toctree found, add one
        lines.append('\n.. toctree::\n   :maxdepth: 2\n   :caption: Contents:\n\n')
        lines.append(f'   {rel_to_parent}\n')
    else:
        # Find where to insert (after directives like :maxdepth:, :caption:, etc.)
        insert_index = toctree_index + 1
        while insert_index < len(lines) and (
            lines[insert_index].strip().startswith(':') or not lines[insert_index].strip()
        ):
            insert_index += 1
        
        # Insert our file with the proper relative path
        lines.insert(insert_index, f'   {rel_to_parent}\n')
    
    # Write back to the parent's index.rst
    with open(parent_index_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Added {rel_to_parent} to {parent_index_path}")
    return True

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
    section = request.form.get('section', 'content').lower()
    
    # Set the section specific paths
    if section == 'gettingstarted':
        base_path = STARTED_PATH
        section_index_path = os.path.join(STARTED_PATH, 'index.rst')
    else:  # Default to content
        base_path = CONTENT_PATH
        section_index_path = os.path.join(CONTENT_PATH, 'index.rst')
    
    # If parent_folder is empty but we're creating a folder in a specific section,
    # we should add it to that section's index.rst, not the root index.rst
    if not parent_folder:
        # Create the section's index.rst if it doesn't exist
        if not os.path.exists(section_index_path):
            os.makedirs(os.path.dirname(section_index_path), exist_ok=True)
            with open(section_index_path, 'w', encoding='utf-8') as f:
                title = section.replace('_', ' ').title()
                underline = '=' * len(title)
                f.write(f"""{title}
{underline}

Section index page.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

""")
            
        # Continue with folder creation
        folderpath = os.path.join(base_path, foldername)
    else:
        # Regular case - parent folder specified
        # Determine where to create the new folder
        relative_parent = parent_folder.strip('/')
        if relative_parent.startswith(section + '/'):
            # Remove section prefix for filesystem path
            relative_parent = relative_parent[len(section) + 1:]
            
        folderpath = os.path.join(base_path, relative_parent, foldername)
    
    # Create the folder
    os.makedirs(folderpath, exist_ok=True)
    
    # Create _static folder inside the new folder
    static_folder = os.path.join(folderpath, "_static")
    os.makedirs(static_folder, exist_ok=True)
    print(f"Created _static folder at: {static_folder}")
    
    # Create index.rst file in the new folder
    index_path = os.path.join(folderpath, "index.rst")
    with open(index_path, 'w', encoding='utf-8') as f:
        title = foldername.replace('_', ' ').title()
        underline = '=' * len(title)
        f.write(f"""{title}
{underline}

This is the main page for {title}.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

""")
    
    # Add the new index.rst to the parent's toctree
    relative_path = os.path.relpath(index_path, SPHINX_DOCS_PATH).replace("\\", "/")
    
    if not parent_folder:
        # For top-level folders without a parent, add to section's index.rst
        parent_folder = section  # Use section name as parent folder
    
    # Use the adjusted parent_folder parameter
    add_to_parent_toctree(relative_path, section, parent_folder)
    
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
    folder = request.form['folder']  # Don't lowercase here to preserve case
    section = request.form.get('section', 'content').lower()
    
    print(f"Attempting to delete folder: {folder} in section: {section}")
    
    # Auto-detect the section from the folder path if needed
    if folder.lower().startswith('gettingstarted/') or folder.lower().startswith('gettingStarted/'):
        section = 'gettingstarted'
        print(f"Section auto-detected as '{section}' from folder path")
    elif folder.lower().startswith('content/'):
        section = 'content'
        print(f"Section auto-detected as '{section}' from folder path")
    
    # Determine the correct base path
    if section == 'gettingstarted':
        base_path = STARTED_PATH
    else:
        base_path = CONTENT_PATH
    
    print(f"Base path: {base_path}")
    
    # Normalize folder path by removing leading/trailing slashes and section prefix
    relative_folder = folder.strip('/')
    
    # Store original folder path for toctree removal
    original_folder_path = relative_folder
    
    # Calculate parent folder path BEFORE any conditional logic
    parent_folder_path = os.path.dirname(original_folder_path)
    if not parent_folder_path:
        parent_folder_path = section
    
    print(f"Parent folder path: {parent_folder_path}")
    
    # Check for various section prefix formats case-insensitively
    possible_prefixes = [
        f"{section}/",
        "content/",
        "gettingStarted/",  # With capital S
        "gettingstarted/"   # All lowercase
    ]
    
    for prefix in possible_prefixes:
        if relative_folder.lower().startswith(prefix.lower()):
            # Match found - remove this prefix
            relative_folder = relative_folder[len(prefix):]
            print(f"Removed prefix '{prefix}' from path")
            break
    
    print(f"Relative folder path after prefix removal: {relative_folder}")
    
    # Create full path with proper OS separators
    folderpath = os.path.join(base_path, relative_folder.replace('/', os.path.sep))
    print(f"Looking for folder at: {folderpath}")
    
    # First try to remove from parent toctree BEFORE deleting the folder
    index_path = os.path.join(folderpath, "index.rst")
    if os.path.exists(index_path):
        # Get the relative path for the index.rst
        relative_index_path = os.path.relpath(index_path, SPHINX_DOCS_PATH).replace("\\", "/")
        print(f"Preparing to remove {relative_index_path} from toctree")
        
        # Remove from parent toctree
        remove_from_parent_toctree(relative_index_path, section, parent_folder_path)
    
    # Now delete the folder
    if os.path.exists(folderpath):
        shutil.rmtree(folderpath)
        print(f"Deleted folder: {folderpath}")
    else:
        # Try the opposite section as a fallback
        opposite_section = 'gettingstarted' if section == 'content' else 'content'
        opposite_base_path = STARTED_PATH if section == 'content' else CONTENT_PATH
        opposite_folderpath = os.path.join(opposite_base_path, relative_folder.replace('/', os.path.sep))
        print(f"Trying opposite section path: {opposite_folderpath}")
        
        if os.path.exists(opposite_folderpath):
            # Same toctree removal logic for opposite section
            opposite_index_path = os.path.join(opposite_folderpath, "index.rst")
            if os.path.exists(opposite_index_path):
                opposite_relative_path = os.path.relpath(opposite_index_path, SPHINX_DOCS_PATH).replace("\\", "/")
                remove_from_parent_toctree(opposite_relative_path, opposite_section, parent_folder_path)
            
            shutil.rmtree(opposite_folderpath)
            print(f"Deleted folder from opposite section: {opposite_folderpath}")
        else:
            print(f"Folder not found in either section")
            
    return redirect(url_for('index'))

def remove_from_parent_toctree(relative_path, section, parent_folder=''):
    """Remove a path from the parent folder's index.rst if it exists."""
    print(f"Removing {relative_path} from parent_folder='{parent_folder}' in section='{section}'")
    
    # If no parent folder specified, use the root index.rst
    if not parent_folder:
        return remove_from_toctree(relative_path, section)
    
    # Determine parent folder's path and its index.rst
    if section == 'content':
        parent_path = os.path.join(CONTENT_PATH, parent_folder)
    else:
        parent_path = os.path.join(STARTED_PATH, parent_folder)
    
    parent_index_path = os.path.join(parent_path, 'index.rst')
    
    # If parent doesn't have an index.rst, fall back to root index.rst
    if not os.path.exists(parent_index_path):
        return remove_from_toctree(relative_path, section)
    
    # Calculate expected relative path as it would appear in the toctree
    file_full_path = os.path.join(SPHINX_DOCS_PATH, relative_path)
    rel_to_parent = os.path.relpath(file_full_path, parent_path).replace('\\', '/')
    
    print(f"Looking to remove entry that matches: {rel_to_parent}")
    
    # Read the parent's index.rst
    with open(parent_index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = False
    new_lines = []
    
    for line in lines:
        line_content = line.strip()
        
        # More specific matching: must match the exact relative path
        # or just the filename in case the path is stored differently
        if line_content == rel_to_parent or line_content == os.path.basename(rel_to_parent):
            found = True
            print(f"Found and removing: '{line_content}' from {parent_index_path}")
            continue
        new_lines.append(line)
    
    if not found:
        print(f"Warning: Could not find '{rel_to_parent}' in {parent_index_path}")
        # As a fallback, try with just the filename
        basename = os.path.basename(relative_path)
        print(f"Trying fallback with just basename: {basename}")
        
        new_lines = []
        second_attempt = False
        
        for line in lines:
            line_content = line.strip()
            if line_content.endswith(basename) and not second_attempt:
                found = True
                second_attempt = True  # Only remove one entry
                print(f"Fallback match - removing: '{line_content}'")
                continue
            new_lines.append(line)
    
    # Write back to the parent's index.rst
    with open(parent_index_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True

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

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image in request'}), 400
    
    file = request.files['image']
    document_path = request.form.get('document_path', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Determine the section (content or gettingstarted) based on the document path
    if document_path.startswith('content/'):
        section = 'content'
        base_path = CONTENT_PATH
    else:
        section = 'gettingstarted'
        base_path = STARTED_PATH
    
    # Extract the folder from document path
    document_path = document_path.strip('/')
    document_dir = os.path.dirname(document_path)
    
    # Remove section prefix from document_dir if present
    if document_dir.startswith(section + '/'):
        document_dir = document_dir[len(section) + 1:]
    
    # Define the _static folder path where image will be saved
    if document_dir:
        # Images go to the _static folder in the same directory as the document
        static_folder = os.path.join(base_path, document_dir, '_static')
    else:
        # If document is at root level, use section's _static folder
        static_folder = os.path.join(base_path, '_static')
    
    # Create _static folder if it doesn't exist
    os.makedirs(static_folder, exist_ok=True)
    
    # Secure the filename and save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(static_folder, filename)
    file.save(file_path)
    
    # Calculate the relative URL for the image
    if document_dir:
        # Relative path from document to its _static folder
        image_url = f"_static/{filename}"
    else:
        # Document is at section root
        image_url = f"_static/{filename}"
    
    return jsonify({
        'url': image_url,
        'filename': filename
    })

if __name__ == '__main__':
    app.run(debug=True)
