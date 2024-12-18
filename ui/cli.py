"""Command-line interface components."""

from colorama import Fore, Style
from typing import Tuple, Optional

from config.constants import GENDER_CATEGORIES
from utils.api_client import get_gpt_response

class CLI:
    @staticmethod
    def print_banner() -> None:
        """Print application banner."""
        banner = f"""
{Fore.CYAN}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  {Fore.WHITE}⚡ regender.xyz ⚡{Fore.CYAN}                      
┃  {Fore.YELLOW}transforming gender in open source books{Fore.CYAN}     
┃  {Fore.MAGENTA}[ Version 1.0.0 ]{Fore.CYAN}                      
┃                                           
┃  {Fore.WHITE}✧{Fore.BLUE} Gender Analysis {Fore.WHITE}✧{Fore.GREEN} Name Processing {Fore.WHITE}✧{Fore.CYAN}       
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
"""
        print(banner)

    @staticmethod
    def print_status(message: str, status_type: str = "info") -> None:
        """Print formatted status message."""
        symbols = {
            "info": f"{Fore.BLUE}ℹ{Style.RESET_ALL}",
            "success": f"{Fore.GREEN}✓{Style.RESET_ALL}",
            "warning": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
            "error": f"{Fore.RED}✗{Style.RESET_ALL}"
        }
        print(f" {symbols.get(status_type, symbols['info'])} {message}")

    def get_gender_choice(self, character: str, current_gender: str) -> Tuple[str, str]:
        """Enhanced gender selection interface."""
        print(f"\n{Fore.CYAN}╭─ Character: {Fore.WHITE}{character} {Fore.YELLOW}({current_gender}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}├─ Select Gender:{Style.RESET_ALL}")
        
        options = [
            f"{Fore.GREEN}1{Style.RESET_ALL} Male",
            f"{Fore.MAGENTA}2{Style.RESET_ALL} Female",
            f"{Fore.BLUE}3{Style.RESET_ALL} Non-binary",
            f"{Fore.YELLOW}↵{Style.RESET_ALL} Keep current"
        ]
        print(f"{Fore.CYAN}│  {Style.RESET_ALL}" + " | ".join(options))
        print(f"{Fore.CYAN}╰─{Style.RESET_ALL}", end=" ")
        
        choice = input().strip()
        return self._process_gender_choice(choice, character, current_gender)

    def _process_gender_choice(self, choice: str, character: str, current_gender: str) -> Tuple[str, str]:
        """Process user's gender choice and handle name changes."""
        if not choice:
            return current_gender, character
            
        try:
            choice_idx = int(choice) - 1
            category_keys = [k for k in GENDER_CATEGORIES.keys() if k != 'UNK']
            if 0 <= choice_idx < len(category_keys):
                selected_key = category_keys[choice_idx]
                selected_gender = GENDER_CATEGORIES[selected_key]['label']
                
                if selected_gender.lower() != current_gender.lower():
                    return self._handle_name_change(character, selected_gender)
                
                return selected_gender, character
        except ValueError:
            pass
            
        return current_gender, character

    def _handle_name_change(self, character: str, new_gender: str) -> Tuple[str, str]:
        """Handle character name changes when gender changes."""
        prompt = (
            f"Suggest three {new_gender.lower()} versions of the name '{character}'. "
            "Provide only the names separated by commas, no explanation."
        )
        suggested_names = get_gpt_response(prompt).split(',')
        suggested_names = [name.strip() for name in suggested_names]
        
        print(f"\n{Fore.CYAN}╭─ Name Suggestions:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│  {Style.RESET_ALL}" + 
              " | ".join(f"{Fore.YELLOW}{name}{Style.RESET_ALL}" for name in suggested_names))
        print(f"{Fore.CYAN}╰─{Style.RESET_ALL}", end=" ")
        
        new_name = input("Enter name (↵ to keep current): ").strip()
        return new_gender, new_name if new_name else character