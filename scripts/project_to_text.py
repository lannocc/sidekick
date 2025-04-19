
import os


def print_directory_tree(path, indent=""):
    """
    Recursively scans a directory and prints its tree structure.

    Args:
        path (str): The path to the directory to scan.
        indent (str): The indentation string for the current level (used in recursive calls).
    """

    try:
        items = os.listdir(path)
    except OSError as e:
        print(f"{indent}Error accessing {path}: {e}")
        return

    for i, item in enumerate(sorted(items)):
        full_path = os.path.join(path, item)

        # Determine the prefix for the current item based on its position in the list.
        if i == len(items) - 1:  # Last item in the list
            prefix = "└── "
            new_indent = indent + "    " # Increase indentation for the next level
        else:
            prefix = "├── "
            new_indent = indent + "│   " # Increase indentation for the next level, maintaining the vertical line

        suffix = ''
        if os.path.isdir(full_path):
            suffix = '/'

        print(indent + prefix + item + suffix)

        if os.path.isdir(full_path):
            print_directory_tree(full_path, new_indent)


def print_file_contents(path):
    items = os.listdir(path)

    for i, item in enumerate(sorted(items)):
        full_path = os.path.join(path, item)

        if os.path.isdir(full_path):
            print_file_contents(full_path)

        else:
            print(f'FILE {full_path}:')
            hint = 'python' if full_path.endswith('.py') else \
                   'svelte' if full_path.endswith('.svelte') else ''
            print(f'```{hint}')
            with open(full_path, 'r') as file:
                print(file.read())
            print('```')
            print()


if __name__ == "__main__":
    print('Our project is laid out as given in the following file hierarchy:')
    print()
    print('sk/')
    print_directory_tree('sk')
    print()

    print('The contents of each file are given in succession below...')
    print()

    print_file_contents('sk')

