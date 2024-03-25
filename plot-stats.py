import pandas as pd
import matplotlib.pyplot as plt
from git import Repo

import sys
import os

def get_line_modification_dates(repo_path, file_path):
    """
    Get modification dates for lines in a specified file within a git repository.
    
    Parameters:
    repo_path (str): Path to the repository's root directory.
    file_path (str): Path to the file relative to the repository's root directory.
    
    Returns:
    list of str: Dates when lines in the file were modified.
    """
    # Initialize the repo object
    repo = Repo(repo_path)
    
    # Get commits affecting the given file
    commits = list(repo.iter_commits(paths=file_path))
    
    # Extract the dates of these commits
    dates = [commit.committed_datetime.strftime('%Y-%m-%d') for commit in commits]
    
    return dates


## FIXME - this does not work entirely fine - some strange glitches happen, although it counts the multiple-line-added situations correctly
def get_commit_dates_for_lines(repo_path, file_path):
    """
    Get commit dates for each line in a file, duplicating dates for lines added in the same commit.
    
    Parameters:
    repo_path (str): Path to the repository.
    file_path (str): Path to the file within the repository.
    
    Returns:
    list of str: A list of dates corresponding to each line in the file.
    """
    repo = Repo(repo_path)
    
    # Reverse the commit list to start from the first commit
    commits = list(repo.iter_commits(paths=file_path, reverse=True))
    
    line_dates = []

    for commit in commits:
        # Get the diff from this commit to its parent (or an empty tree if no parent)
        parent = commit.parents[0] if commit.parents else None
        diffs = commit.diff(parent, paths=file_path, create_patch=True)
        
        for diff in diffs:
            # Parse the diff to count the number of lines added
            diff_lines = diff.diff.decode().split('\n')
            removed_lines = [line for line in diff_lines if line.startswith('-') and not line.startswith('---')]

            # For each line added, record the commit date
            for _ in removed_lines:
                line_dates.append(commit.committed_datetime.strftime('%Y-%m-%d'))
    
    return line_dates


def parse_books_file(file_path, dates):
    """
    Parses the given file to separate comic books (marked with [K] at the end) from other books.

    Parameters:
    file_path (str): Path to the file containing the list of books.

    Returns:
    tuple: Two lists, the first with dates of all books, and the second excluding comic books.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    all_books = []
    non_comic_books = []

    for date, book_info in zip(dates, lines):
        if book_info.strip().endswith("[K]"):
            all_books.append(date)  # Comic book, add only to all_books
        else:
            all_books.append(date)
            non_comic_books.append(date)  # Non-comic book, add to both lists

    return all_books, non_comic_books

def plot_reading_progress(dates, dates_no_comics, target_books, output_file):
    # Convert list of dates into DataFrames
    df_books = pd.DataFrame({"Date": pd.to_datetime(dates), "Count": 1})
    df_books.set_index("Date", inplace=True)
    df_books_no_comics = pd.DataFrame({"Date": pd.to_datetime(dates_no_comics), "Count": 1})
    df_books_no_comics.set_index("Date", inplace=True)
    
    # Monthly cumulative count of books read
    df_books_monthly = df_books.resample("ME").sum().cumsum()
    df_books_monthly = df_books_monthly.asfreq('ME', fill_value=0)
    df_books_monthly['Month'] = df_books_monthly.index.month
    df_books_no_comics_monthly = df_books_no_comics.resample("ME").sum().cumsum()
    df_books_no_comics_monthly = df_books_no_comics_monthly.asfreq('ME', fill_value=0)
    
    # Create a target line for reading goal
    months = pd.date_range(start=df_books_monthly.index.min(), end=df_books_monthly.index.max(), freq='ME').month
    target_line = pd.DataFrame({'Month': months, 'Target': (months / 12) * target_books})
    
    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(df_books_monthly['Month'], df_books_monthly['Count'], marker='o', linestyle='-', label='All Books Read')
    plt.plot(df_books_no_comics_monthly.index.month, df_books_no_comics_monthly['Count'], marker='^', linestyle='-', color='green', label='Books Read (excluding comics)')
    plt.plot(target_line['Month'], target_line['Target'], linestyle='--', color='red', label='Target Line')
    plt.title('Cumulative Number of Books Read vs. Target')
    plt.xlabel('Month')
    plt.ylabel('Cumulative Number of Books Read/Target')
    plt.xticks(range(1, 13))
    plt.legend()
    plt.grid(True)
    
    # Save the plot to a file
    plt.savefig(output_file)
    plt.close()  # Close the figure to free up memory

target_books = 25

if __name__ == "__main__":

    if len(sys.argv) == 1:
        print(f"usage: {sys.argv[0]} file_name.md")
        exit(1)
    
    file_path = sys.argv[1]
    repo_path = os.getcwd() 

    modification_dates = get_line_modification_dates(repo_path, file_path)
    # modification_dates = get_commit_dates_for_lines(repo_path, file_path)

    all_books_dates, non_comic_books_dates = parse_books_file(file_path, modification_dates)

    output_file = file_path.split(".")[0] + ".png"
    plot_reading_progress(all_books_dates, non_comic_books_dates, target_books, "plots/" + output_file)
