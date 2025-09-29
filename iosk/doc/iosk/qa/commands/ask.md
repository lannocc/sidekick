# Test Plan for `ask` command

## Objective
To ensure the `ask` command functions as expected across all its options and integrates correctly with the IOSK environment.

## Test Environment
IOSK live chat system.

## Test Cases

### 1. Basic Functionality
**Description:** Verify the `ask` command can send a simple prompt to the AI and receive a response.
**Steps:**
1. Execute `ask "Hello, what is your name?"`
**Expected Result:** A coherent response from the AI addressing the prompt.

### 2. Help Message
**Description:** Verify the `--help` option displays the correct usage information.
**Steps:**
1. Execute `ask --help`
**Expected Result:** The help message for the `ask` command is displayed, matching the output of `help ask`.

### 3. Quiet Mode (`-q`)
**Description:** Verify the `-q` option suppresses additional output, only showing the AI's final response.
**Steps:**
1. Execute `ask -q "Tell me a short joke."`
**Expected Result:** Only the AI's joke is printed, without any preliminary or verbose system messages.

### 4. Attaching Files (`-f`)
**Description:** Verify that the content of specified files is correctly attached to the prompt.

#### 4.1 Single File Attachment
**Steps:**
1. Create a test file: `echo "This is a test file for attachment." > /home/beta/attach_test.txt`
2. Execute `ask -f /home/beta/attach_test.txt "Summarize the attached file."`
**Expected Result:** The AI summarizes the content of `attach_test.txt`.

#### 4.2 Multiple File Attachments
**Steps:**
1. Create two test files:
   `echo "File one content." > /home/beta/attach_test1.txt`
   `echo "File two content." > /home/beta/attach_test2.txt`
2. Execute `ask -f /home/beta/attach_test1.txt -f /home/beta/attach_test2.txt "Compare the content of the two attached files."`
**Expected Result:** The AI compares the content of `attach_test1.txt` and `attach_test2.txt`.

### 5. Packaging Directories (`-p`)
**Description:** Verify that the content of files within specified directories is correctly packaged and attached to the prompt.

#### 5.1 Single Directory Attachment
**Steps:**
1. Create a test directory and files:
   `mkdir -p /home/beta/package_test_dir`
   `echo "Content of file_a." > /home/beta/package_test_dir/file_a.txt`
   `echo "Content of file_b." > /home/beta/package_test_dir/file_b.md`
2. Execute `ask -p /home/beta/package_test_dir "List all files and their contents from the attached package."`
**Expected Result:** The AI lists `file_a.txt` and `file_b.md` with their respective contents.

#### 5.2 Multiple Directory Attachments
**Steps:**
1. Create two test directories and files:
   `mkdir -p /home/beta/package_test_dir1`
   `echo "Content A." > /home/beta/package_test_dir1/a.txt`
   `mkdir -p /home/beta/package_test_dir2`
   `echo "Content B." > /home/beta/package_test_dir2/b.txt`
2. Execute `ask -p /home/beta/package_test_dir1 -p /home/beta/package_test_dir2 "Describe the overall theme of the attached packages."`
**Expected Result:** The AI provides a description based on the combined content of both directories.

### 6. Extracting Code Blocks (`-e`)
**Description:** Verify that markdown code blocks can be extracted and saved to a file.

#### 6.1 Python Code Extraction
**Steps:**
1. Execute `ask -e python /home/beta/extracted_code.py "Write a simple Python function that adds two numbers."`
**Expected Result:** A file named `extracted_code.py` is created in `/home/beta/` containing the Python function in a markdown code block.

#### 6.2 Shell Script Extraction
**Steps:**
1. Execute `ask -e sh /home/beta/extracted_script.sh "Write a simple shell script that prints 'Hello, IOSK'."`
**Expected Result:** A file named `extracted_script.sh` is created in `/home/beta/` containing the shell script in a markdown code block.

### 7. Specifying Models (`-1`, `-2`, `-3`)
**Description:** Verify that different AI models can be selected.
**Note:** It may be difficult to discern if the correct model was used without system logs, but the command should execute without error.

#### 7.1 Model 1 (`-1`)
**Steps:**
1. Execute `ask -1 "What is your current model?"`
**Expected Result:** The AI responds, ideally indicating it is using `gemini-2.0-flash-lite` or a similar response consistent with the selected model.

#### 7.2 Model 2 (`-2`, Default)
**Steps:**
1. Execute `ask -2 "What is your current model?"`
**Expected Result:** The AI responds, ideally indicating it is using `gemini-2.5-flash` or a similar response consistent with the selected model.
2. Execute `ask "What is your current model?"` (without specifying model option)
**Expected Result:** The AI responds, ideally indicating it is using `gemini-2.5-flash` (default model).

#### 7.3 Model 3 (`-3`)
**Steps:**
1. Execute `ask -3 "What is your current model?"`
**Expected Result:** The AI responds, ideally indicating it is using `gemini-2.5-pro` or a similar response consistent with the selected model.

### 8. Reading Prompt from Standard Input
**Description:** Verify that the prompt can be read from stdin if not provided as an argument.
**Steps:**
1. Execute `echo "Generate a simple haiku about the moon." | ask`
**Expected Result:** The AI generates a haiku about the moon.

### 9. Combined Options
**Description:** Verify that multiple options can be used together.
**Steps:**
1. Create a test file: `echo "Test content for combined options." > /home/beta/combined_test.txt`
2. Execute `ask -q -f /home/beta/combined_test.txt -e txt /home/beta/combined_output.txt "Summarize the attached file in one sentence."`
**Expected Result:** A file `combined_output.txt` is created containing a one-sentence summary of `combined_test.txt`, and only the summary (without verbose output) is printed to the console.

## Cleanup
**Description:** Remove all test files and directories created during the testing process.
**Steps:**
1. Execute `rm /home/beta/attach_test.txt`
2. Execute `rm /home/beta/attach_test1.txt /home/beta/attach_test2.txt`
3. Execute `rm -r /home/beta/package_test_dir`
4. Execute `rm -r /home/beta/package_test_dir1 /home/beta/package_test_dir2`
5. Execute `rm /home/beta/extracted_code.py`
6. Execute `rm /home/beta/extracted_script.sh`
7. Execute `rm /home/beta/combined_test.txt /home/beta/combined_output.txt`
**Expected Result:** All temporary files and directories are successfully removed.

