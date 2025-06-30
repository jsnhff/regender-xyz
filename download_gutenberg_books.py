#!/usr/bin/env python3
"""
Download top books from Project Gutenberg.

This script:
1. Fetches the top books list from Gutenberg
2. Extracts book IDs and titles
3. Downloads the plain text version of each book
4. Organizes them in a project folder structure
"""

import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import List, Tuple, Optional
import argparse

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: BeautifulSoup not available. Install with: pip install beautifulsoup4")


class GutenbergDownloader:
    """Download books from Project Gutenberg"""
    
    BASE_URL = "https://www.gutenberg.org"
    TOP_BOOKS_URL = "https://www.gutenberg.org/browse/scores/top"
    
    def __init__(self, output_dir: str = "gutenberg_books", delay: float = 1.0):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory to save downloaded books
            delay: Delay between downloads (be nice to servers)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay = delay
        self.user_agent = 'Mozilla/5.0 (Gutenberg Book Downloader)'
    
    def fetch_top_books_list(self, limit: int = 100) -> List[Tuple[str, str]]:
        """
        Fetch the list of top books from Gutenberg.
        
        Args:
            limit: Maximum number of books to fetch
            
        Returns:
            List of (book_id, title) tuples
        """
        print(f"Fetching top books list from {self.TOP_BOOKS_URL}")
        
        req = Request(self.TOP_BOOKS_URL, headers={'User-Agent': self.user_agent})
        response = urlopen(req)
        html = response.read().decode('utf-8')
        
        books = []
        
        if BS4_AVAILABLE:
            # Use BeautifulSoup for robust parsing
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the ordered list of top books
            # The structure is typically: <ol><li><a href="/ebooks/ID">Title</a>
            book_list = soup.find('ol', {'start': '1'})
            
            if book_list:
                for li in book_list.find_all('li')[:limit]:
                    link = li.find('a', href=re.compile(r'/ebooks/\d+'))
                    if link:
                        # Extract book ID from URL
                        match = re.search(r'/ebooks/(\d+)', link.get('href', ''))
                        if match:
                            book_id = match.group(1)
                            title = link.get_text(strip=True)
                            # Clean up title (remove author info if present)
                            title = re.sub(r'\s*by\s+.*$', '', title)
                            books.append((book_id, title))
        else:
            # Fallback: use regex parsing
            # Look for links like: <a href="/ebooks/1342">Pride and Prejudice by Jane Austen</a>
            pattern = r'<a[^>]+href="/ebooks/(\d+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            for book_id, full_title in matches[:limit]:
                # Clean up title
                title = re.sub(r'\s*by\s+.*$', '', full_title.strip())
                books.append((book_id, title))
        
        print(f"Found {len(books)} books")
        return books
    
    def get_text_url(self, book_id: str) -> str:
        """
        Get the plain text URL for a book.
        
        Args:
            book_id: Gutenberg book ID
            
        Returns:
            URL to the plain text file
        """
        # Gutenberg URL patterns for plain text files
        # Try multiple patterns as they can vary
        patterns = [
            f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
            f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
            f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
        ]
        
        # Try each pattern
        for url in patterns:
            try:
                req = Request(url, headers={'User-Agent': self.user_agent})
                req.get_method = lambda: 'HEAD'
                response = urlopen(req)
                if response.getcode() == 200:
                    return url
            except:
                continue
        
        # If none work, return the most common pattern
        return patterns[1]
    
    def sanitize_filename(self, title: str) -> str:
        """
        Sanitize a title for use as a filename.
        
        Args:
            title: Book title
            
        Returns:
            Sanitized filename
        """
        # Remove/replace problematic characters
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = re.sub(r'\s+', '_', title)
        title = title.strip('._')
        
        # Limit length
        if len(title) > 100:
            title = title[:100]
        
        return title
    
    def download_book(self, book_id: str, title: str) -> Optional[Path]:
        """
        Download a single book.
        
        Args:
            book_id: Gutenberg book ID
            title: Book title
            
        Returns:
            Path to downloaded file or None if failed
        """
        # Create folder for this book
        safe_title = self.sanitize_filename(title)
        book_dir = self.output_dir / f"{book_id}_{safe_title}"
        book_dir.mkdir(exist_ok=True)
        
        # Get text URL
        text_url = self.get_text_url(book_id)
        
        # Download the text
        try:
            print(f"Downloading: {title} (ID: {book_id})")
            print(f"  URL: {text_url}")
            
            req = Request(text_url, headers={'User-Agent': self.user_agent})
            response = urlopen(req)
            content = response.read()
            
            # Save the text
            output_file = book_dir / f"pg{book_id}.txt"
            output_file.write_bytes(content)
            
            # Also save metadata
            metadata_file = book_dir / "metadata.txt"
            metadata_file.write_text(
                f"Title: {title}\n"
                f"Book ID: {book_id}\n"
                f"Source URL: {text_url}\n"
                f"Downloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            
            print(f"  Saved to: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"  ERROR: Failed to download - {e}")
            return None
    
    def download_top_books(self, limit: int = 10):
        """
        Download the top N books from Gutenberg.
        
        Args:
            limit: Number of books to download
        """
        # Get the list of top books
        books = self.fetch_top_books_list(limit)
        
        if not books:
            print("No books found!")
            return
        
        # Download each book
        successful = 0
        failed = 0
        
        for i, (book_id, title) in enumerate(books, 1):
            print(f"\n[{i}/{len(books)}] Processing: {title}")
            
            if self.download_book(book_id, title):
                successful += 1
            else:
                failed += 1
            
            # Be nice to the server
            if i < len(books):
                time.sleep(self.delay)
        
        # Summary
        print(f"\nDownload complete!")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Books saved to: {self.output_dir.absolute()}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download top books from Project Gutenberg"
    )
    parser.add_argument(
        "-n", "--number",
        type=int,
        default=10,
        help="Number of books to download (default: 10)"
    )
    parser.add_argument(
        "-o", "--output",
        default="gutenberg_books",
        help="Output directory (default: gutenberg_books)"
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=1.0,
        help="Delay between downloads in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    # Create downloader and run
    downloader = GutenbergDownloader(
        output_dir=args.output,
        delay=args.delay
    )
    
    downloader.download_top_books(limit=args.number)


if __name__ == "__main__":
    main()