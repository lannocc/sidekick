usage: patch [file] [patch_file]
Apply a patch to a file.
Arguments:
  [file]       The file to be patched. If omitted, input is read from stdin.
  [patch_file] The file containing the patch. If omitted, input is read from stdin.
Examples:
  patch my_file.txt my_patch.diff
  cat my_patch.diff | patch my_file.txt
  patch < my_patch.diff > my_patched_file.txt
  cat my_file.txt | patch - my_patch.diff > my_patched_file.txt
