#!/usr/bin/env python3
"""
CLI visual enhancements for regender-xyz.
Provides colorful output, stylish banners, and animated loading indicators.
"""

import sys
import time
import threading
import itertools
from typing import List, Callable, Optional, Any

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class GenderSpinner:
    """Animated spinner that visually represents gender transformation."""
    
    def __init__(self, message: str = "Processing", delay: float = 0.08, transform_type: str = "feminine"):
        """Initialize the spinner.
        
        Args:
            message: Message to display alongside the spinner
            delay: Delay between frames in seconds
            transform_type: Type of transformation (feminine, masculine, neutral)
        """
        self.message = message
        self.delay = delay
        self.transform_type = transform_type
        self.running = False
        self.spinner_thread = None
        
        # Use a single color for all spinners regardless of gender type
        self.color = Colors.BRIGHT_WHITE
        
        # Star animation frames - more visible than dots12
        self.frames = ["✶", "✸", "✹", "✺", "✹", "✷"]
    
    def _spin(self):
        """Internal method to animate the spinner."""
        write = sys.stdout.write
        flush = sys.stdout.flush
        
        while self.running:
            for frame in self.frames:
                if not self.running:
                    break
                # Minimal and sleek design with star at the front
                write(f"\r{self.color}{frame}{Colors.RESET} {self.message}")
                flush()
                time.sleep(self.delay)
    
    def start(self):
        """Start the spinner animation."""
        if not self.running:
            self.running = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
    
    def stop(self):
        """Stop the spinner animation."""
        self.running = False
        if self.spinner_thread:
            self.spinner_thread.join()


class ProgressBar:
    """Minimal animated progress bar."""
    
    def __init__(self, total: int = 100, width: int = 40, transform_type: str = "feminine"):
        """Initialize the progress bar.
        
        Args:
            total: Total number of steps
            width: Width of the progress bar in characters
            transform_type: Type of transformation (feminine, masculine, neutral)
        """
        self.total = total
        self.width = width
        self.transform_type = transform_type
        
        # Use a single color for all progress bars
        self.color = Colors.BRIGHT_WHITE
        
        # Minimal progress bar characters
        self.progress_char = "█"  # Solid block
        self.empty_char = "░"     # Light shade
    
    def update(self, progress: int):
        """Update the progress bar.
        
        Args:
            progress: Current progress (0 to total)
        """
        # Ensure progress is within bounds
        progress = max(0, min(self.total, progress))
        
        # Calculate percentage
        percent = progress / self.total
        
        # Calculate how many characters to fill
        filled_width = int(self.width * percent)
        
        # Create the progress bar with simple filled/empty characters
        bar = self.progress_char * filled_width + self.empty_char * (self.width - filled_width)
        
        # Print the progress bar without brackets but with color
        sys.stdout.write(f"\r{self.color}{bar}{Colors.RESET} {int(percent * 100)}%")
        sys.stdout.flush()
    
    def finish(self):
        """Complete the progress bar with a checkmark."""
        self.update(self.total)  # Ensure the bar is filled
        print(f" {Colors.BRIGHT_GREEN}✓{Colors.RESET}")  # Add checkmark and move to the next line
        sys.stdout.flush()


def print_fancy_banner():
    """Print a minimal and sleek banner for the application."""
    banner = f"""
{Colors.BRIGHT_CYAN}╭───────────────────────────────────────────────╮{Colors.RESET}
{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.BOLD}{Colors.BRIGHT_WHITE}regender-xyz{Colors.RESET}                          
{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.ITALIC}transforming gender in literature{Colors.RESET}         
{Colors.BRIGHT_CYAN}│{Colors.RESET}  v0.3.0                          
{Colors.BRIGHT_CYAN}╰───────────────────────────────────────────────╯{Colors.RESET}
"""    
    print(banner)


