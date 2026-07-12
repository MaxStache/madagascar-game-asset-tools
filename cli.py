# cli.py
import sys
import os
import shutil
from formats.lib.rwConstants import RWSectionType

def testcommand(value):
    try:
        number = int(value, 0)
        sectype = RWSectionType(number)
        print(f"GENERATING FOR: 0x{number:04X} - {sectype.name}")
        path = os.path.join("formats", "sections", f"{sectype.name.replace("rwID_", "")}_{sectype.value:04X}.py")
        print(f"Path: {path}")

        if not os.path.exists(path):
            shutil.copyfile(os.path.join("formats", "sections", "copybase.py"), path)
            print(f"Created new section file: {path}")


    except ValueError as e:
        print(f"Invalid number: {value}")
        print(e)

def main():
    if len(sys.argv) < 3:
        print("Usage: python cli.py secfile 0x<value>")
        return

    command = sys.argv[1]

    if command == "secfile":
        testcommand(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()