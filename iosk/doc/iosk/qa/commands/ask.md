# /bin/ask.py
**Description:** Interacts with an AI model by sending prompts, optionally attaching file contents or packaging directories. It can also extract markdown code blocks from AI responses and save them to files, and allows specifying different AI models for interaction.
**Usage:**
  - `ask [options] "<prompt>"`
  - `/bin/ask.py [options] "<prompt>"`
  - `echo "<prompt>" | ask [options]`
**Options:**
  - `-q`: Quiet mode, suppresses preliminary or verbose system messages.
  - `-f <file_path>`: Attach the content of a specified file to the prompt. Can be used multiple times.
  - `-p <directory_path>`: Package the content of files within a specified directory and attach them to the prompt. Can be used multiple times.
  - `-e <lang> <output_file>`: Extract the first markdown code block tagged with `<lang>` from the AI's response and save it to `<output_file>`.
  - `-1`: Select model `gemini-2.0-flash-lite`.
  - `-2`: Select model `gemini-2.5-flash` (default).
  - `-3`: Select model `gemini-2.5-pro`.
  - `--help`: Display the help message.
**Example:**
To package a directory and ask the AI to summarize its contents:
  - `mkdir -p /home/beta/test_dir`
  - `echo "This is content A." > /home/beta/test_dir/file_a.txt`
  - `echo "This is content B." > /home/beta/test_dir/file_b.md`
  - `ask -p /home/beta/test_dir "List all files and their contents from the attached package."`
**Output:**
The AI listed `/home/beta/test_dir/file_a.txt` with content "This is content A." and `/home/beta/test_dir/file_b.md` with content "This is content B.".
**Status:** Working.
