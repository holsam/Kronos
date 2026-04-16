# Import external dependencies
import random, shutil, time, typer
from pathlib import Path
from pyfiglet import Figlet
from rich import print
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static
from textual.containers import Horizontal, Container
from textual.reactive import reactive
from typing import Annotated

# Initialise typer instance
cli = typer.Typer()

# collect_files
# Returns list of Paths under the specified directory
def collect_files(base_dir: Path) -> list[Path]:
    '''Recursively collect all files under base_dir'''
    return [p for p in base_dir.rglob('*') if p.is_file()]

# score_file
# Returns a float score derived from file age and size
def score_file(file: Path) -> float:
    '''Scores files by age and size, increasing score for older and larger files'''
    try:
        # Get file information
        stat = file.stat()
        # Extract last modified time for file and convert to days from current time
        age_days = (time.time() - stat.st_mtime) / 86400
        # Get size of file and convert to megabytes
        size_mb = stat.st_size / (1024*1024)
        # Calculate score as 0.7*age + 0.3*size
        score = (0.7 * age_days)+(0.3 * size_mb)
        # Return score
        return score
    # If exception raised:
    except Exception:
        # Return 0
        return 0

# smart_shuffle
# Returns list of Paths after sorting by score and shuffling
def smart_shuffle(files: list[Path]) -> list[Path]:
    '''Sorts files by score and shuffles to maintain randomness'''
    # Score all files
    scored = [(score_file(file), file) for file in files]
    # Reverse order so highest scores are first
    scored.sort(reverse=True)
    # Take the top 50% scored files and shuffle
    top = [f for _, f in scored[: len(scored) // 2]]
    random.shuffle(top)
    # Take the bottom 50% scored files and shuffle
    bottom = [f for _, f in scored[len(scored) // 2 :]]
    random.shuffle(bottom)
    # Return combined list after shuffling
    return top + bottom

class KronosHeader(Static):
    def compose(self) -> ComposeResult:
        f = Figlet(font='chunky')
        yield Static(f'{f.renderText('KRONOS')}', classes='title')

# Define Textual app
class Kronos(App):
    # Define style using CSS
    CSS = '''
    Screen {
        layout: vertical;
    }
    .title {
        content-align: center middle;
        color: green;
    }
    #main {
        padding: 0 1;
    }
    .panel {
        border: round green;
        padding: 0 1;
        height: auto;
    }
    #info_panel {
        border: round green;
        padding: 0 1;
        height: auto;
    }

    #actions, #files {
        width: 1fr;
    }

    #history {
        width: 2fr;
    }

    #actions {
        content-align: left middle;
    }

    #files {
        content-align: left middle;
    }

    #history {
        content-align: left middle;
        text-wrap: nowrap;
    }
    '''
    # Define key bindings
    BINDINGS = [
        ('y', 'accept', 'Include File'),
        ('n', 'skip', 'Skip File'),
        ('q', 'quit', 'Quit Kronos'),
    ]
    index = reactive(0)
    selected = reactive(0)
    reviewed = reactive(0)
    history = ['','','']

    def __init__(self, files, n, kronos_dir, directory):
        super().__init__()
        self.files = files
        self.n = n
        self.kronos_dir = kronos_dir
        self.base_dir = directory

    def compose(self) -> ComposeResult:
        yield KronosHeader()
        with Container(id='main'):
            self.info_panel = Horizontal(
                Static(id="actions"),
                Static(id="files"),
                Static(id="history"),
                id="info_panel",
            )
            self.file_panel = Static(classes='panel')
            yield self.info_panel
            yield self.file_panel
        # yield Footer()

    def on_mount(self):
        self.refresh_ui()

    # Define helper function to format command history
    def format_history_item(self, text: str, max_width: int = 30) -> str:
        if len(text) <= max_width:
            return text
        # Split into action + filename
        if text == '':
            return text
        if ': ' in text:
            action, filename = text.split(': ', 1)
        else:
            return text[:max_width - 3] + '...'
        # Extract extension
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            ext = '.' + ext
        else:
            name, ext = filename, ''
        # Keep start of filename
        available = max_width - len(action) - len(ext) - 6  # buffer for ': ...'
        if available <= 0:
            return f'{action}: [dim]...[/dim]{ext}'
        return f'{action}: {name[:available]}[dim]...[/dim]{ext}'

    def refresh_ui(self):
        # Check files included doesn't equal or exceed the desired number
        if self.index >= len(self.files):
            self.exit()
            return

        # Refresh actions column of info panel
        self.query_one('#actions', Static).update(
            f'[bold]ACTIONS[/bold]\n[italic][bold]y[/bold] = include file\n[bold]n[/bold] = skip file\n[bold]q[/bold] = quit Kronos[/italic]'
        )

        # Refresh files column of info panel
        self.query_one('#files', Static).update(
            f'[bold]FILES[/bold]\n[italic][bold]Found:[/bold] {len(self.files)}\n[bold]Reviewed:[/bold] {self.reviewed}\n[bold]Included:[/bold] {self.selected}/{self.n}[/italic]'
        )

        # Refresh history column of info panel
        history_items = self.history[-3:] if hasattr(self, 'history') else []
        terminal_width = (self.query_one('#history').size.width) - 4
        formatted = [self.format_history_item(item, terminal_width) for item in history_items]
        self.query_one('#history', Static).update(f'[bold]HISTORY[/bold]\n[italic]{'\n'.join(formatted)}[/italic]')
        
        # Update file 
        file = self.files[self.index]

        # Refresh file panel
        cur_dir = self.kronos_dir.parent # get current directory
        rel_parent = file.relative_to(self.base_dir).parent # get parent of files relative to current directory subdirectory/ies file is from
        subdir = '/' if rel_parent == "." else f'{rel_parent}/'

        self.file_panel.update(
            f'[bold]CURRENT FILE[/bold]\n[italic]Subdirectory: [cyan]{subdir}[/cyan]\nFile: [cyan]{file.name}[/cyan]'
        )

    def next_file(self):
        self.index += 1
        self.refresh_ui()

    # Define action on keybinding y
    def action_accept(self):
        if self.selected >= self.n:
            self.exit()
            return
        file = self.files[self.index]
        # Define the destination
        dest = self.kronos_dir / file.name
        # If another file exists with same name
        counter = 1
        while dest.exists():
            # Add counter to avoid name collisions
            dest = self.kronos_dir / f"{file.stem}_{counter}{file.suffix}"
            counter += 1
        # Copy file to kronos directory
        shutil.copy2(file, dest)
        # Increase number of selected files
        self.selected += 1
        # Increase number of reviewed files
        self.reviewed += 1
        # Update history
        self.history.append(f'Included: {file.name}')
        if self.selected >= self.n:
            self.exit()
        else:
            self.next_file()
    # Define action on keybinding n
    def action_skip(self):
        file = self.files[self.index]
        # Increase number of reviewed files
        self.reviewed += 1
        # Update history
        self.history.append(f'Skipped: {file.name}')
        self.next_file()
    # Define action on keybinding q
    def action_quit(self):
        # Update history
        self.history.append(f'Quit Kronos')
        self.exit()


# Define command
@cli.command()
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
        # Check if empty:
        if not collect_files(kronos_dir):
            # If so, print message
            print('[yellow]kronos/ already exists but is empty - continuing...[/yellow]')
        else:
            if overwrite:
                # If overwrite option was provided, remove old directory
                shutil.rmtree(kronos_dir)
            else:
                # Otherwise, print message
                print('[red]kronos/ already exists. Use --overwrite to replace it.[/red]')
                # Exit
                raise typer.Exit(code=1)

    # Make kronos directory
    kronos_dir.mkdir(parents=True, exist_ok=True)

    # Collect all files from specified directory
    files = collect_files(directory)

    # If directory does not contain any files
    if not files:
        # Print a message
        print('[red]No files found.[/red]')
        # Exit
        raise typer.Exit(code=1)

    # Shuffle the files
    files = smart_shuffle(files)

    app = Kronos(files, n, kronos_dir, directory)
    app.run()

# Entrypoint
if __name__ == '__main__':
    cli()