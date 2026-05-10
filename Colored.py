from colorama import Fore, init

init(autoreset=True)


class Colored:
    @classmethod
    def request(cls, text):
        return f"{Fore.YELLOW}[!]{Fore.RESET} {text}"

    @classmethod
    def success(cls, text):
        return f"{Fore.GREEN}[+]{Fore.RESET} {text}"

    @classmethod
    def error(cls, text):
        return f"{Fore.RED}[-]{Fore.RESET} {text}"

    @classmethod
    def info(cls, text):
        return f"{Fore.CYAN}[*]{Fore.RESET} {text}"
