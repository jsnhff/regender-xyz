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
    
    def __init__(self, message: str = "Processing", delay: float = 0.1, transform_type: str = "feminine"):
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
        
        # Set colors and symbols based on transformation type
        if transform_type == "feminine":
            self.color_from = Colors.BRIGHT_BLUE
            self.color_to = Colors.BRIGHT_MAGENTA
            self.symbol_from = "♂"  # Male
            self.symbol_to = "♀"    # Female
        elif transform_type == "masculine":
            self.color_from = Colors.BRIGHT_MAGENTA
            self.color_to = Colors.BRIGHT_BLUE
            self.symbol_from = "♀"  # Female
            self.symbol_to = "♂"    # Male
        else:  # neutral
            self.color_from = Colors.BRIGHT_CYAN
            self.color_to = Colors.BRIGHT_YELLOW
            self.symbol_from = "⚥"  # Male/Female
            self.symbol_to = "⚧"    # Transgender
        
        # Loading wheel characters
        self.wheel_chars = ["◐", "◓", "◑", "◒"]
        # Arrow types for different animation frames
        self.arrows = ["→", "⇒", "⟹", "⟶", "⟾"]
    
    def _spin(self):
        """Internal method to animate the spinner."""
        frames = []
        
        # Create frames with a loading wheel and gender symbols
        for i, wheel in enumerate(self.wheel_chars):
            # Alternate arrow directions for visual interest
            arrow = self.arrows[i % len(self.arrows)]
            
            # Frame 1: Symbol From → Symbol To with wheel at start
            frames.append(f"{Colors.BRIGHT_WHITE}{wheel} {Colors.BOLD}{self.color_from}{self.symbol_from} {arrow} {self.color_to}{self.symbol_to}{Colors.RESET}")
            
            # Frame 2: Symbol From → Symbol To with wheel in middle
            frames.append(f"{self.color_from}{self.symbol_from} {Colors.BRIGHT_WHITE}{wheel} {self.color_to}{self.symbol_to}{Colors.RESET}")
            
            # Frame 3: Symbol From → Symbol To with wheel at end
            frames.append(f"{self.color_from}{self.symbol_from} {arrow} {Colors.BRIGHT_WHITE}{wheel} {self.color_to}{self.symbol_to}{Colors.RESET}")
            
            # Frame 4: Symbol From → Symbol To with wheel after
            frames.append(f"{self.color_from}{self.symbol_from} {arrow} {self.color_to}{self.symbol_to} {Colors.BRIGHT_WHITE}{wheel}{Colors.RESET}")
        
        # Create frames with pulsing symbols and arrows
        for i in range(3):
            # Pulsing effect with different arrow styles
            arrow = self.arrows[i % len(self.arrows)]
            
            # Pulsing from symbol
            frames.append(f"{Colors.BOLD}{self.color_from}{self.symbol_from}{Colors.RESET} {arrow} {self.color_to}{self.symbol_to}")
            
            # Pulsing arrow
            frames.append(f"{self.color_from}{self.symbol_from} {Colors.BOLD}{Colors.WHITE}{arrow}{Colors.RESET} {self.color_to}{self.symbol_to}")
            
            # Pulsing to symbol
            frames.append(f"{self.color_from}{self.symbol_from} {arrow} {Colors.BOLD}{self.color_to}{self.symbol_to}{Colors.RESET}")
        
        # Create special transformation frames with loading wheel
        for i, wheel in enumerate(self.wheel_chars):
            if self.transform_type == "feminine":
                frames.append(f"{self.color_from}{self.symbol_from} {Colors.BRIGHT_WHITE}{wheel} {self.color_to}{self.symbol_to} {Colors.BRIGHT_BLUE}M{Colors.RESET}→{Colors.BRIGHT_MAGENTA}F{Colors.RESET}")
            elif self.transform_type == "masculine":
                frames.append(f"{self.color_from}{self.symbol_from} {Colors.BRIGHT_WHITE}{wheel} {self.color_to}{self.symbol_to} {Colors.BRIGHT_MAGENTA}F{Colors.RESET}→{Colors.BRIGHT_BLUE}M{Colors.RESET}")
            else:  # neutral
                frames.append(f"{self.color_from}{self.symbol_from} {Colors.BRIGHT_WHITE}{wheel} {self.color_to}{self.symbol_to} {Colors.BRIGHT_CYAN}N{Colors.RESET}⟺{Colors.BRIGHT_YELLOW}X{Colors.RESET}")
        
        write = sys.stdout.write
        flush = sys.stdout.flush
        
        while self.running:
            for frame in frames:
                if not self.running:
                    break
                # Make the spinner more noticeable with brackets and padding
                write(f"\r{self.message} [{Colors.BOLD}{frame}{Colors.RESET}] ")
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
        if self.spinner_thread is not None:
            self.spinner_thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        sys.stdout.flush()


