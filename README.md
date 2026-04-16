# Kronos

A file rediscovery tool.

## Usage

```sh
Usage: kronos [OPTIONS] DIRECTORY

Arguments 
    *                   DIRECTORY       Directory to search [required]

Options 
    -n  --num-files     INTEGER         Number of files to collect [default:10]
    -o  --overwrite                     Overwrite an existing kronos/ directory
        --help                          Show this message and exit
```

## TUI
Once command is entered, the Kronos TUI will appear. This TUI has two panels as described below.

### Information Panel
This panel is made of three columns providing the following information:
- Actions: what actions are available and their respective keybindings
- Files: information on the total number of files found, how many have been reviewed, and how many have been selected for inclusion
- History: the actions taken for the last three files presented

### File Panel
This panel shows the current file, split into the file name and path (from the specified directory in the original command).