usage: wc [-l] [-w] [-c] path [path ...]
Print newline, word, and byte counts for each file.
Arguments:
  path  The path to the file.
Options:
  -l    Print the newline counts.
  -w    Print the word counts.
  -c    Print the byte counts.
Examples:
  wc myfile.txt
  wc -l -w another_file.log
  wc -c /etc/skrc
