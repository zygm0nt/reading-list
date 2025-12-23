#!/usr/bin/env python3
import json
import yaml
from collections import Counter


class IndentDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# Read the categorized books JSON
with open('books_categorized.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Process each year
output = {}

for year in sorted(data.keys()):
    year_data = data[year]
    books = year_data.get('books', [])
    
    # Count books by category
    category_counts = Counter(book['category'] for book in books)
    
    # Convert to list format matching books_data.yaml
    output[int(year)] = [
        {
            'kategoria': category,
            'ilosc': count
        }
        for category, count in sorted(category_counts.items())
    ]

# Write to YAML file
with open('books_data.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False, Dumper=IndentDumper,)

print(f"Successfully converted books_categorized.json to books_data.yaml")
print(f"Processed {len(output)} years")