def print_section_header(title: str):
    """Print a minimal and sleek section header.
    
    Args:
        title: Section title
    """
    print(f"\n{Colors.BRIGHT_CYAN}┌───────────────────────────────────────────────┐{Colors.RESET}")
    print(f"{Colors.BRIGHT_CYAN}│{Colors.RESET} {Colors.BOLD}{Colors.WHITE}{title}{Colors.RESET} {Colors.BRIGHT_CYAN}│{Colors.RESET}")
    print(f"{Colors.BRIGHT_CYAN}└───────────────────────────────────────────────┘{Colors.RESET}")


def print_success(message: str):
    """Print a success message.
    
    Args:
        message: Success message
    """
    print(f"{Colors.BRIGHT_GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print a warning message.
    
    Args:
        message: Warning message
    """
    print(f"{Colors.BRIGHT_YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message.
    
    Args:
        message: Error message
    """
    print(f"{Colors.BRIGHT_RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message.
    
    Args:
        message: Info message
    """
    print(f"{Colors.BRIGHT_BLUE}ℹ {message}{Colors.RESET}")


def run_with_spinner(func: Callable, message: str = "Processing", transform_type: str = "feminine", *args, **kwargs) -> Any:
    """Run a function with a spinner animation.
    
    Args:
        func: Function to run
        message: Message to display alongside the spinner
        transform_type: Type of transformation (feminine, masculine, neutral)
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The return value of the function
    """
    spinner = GenderSpinner(message, transform_type=transform_type)
    spinner.start()
    try:
        result = func(*args, **kwargs)
        # Replace the star with a checkmark at the front
        sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✓{Colors.RESET} {spinner.message}")
        sys.stdout.flush()
        print()  # Now move to the next line
        return result
    finally:
        spinner.stop()


def simulate_pipeline():
    """Simulate a pipeline run to demonstrate the full CLI visuals."""
    print_section_header("Simulated Pipeline Run")
    print_info("Running full pipeline on: sample_text.txt")
    
    # Step 1: Character Analysis
    print_section_header("Step 1: Character Analysis")
    
    def run_analysis():
        # Simulate analysis delay
        time.sleep(3)
        return {"characters": {"Character 1": {}, "Character 2": {}}}
    
    result = run_with_spinner(run_analysis, "Analyzing text for characters", "neutral")
    print(f"\nFound {len(result['characters'])} characters:")
    for name in result['characters'].keys():
        print(f"- {name}: 5 mentions")
    
    # Step 2: Gender Transformation
    print_section_header("Step 2: Gender-neutral Transformation")
    
    def run_transform():
        # Simulate transformation delay
        time.sleep(3)
        return "Transformed text", ["Change 1", "Change 2"]
    
    transformed, changes = run_with_spinner(run_transform, "Applying Gender-neutral transformation", "neutral")
    
    print("\nChanges made:")
    for change in changes:
        print(f"- {change}")
    
    print("\nTransformed text saved to output/sample.txt")
    print_success("Pipeline completed successfully!")


if __name__ == "__main__":
    # Demo
    print_fancy_banner()
    print_section_header("Demo of CLI Visuals")
    
    print_info("This is an info message")
    print_success("This is a success message")
    print_warning("This is a warning message")
    print_error("This is an error message")
    
    print("\nDemonstrating spinners:")
    
    print("\nFeminine transformation spinner:")
    spinner = GenderSpinner("Transforming to feminine", transform_type="feminine")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Feminine transformation complete{Colors.RESET}")
    
    print("\nMasculine transformation spinner:")
    spinner = GenderSpinner("Transforming to masculine", transform_type="masculine")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Masculine transformation complete{Colors.RESET}")
    
    print("\nNeutral transformation spinner:")
    spinner = GenderSpinner("Transforming to neutral", transform_type="neutral")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Neutral transformation complete{Colors.RESET}")
    
    print("\nDemonstrating editing progress bars:")
    
    print("\nEditing progress bar 1:")
    bar = ProgressBar(total=100, transform_type="feminine")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
    
    print("\nEditing progress bar 2:")
    bar = ProgressBar(total=100, transform_type="masculine")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
    
    print("\nEditing progress bar 3:")
    bar = ProgressBar(total=100, transform_type="neutral")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
    
    # Run simulated pipeline to show full design
    print("\n")
    simulate_pipeline()
