#!/usr/bin/env python3
"""
Categorize books from books.json using ChatGPT API.
For each year, sends all books to ChatGPT and asks for categorization.
"""
import json
import os
import sys
import pickle
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Allowed categories
ALLOWED_CATEGORIES = {
    "non-fiction",
    "sci-fi",
    "fantasy",
    "comic books",
    "tech books",
    "self-development books",
    "history"
}

def validate_response(books_sent: List[Dict], response_data: Dict) -> Tuple[bool, str, List[str]]:
    """
    Validate that the ChatGPT response contains all books and valid categories.
    Returns (is_valid, error_message, warnings)
    Missing books are treated as warnings, not errors.
    """
    warnings = []
    
    if not isinstance(response_data, dict) or "books" not in response_data:
        return False, "Response must be a JSON object with a 'books' key", warnings
    
    categorized_books = response_data["books"]
    
    if not isinstance(categorized_books, list):
        return False, "Response 'books' must be an array", warnings
    
    # Check that all books are present (treat as warning, not error)
    sent_titles = {book["title"].lower() for book in books_sent}
    received_titles = {book.get("title", "").lower() for book in categorized_books}
    
    missing_books = sent_titles - received_titles
    if missing_books:
        warning_msg = f"Missing books in response: {missing_books}"
        warnings.append(warning_msg)
    
    # Check that all categories are valid
    invalid_categories = set()
    for book in categorized_books:
        category = book.get("category", "").lower().strip()
        if category and category not in ALLOWED_CATEGORIES:
            invalid_categories.add(book.get("category", ""))
    
    if invalid_categories:
        return False, f"Invalid categories found: {invalid_categories}. Allowed: {ALLOWED_CATEGORIES}", warnings
    
    # Check that each book has required fields
    for book in categorized_books:
        if "title" not in book:
            return False, "Some books in response are missing 'title' field", warnings
        if "category" not in book:
            return False, f"Book '{book.get('title', 'unknown')}' is missing 'category' field", warnings
    
    return True, "", warnings

def get_books_hash(books: List[Dict]) -> str:
    """
    Generate a hash of the books list to detect changes.
    """
    # Create a stable representation of books for hashing
    books_repr = json.dumps(books, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(books_repr.encode('utf-8')).hexdigest()

def load_cache(cache_file: str) -> Dict[str, Dict[str, Any]]:
    """
    Load cache from pickle file.
    Returns dict with structure: {year: {'books_hash': str, 'response': dict}}
    """
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cache = pickle.load(f)
            print(f"  Loaded cache from {cache_file} ({len(cache)} years cached)")
            return cache
        except Exception as e:
            print(f"  Warning: Failed to load cache: {e}")
            return {}
    return {}

def save_cache(cache: Dict[str, Dict[str, Any]], cache_file: str):
    """
    Save cache to pickle file.
    """
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)
        print(f"  Cache saved to {cache_file}")
    except Exception as e:
        print(f"  Warning: Failed to save cache: {e}")

def log_response(log_file: Optional[object], year: str, prompt: str, response_text: str, response_data: Optional[Dict] = None, error: Optional[str] = None):
    """
    Log OpenAI response to file.
    """
    if log_file:
        timestamp = datetime.now().isoformat()
        log_file.write(f"\n{'='*80}\n")
        log_file.write(f"Year: {year}\n")
        log_file.write(f"Timestamp: {timestamp}\n")
        log_file.write(f"{'='*80}\n\n")
        
        log_file.write("PROMPT:\n")
        log_file.write("-" * 80 + "\n")
        log_file.write(prompt + "\n\n")
        
        log_file.write("RAW RESPONSE:\n")
        log_file.write("-" * 80 + "\n")
        log_file.write(response_text + "\n\n")
        
        if response_data:
            log_file.write("PARSED RESPONSE:\n")
            log_file.write("-" * 80 + "\n")
            log_file.write(json.dumps(response_data, ensure_ascii=False, indent=2) + "\n\n")
        
        if error:
            log_file.write("ERROR:\n")
            log_file.write("-" * 80 + "\n")
            log_file.write(error + "\n\n")
        
        log_file.flush()

