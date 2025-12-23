#!/usr/bin/env python3
"""
Extract books from YEAR.md files and generate a JSON file.
"""
import re
import json
import glob
from pathlib import Path

def extract_books_from_file(file_path):
    """Extract books from a single YEAR.md file."""
    books = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by lines and process
    lines = content.split('\n')
    current_entry = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a new numbered entry (starts with number and dot)
        match = re.match(r'^\d+\.\s*(.*)', line)
        if match:
            # Save previous entry if exists
            if current_entry:
                book = parse_book_entry(current_entry)
                if book:
                    books.append(book)
            
            # Start new entry
            current_entry = match.group(1)
        elif current_entry:
            # Continuation of previous entry (multi-line)
            current_entry += ' ' + line
    
    # Don't forget the last entry
    if current_entry:
        book = parse_book_entry(current_entry)
        if book:
            books.append(book)
    
    return books

def parse_book_entry(entry):
    """Parse a book entry to extract author and title."""
    # Remove common markers and tags
    entry = entry.strip()
    
    # Remove (*) marker at the start
    entry = re.sub(r'^\(\*\)\s*', '', entry)
    
    # Remove tags like [A], [K], [R], [DNF] etc.
    entry = re.sub(r'\[[^\]]+\]', '', entry)
    
    # Remove dates and ratings (patterns like "12.01.2015", "4 -", "5/10", etc.)
    entry = re.sub(r'\d+\.\d+\.\d+', '', entry)  # Dates
    entry = re.sub(r'\d+\s*-\s*\d+', '', entry)  # Date ranges
    entry = re.sub(r'\d+/\d+', '', entry)  # Ratings like 2/10
    entry = re.sub(r'-\s*\d+\s*-', '', entry)  # Ratings like "- 4 -"
    entry = re.sub(r'-\s*\d+$', '', entry)  # Ratings at end like "- 4"
    
    # Remove common suffixes
    entry = re.sub(r'\s*-\s*unfinished.*$', '', entry, flags=re.IGNORECASE)
    entry = re.sub(r'\s*DNF.*$', '', entry, flags=re.IGNORECASE)
    entry = re.sub(r'\s*might come back.*$', '', entry, flags=re.IGNORECASE)
    entry = re.sub(r'\s*słabo napisany.*$', '', entry, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    entry = re.sub(r'\s+', ' ', entry).strip()
    
    # Try to extract author and title
    # Pattern: Author "Title" or Author Title (without quotes)
    # Some entries might not have quotes
    match = re.match(r'^(.+?)\s+"([^"]+)"', entry)
    if match:
        author = match.group(1).strip()
        title = match.group(2).strip()
        return {"author": author, "title": title}
    
    # Try without quotes - look for common patterns
    # If entry doesn't have quotes, try to split by common separators
    # For now, let's try to find title in quotes first, if not, use the whole entry
    if not entry:
        return None
    
    # If no quotes found, try to extract from the whole entry
    # Some entries might be just titles
    # For simplicity, if no quotes, treat the whole thing as title with empty author
    # But let's be smarter - look for patterns like "Author Title" where Title might be capitalized
    # Actually, let's just store what we have
    parts = entry.split(' ', 1)
    if len(parts) == 2:
        return {"author": parts[0], "title": parts[1]}
    else:
        return {"author": "", "title": entry}

def main():
    """Main function to extract books from all YEAR.md files."""
    books_by_year = {}
    
    # Find all YEAR.md files (2011.md through 2025.md or any 4-digit year)
    year_files = sorted(glob.glob('[0-9][0-9][0-9][0-9].md'))
    
    for file_path in year_files:
        year = Path(file_path).stem
        print(f"Processing {file_path}...")
        
        try:
            books = extract_books_from_file(file_path)
            books_by_year[year] = books
            print(f"  Found {len(books)} books")
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            books_by_year[year] = []
    
    # Write to JSON file
    output_file = 'books.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(books_by_year, f, ensure_ascii=False, indent=2)
    
    print(f"\nExtracted books written to {output_file}")
    print(f"Total years: {len(books_by_year)}")
    print(f"Total books: {sum(len(books) for books in books_by_year.values())}")

if __name__ == '__main__':
    main()

