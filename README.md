# GUI for Docs Manual

## About

This is a simple web-based documentation management system designed specifically for creating and maintaining Sphinx-based documentation. It provides an intuitive interface for organizing, editing, and publishing structured documentation with minimal technical knowledge required. THe app requires that you have set up a Sphinx program and updated the path: SPHINX_DOCS_PATH = "". the Sphinx program also needs to have a folder set up called "gettingstarted" and one name "content". This can ofcourse be configured.

## Features

- **Dual Section Management**: Organize content into "Getting Started" and "Content" sections
- **Rich Markdown Editor**: Full-featured editor with live preview and syntax highlighting
- **Image Management**: Upload and embed images directly from your computer
- **Hierarchical Organization**: Create nested folder structures with proper indexing
- **Automatic TOC**: Maintains table of contents (toctree) entries automatically
- **Static Asset Management**: Creates and manages _static folders for images and other assets
- **Real-Time Preview**: See how your documentation will look before publishing
- **Documentation Building**: Build and publish your Sphinx documentation with one click

## Setup

1. Clone this repository
2. Install the required dependencies: `pip install -r requirements.txt`
3. Configure your Sphinx documentation path in `app.py`
4. Run the application: `python app.py`
5. Access the web interface at http://localhost:5000

## Usage

### Creating Content

- Use the "New File" button to create new documentation pages
- Use the "New Folder" button to create new sections with proper index files
- Select a section (Getting Started or Content) for your new pages and folders

### Editing Content

- Click on any file to open the rich text editor
- Use the formatting toolbar for common Markdown elements
- Upload images by clicking the image button and selecting a file
- Preview your changes in real-time with the side-by-side view

### Building Documentation

- Click the "Build Docs" button to compile your Sphinx documentation
- Access the built HTML files in the configured build directory

## Technologies

- Flask (Python web framework)
- EasyMDE (Markdown editor)
- Sphinx (Documentation generator)
- Bootstrap (UI framework)