def categorize_year_books(client: OpenAI, year: str, books: List[Dict], log_file: Optional[object] = None, cache: Optional[Dict] = None, cache_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Send books for a year to ChatGPT and get categorization.
    Uses cache if available.
    """
    # Check cache first
    books_hash = get_books_hash(books)
    if cache is not None and year in cache:
        cached_entry = cache[year]
        if cached_entry.get('books_hash') == books_hash:
            print(f"  Using cached response for {year}...")
            cached_response = cached_entry.get('response', {})
            # Still log the cached response
            if log_file:
                log_response(log_file, year, f"[CACHED] {len(books)} books", "[CACHED RESPONSE]", cached_response)
            print(f"  ✓ Using cached categorization for {len(cached_response.get('books', []))} books")
            return cached_response
        else:
            print(f"  Cache invalid for {year} (books changed), fetching new response...")
    
    # Build the prompt
    books_list = "\n".join([f"- {book['author']} \"{book['title']}\"" for book in books])
    
    prompt = f"""Please categorize the following books from {year} into one of these categories:
- non-fiction
- sci-fi
- fantasy
- comic books
- tech books
- self-development books
- history

Books:
{books_list}

Return a JSON object with this exact structure:
{{
  "books": [
    {{
      "author": "Author Name",
      "title": "Book Title",
      "category": "one of the categories above"
    }},
    ...
  ]
}}

Make sure:
1. All books are included in the response
2. Each book has exactly one category from the list above
3. The category matches one of the 7 categories exactly (case-insensitive)
4. Return ONLY valid JSON, no additional text or markdown formatting"""
    
    print(f"  Sending {len(books)} books to ChatGPT...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that categorizes books. Always return valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        response_data = json.loads(response_text)
        
        # Log response
        log_response(log_file, year, prompt, response_text, response_data)
        
        # Validate response
        is_valid, error_msg, warnings = validate_response(books, response_data)
        
        # Log warnings (missing books, etc.) but continue processing
        if warnings:
            for warning in warnings:
                print(f"  WARNING: {warning}")
                if log_file:
                    log_response(log_file, year, prompt, response_text, response_data, warning)
        
        # Only fail on actual errors (invalid structure, invalid categories, missing required fields)
        if not is_valid:
            print(f"  ERROR: {error_msg}")
            log_response(log_file, year, prompt, response_text, response_data, error_msg)
            return {"error": error_msg, "books": []}
        
        # Save to cache if valid
        if cache is not None:
            cache[year] = {
                'books_hash': books_hash,
                'response': response_data
            }
            if cache_file:
                save_cache(cache, cache_file)
        
        print(f"  ✓ Successfully categorized {len(response_data['books'])} books")
        return response_data
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response: {e}"
        print(f"  ERROR: {error_msg}")
        log_response(log_file, year, prompt, response_text if 'response_text' in locals() else "N/A", None, error_msg)
        return {"error": error_msg, "books": []}
    except Exception as e:
        error_msg = f"API error: {e}"
        print(f"  ERROR: {error_msg}")
        log_response(log_file, year, prompt, "N/A", None, error_msg)
        return {"error": error_msg, "books": []}

def main():
    """Main function to categorize all books."""
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it either:")
        print("  1. Create a .env file with: OPENAI_API_KEY=your-api-key")
        print("  2. Or export it: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Load books.json
    input_file = "books.json"
    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found")
        sys.exit(1)
    
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        books_by_year = json.load(f)
    
    print(f"Found {len(books_by_year)} years to process\n")
    
    # Load cache
    cache_file = "openai_cache.pkl"
    cache = load_cache(cache_file)
    
    # Open log file for OpenAI responses
    log_file_path = "openai_responses.log"
    log_file = open(log_file_path, 'w', encoding='utf-8')
    log_file.write(f"OpenAI API Response Log\n")
    log_file.write(f"Started: {datetime.now().isoformat()}\n")
    log_file.write(f"{'='*80}\n\n")
    
    try:
        # Categorize books for each year
        categorized_by_year = {}
        
        for year in sorted(books_by_year.keys()):
            books = books_by_year[year]
            print(f"Processing {year} ({len(books)} books)...")
            
            result = categorize_year_books(client, year, books, log_file, cache, cache_file)
            categorized_by_year[year] = result
            
            # Wait for user input before continuing
            print(f"\n  Year {year} completed. Press Enter to continue to next year (or Ctrl+C to exit)...")
            try:
                input()
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Saving progress...")
                break
    finally:
        log_file.close()
        print(f"\n  Responses logged to {log_file_path}")
        # Save cache one final time
        save_cache(cache, cache_file)
    
    # Save results
    output_file = "books_categorized.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categorized_by_year, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Categorization complete!")
    print(f"Results saved to {output_file}")
    
    # Print summary
    total_books = 0
    total_errors = 0
    for year, result in categorized_by_year.items():
        if "error" in result:
            total_errors += 1
            print(f"  {year}: ERROR - {result['error']}")
        else:
            count = len(result.get("books", []))
            total_books += count
            print(f"  {year}: {count} books categorized")
    
    print(f"\nTotal: {total_books} books categorized, {total_errors} errors")

if __name__ == '__main__':
    main()

