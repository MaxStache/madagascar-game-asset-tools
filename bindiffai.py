from pathlib import Path
from colorama import Fore, Style, init

init(autoreset=True)


def binary_diff(file_a: str, file_b: str, width: int = 16):
    a = Path(file_a).read_bytes()
    b = Path(file_b).read_bytes()

    max_len = max(len(a), len(b))

    for start in range(0, max_len, width):
        left = a[start:start + width]
        right = b[start:start + width]

        left_str = ""
        right_str = ""

        for i in range(width):
            byte_a = left[i] if i < len(left) else None
            byte_b = right[i] if i < len(right) else None

            if byte_a == byte_b:
                value = f"{byte_a:02X}" if byte_a is not None else "  "
                left_str += value + " "
                right_str += value + " "
            else:
                a_str = f"{byte_a:02X}" if byte_a is not None else "--"
                b_str = f"{byte_b:02X}" if byte_b is not None else "--"

                left_str += Fore.RED + a_str + Style.RESET_ALL + " "
                right_str += Fore.RED + b_str + Style.RESET_ALL + " "

        print(f"{start:08X}  {left_str} | {right_str}")


binary_diff("Levels/KingOfNY/967_ME_Sound_Ambient.ai", "compiled.out.ai")