class ProgressBar:
    """Animated progress bar with gender transformation theme."""
    
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
        self.progress = 0
        
        # Set colors and patterns based on transformation type
        if transform_type == "feminine":
            self.color_from = Colors.BRIGHT_BLUE
            self.color_to = Colors.BRIGHT_MAGENTA
            self.fill_chars = ['◯', '◎', '●', '◆', '◈', '◉', '♀']
        elif transform_type == "masculine":
            self.color_from = Colors.BRIGHT_MAGENTA
            self.color_to = Colors.BRIGHT_BLUE
            self.fill_chars = ['◯', '◎', '●', '◆', '◈', '◉', '♂']
        else:  # neutral
            self.color_from = Colors.BRIGHT_CYAN
            self.color_to = Colors.BRIGHT_YELLOW
            self.fill_chars = ['◯', '◎', '●', '◆', '◈', '◉', '⚧']
        
        # Empty bar character
        self.empty_char = '·'
    
    def update(self, progress: int):
        """Update the progress bar.
        
        Args:
            progress: Current progress (0 to total)
        """
        self.progress = min(progress, self.total)
        percent = self.progress / self.total
        filled_width = int(self.width * percent)
        
        # Create textural effect with different characters
        bar = ""
        for i in range(self.width):
            if i < filled_width:
                # Create a textural pattern using different characters
                char_index = min(int((i / filled_width) * len(self.fill_chars)), len(self.fill_chars) - 1)
                
                # Color gradient from color_from to color_to
                if i < filled_width // 3:
                    bar += f"{self.color_from}{self.fill_chars[char_index]}"
                elif i < filled_width * 2 // 3:
                    # Mix colors in the middle for a richer texture
                    if i % 2 == 0:
                        bar += f"{self.color_from}{self.fill_chars[char_index]}"
                    else:
                        bar += f"{self.color_to}{self.fill_chars[char_index]}"
                else:
                    bar += f"{self.color_to}{self.fill_chars[char_index]}"
            else:
                bar += f"{Colors.BRIGHT_BLACK}{self.empty_char}"
        
        # Print the progress bar with percentage
        sys.stdout.write(f"\r{Colors.RESET}[{bar}{Colors.RESET}] {int(percent * 100)}%")
        sys.stdout.flush()
    
    def finish(self):
        """Complete the progress bar."""
        self.update(self.total)
        sys.stdout.write("\n")
        sys.stdout.flush()


def print_fancy_banner():
    """Print a fancy banner for the application."""
    banner = f"""
{Colors.CYAN}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  {Colors.BRIGHT_YELLOW}⚡ {Colors.BRIGHT_MAGENTA}r{Colors.BRIGHT_CYAN}e{Colors.BRIGHT_GREEN}g{Colors.BRIGHT_BLUE}e{Colors.BRIGHT_RED}n{Colors.BRIGHT_YELLOW}d{Colors.BRIGHT_MAGENTA}e{Colors.BRIGHT_CYAN}r{Colors.BRIGHT_GREEN}-{Colors.BRIGHT_BLUE}x{Colors.BRIGHT_RED}y{Colors.BRIGHT_YELLOW}z {Colors.BRIGHT_YELLOW}⚡{Colors.CYAN}                          
┃  {Colors.BRIGHT_WHITE}~ transforming gender in literature ~         
┃  {Colors.BRIGHT_CYAN}[ Version 0.3.0 ]                          
┃                                               
┃  {Colors.BRIGHT_MAGENTA}✧ {Colors.WHITE}character analysis {Colors.BRIGHT_MAGENTA}✧ {Colors.WHITE}gender transformation {Colors.BRIGHT_MAGENTA}✧           
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯{Colors.RESET}
"""
    print(banner)


def print_section_header(title: str):
    """Print a stylish section header.
    
    Args:
        title: Section title
    """
    width = 55
    padding = max(0, width - len(title) - 4)  # 4 accounts for spacing and borders
    
    print(f"\n{Colors.BRIGHT_CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{Colors.RESET}")
    print(f"{Colors.BRIGHT_CYAN}┃{Colors.RESET} {Colors.BOLD}{Colors.WHITE}{title}{Colors.RESET}{' ' * padding} {Colors.BRIGHT_CYAN}┃{Colors.RESET}")
    print(f"{Colors.BRIGHT_CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{Colors.RESET}")


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
        return result
    finally:
        spinner.stop()


if __name__ == "__main__":
    # Demo
    print_fancy_banner()
    print_section_header("Demo of CLI Visuals")
    
    print_info("This is an info message")
    print_success("This is a success message")
    print_warning("This is a warning message")
    print_error("This is an error message")
    
    print("\nDemonstrating spinners:")
    
    print(f"\n{Colors.BOLD}Feminine transformation spinner:{Colors.RESET}")
    spinner = GenderSpinner("Transforming to feminine", transform_type="feminine")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_MAGENTA}Feminine transformation complete!{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Masculine transformation spinner:{Colors.RESET}")
    spinner = GenderSpinner("Transforming to masculine", transform_type="masculine")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_BLUE}Masculine transformation complete!{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Neutral transformation spinner:{Colors.RESET}")
    spinner = GenderSpinner("Transforming to neutral", transform_type="neutral")
    spinner.start()
    time.sleep(5)
    spinner.stop()
    print(f"\n{Colors.BRIGHT_YELLOW}Neutral transformation complete!{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Demonstrating textural progress bars:{Colors.RESET}")
    
    print(f"\n{Colors.BRIGHT_MAGENTA}Feminine progress bar:{Colors.RESET}")
    bar = ProgressBar(total=100, transform_type="feminine")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
    
    print(f"\n{Colors.BRIGHT_BLUE}Masculine progress bar:{Colors.RESET}")
    bar = ProgressBar(total=100, transform_type="masculine")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
    
    print(f"\n{Colors.BRIGHT_YELLOW}Neutral progress bar:{Colors.RESET}")
    bar = ProgressBar(total=100, transform_type="neutral")
    for i in range(101):
        bar.update(i)
        time.sleep(0.03)
    bar.finish()
