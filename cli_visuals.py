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
    
    # Class-level variable to track the current active spinner
    current_spinner = None
    
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
        self.last_drawn_line = ""
        
        # Use green color for the star to match the text
        self.color = Colors.BRIGHT_GREEN
        
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
                # Clear the line and redraw the spinner
                spinner_text = f"{self.color}{frame}{Colors.RESET} {Colors.BRIGHT_GREEN}{self.message}{Colors.RESET}"
                write("\r" + " " * 80 + "\r" + spinner_text)
                self.last_drawn_line = spinner_text
                flush()
                time.sleep(self.delay)
    
    def start(self):
        """Start the spinner animation."""
        # Stop any existing spinner
        if GenderSpinner.current_spinner and GenderSpinner.current_spinner.running:
            GenderSpinner.current_spinner.stop()
        
        # Set this as the current spinner
        GenderSpinner.current_spinner = self
        
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
        
        # Clear the current spinner reference
        if GenderSpinner.current_spinner == self:
            GenderSpinner.current_spinner = None


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
    print(
        f"\n{Colors.RESET}"
        f"╭───────────────────────────────────────────────╮\n"
        f"│  {Colors.BOLD}regender-xyz{Colors.RESET}                          \n"
        f"│  {Colors.ITALIC}transforming gender in literature{Colors.RESET}         \n"
        f"│  {Colors.BRIGHT_BLACK}v0.3.1{Colors.RESET}                          \n"
        f"╰───────────────────────────────────────────────╯\n"
    )


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
    # Create a new spinner with the specified message
    spinner = GenderSpinner(message, transform_type=transform_type)
    spinner.start()
    start_time = time.time()
    
    try:
        # Run the function with the provided arguments
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Clear the line before showing completion
        sys.stdout.write("\r" + " " * 80)
        
        # Replace the star with a checkmark at the front
        sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✓ {spinner.message}{Colors.RESET}")
        sys.stdout.flush()
        print()  # Now move to the next line
        
        # For long-running processes, show the total time taken
        if elapsed_time > 10:  # Only show for processes that took more than 10 seconds
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            print_info(f"Completed in {minutes}m {seconds}s")
            
        return result
    except Exception as e:
        # Clear the line before showing error
        sys.stdout.write("\r" + " " * 80)
        
        # Replace the star with an X at the front to indicate failure
        sys.stdout.write(f"\r{Colors.BRIGHT_RED}✗ {spinner.message}{Colors.RESET}")
        sys.stdout.flush()
        print()  # Now move to the next line
        raise e
    finally:
        # Always stop the spinner when done
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


