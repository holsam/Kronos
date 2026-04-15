# Import external dependencies
import random, shutil, typer
from pathlib import Path
from typing import Annotated

# Initialise typer instance
app = typer.Typer()

# collect_files
# Returns all files under the specified directory
def collect_files(base_dir: Path) -> list[Path]:
    '''Recursively collect all files under base_dir.'''
    return [p for p in base_dir.rglob('*') if p.is_file()]

# Define command
@app.command()
def main(
    # Add argument directory: which directory to search
    directory: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, dir_okay=True)
    ],
    # Add option -n/--num-files: how many files to end up with (default = 10)
    n: Annotated[
        int,
        typer.Option('-n', '--num-files', help='Number of files to collect'),
    ] = 10,
    # Add option -o/--overwrite: allows overwriting existing kronos directory
    overwrite: Annotated[
        bool,
        typer.Option('-o', '--overwrite', help = 'Overwrite an existing kronos directory')
    ] = False,
):
    # Define path to kronos directory
    kronos_dir = Path.cwd() / 'kronos'

    # Handle existing kronos directory
    if kronos_dir.exists():
        # If directory exists:
        if overwrite:
            # If overwrite option was provided, remove old directory
            shutil.rmtree(kronos_dir)
        else:
            # Otherwise, print message
            typer.echo('kronos/ already exists. Use --overwrite to replace it.')
            # Exit
            raise typer.Exit(code=1)

    # Make kronos directory
    kronos_dir.mkdir(parents=True, exist_ok=True)

    # Collect all files from specified directory
    files = collect_files(directory)

    # If directory does not contain any files
    if not files:
        # Print a message
        typer.echo('No files found.')
        # Exit
        raise typer.Exit(code=1)

    # Shuffle the files
    random.shuffle(files)

    # Initilaise count and seen variables
    selected_count = 0
    seen = set()

    # Loop through each file
    for file in files:
        # If the number of selected files is equal or greater than specified number
        if selected_count >= n:
            # Break out of loop
            break
        
        # If the file has been seen already
        if file in seen:
            # Skip to next file
            continue

        # Add file to seen
        seen.add(file)

        # Print nanme of file to terminal
        typer.echo(f'\nFile: {file}')
        
        # Ask whether to include file
        choice = typer.prompt('Include this file? [y/n]', default='n').lower()

        # If file should be included
        if choice == 'y':
            # Define the destination
            dest = kronos_dir / file.name

            # If another file exists with same name
            counter = 1
            while dest.exists():
                # Add counter to avoid collisions
                dest = kronos_dir / f'{file.stem}_{counter}{file.suffix}'
                counter += 1

            # Copy file to kronos folder
            shutil.copy2(file, dest)
            
            # Increase number of selected files
            selected_count += 1

            # Print message
            typer.echo(f'Copied to {dest}')

    # Print final message
    typer.echo(f'\nDone. Collected {selected_count} file(s).')

# Entrypoint
if __name__ == '__main__':
    app()