def simulate_novel_transformation():
    """Simulate a novel transformation run with the new colored logging format."""
    # Import ColoredFormatter-like functionality directly to avoid circular imports
    class Colors:
        RESET = "\033[0m"
        WHITE = "\033[37m"        # White for regular text
        BRIGHT_WHITE = "\033[97m" # Bright white for emphasis
        BRIGHT_BLACK = "\033[90m"  # Dark gray for timestamps
        GREEN = "\033[32m"        # Green for INFO
        YELLOW = "\033[33m"       # Yellow for WARNING
        RED = "\033[31m"          # Red for ERROR
        BRIGHT_RED = "\033[91m"   # Bright red for CRITICAL
        BRIGHT_GREEN = "\033[92m" # Bright green for success
        CYAN = "\033[36m"         # Cyan for DEBUG
    
    print_section_header("Full Novel Transformation")
    print_info("Processing novel: pride_and_prejudice_full.txt")
    print_info("Transformation type: Gender-neutral")
    print_info("Output file: output/neutral_pride_and_prejudice.txt")
    print_info("Chapters per chunk: 5")
    print_info("Debug directory: debug_full")
    
    print(f"\n{Colors.YELLOW}This operation will process the entire novel and may take a significant amount of time.{Colors.RESET}")
    confirm = input(f"Do you want to proceed? (y/n): ")
    if confirm.lower() not in ["y", "yes"]:
        print_info("Operation cancelled by user")
        return
    
    # Simulate identifying chapters
    print(f"{Colors.WHITE}✓ Starting transformation of pride_and_prejudice_full.txt with type: neutral{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:15]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Using model: gpt-4.1-mini, chapters per chunk: 5{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:15]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Loaded text file: 755922 characters{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:16]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Identifying chapters in the text...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:16]{Colors.RESET}")
    
    # Show the spinner for a moment
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✶{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and continue with log messages
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    print(f"{Colors.WHITE}✓ Identifying chapters using AI...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:16]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Sending chapter identification request to gpt-4.1-mini...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:17]{Colors.RESET}")
    
    # Show the spinner again
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✸{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and continue with log messages
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    print(f"{Colors.WHITE}✓ Successfully identified 61 chapters{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:25]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Identified 61 chapters in 8.27 seconds{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:25]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Chapter 1: Chapter I - 3900 chars{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:25]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Chapter 2: Chapter II - 4200 chars{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:25]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Chapter 3: Chapter III - 5100 chars{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:25]{Colors.RESET}")
    
    # Simulate character analysis
    print(f"{Colors.WHITE}✓ Analyzing characters in the full text...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:42:26]{Colors.RESET}")
    
    # Show the spinner again
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✹{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and continue with log messages
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    print(f"{Colors.WHITE}✓ Identified 24 characters in 63.72 seconds{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:30]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Character: Mr. Bennet, Gender: male, Role: Father of the Bennet family{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:30]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Character: Mrs. Bennet, Gender: female, Role: Mother of the Bennet family{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:30]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Character: Elizabeth, Gender: female, Role: Second eldest Bennet daughter{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:30]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Processing 13 chunks of approximately 5 chapters each{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:31]{Colors.RESET}")
    
    # Chunk 1
    print(f"{Colors.WHITE}✓ Processing chunk 1/13: 21707 characters (7.7% complete){Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:31]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Sending transformation request to gpt-4.1-mini...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:32]{Colors.RESET}")
    
    # Show the spinner again
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✺{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and continue with log messages
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    print(f"{Colors.WHITE}✓ Successfully transformed text with 87 changes{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Chunk 1 processed in 20.17 seconds with 87 changes{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Estimated time remaining: 4m 22s{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Change 1: Changed 'Mr.' to 'Mx.'{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Change 2: Changed 'Mrs.' to 'Mx.'{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Change 3: Changed 'he/she' to 'they'{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Change 4: Changed 'him/her' to 'them'{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Change 5: Changed 'his/her' to 'their'{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ ... and 82 more changes{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:52]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Processing chunk 2/13: 19845 characters (15.4% complete){Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:53]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Estimated time remaining: 4m 01s{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:53]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Sending transformation request to gpt-4.1-mini...{Colors.RESET} {Colors.BRIGHT_BLACK}[16:43:53]{Colors.RESET}")
    
    # Show the spinner again
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✹{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and continue with log messages
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    print(f"{Colors.WHITE}✓ Successfully transformed text with 92 changes{Colors.RESET} {Colors.BRIGHT_BLACK}[16:44:15]{Colors.RESET}")
    print(f"{Colors.WHITE}✓ Chunk 2 processed in 22.31 seconds with 92 changes{Colors.RESET} {Colors.BRIGHT_BLACK}[16:44:15]{Colors.RESET}")
    
    # Show the final spinner
    sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}✷{Colors.RESET} {Colors.BRIGHT_GREEN}Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    time.sleep(1)
    
    # Clear the spinner line and show completion
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.write(f"{Colors.BRIGHT_GREEN}✓ Transforming novel to gender-neutral{Colors.RESET}")
    sys.stdout.flush()
    print()
    
    print_info("Completed in 5m 42s")
    print_success("Novel transformation completed successfully!")
    print_info("Made 1247 changes")
    print_info("Transformed text saved to output/neutral_pride_and_prejudice.txt")
    print_info("Debug files saved to debug_full")


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
    time.sleep(2)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Feminine transformation complete{Colors.RESET}")
    
    print("\nMasculine transformation spinner:")
    spinner = GenderSpinner("Transforming to masculine", transform_type="masculine")
    spinner.start()
    time.sleep(2)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Masculine transformation complete{Colors.RESET}")
    
    print("\nNeutral transformation spinner:")
    spinner = GenderSpinner("Transforming to neutral", transform_type="neutral")
    spinner.start()
    time.sleep(2)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_GREEN}✓ Neutral transformation complete{Colors.RESET}")
    
    print("\nDemonstrating editing progress bars:")
    
    print("\nEditing progress bar:")
    bar = ProgressBar(total=100, transform_type="neutral")
    for i in range(101):
        bar.update(i)
        time.sleep(0.01)
    bar.finish()
    
    # Choose which demo to run
    demo_choice = input("\nSelect demo (1=Pipeline, 2=Novel Transformation): ")
    
    if demo_choice == "2":
        # Run simulated novel transformation to show new logging format
        print("\n")
        simulate_novel_transformation()
    else:
        # Run simulated pipeline to show basic design
        print("\n")
        simulate_pipeline()
