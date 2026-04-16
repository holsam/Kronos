# Import external dependencies
import random, shutil, time, typer
from pathlib import Path
from rich import print
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container
from textual.reactive import reactive
from typing import Annotated

# Initialise typer instance
cli = typer.Typer()

# collect_files
# Returns list of Paths under the specified directory
def collect_files(base_dir: Path) -> list[Path]:
    '''Recursively collect all files under base_dir.'''
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

# Define Textual app
class Kronos(App):
    # Define style
    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        padding: 1 2;
    }

    .panel {
        border: round $accent;
        padding: 1;
        margin-bottom: 1;
    }
    """
    # Define key bindings
    BINDINGS = [
        ("y", "accept", "Include"),
        ("n", "skip", "Skip"),
        ("q", "quit", "Quit"),
    ]
    index = reactive(0)
    selected = reactive(0)
    reviewed = reactive(0)
    last_action = reactive("Starting...")
    
    def __init__(self, files, n, kronos_dir):
        super().__init__()
        self.files = files
        self.n = n
        self.kronos_dir = kronos_dir

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            self.file_panel = Static(classes="panel")
            self.stats_panel = Static(classes="panel")
            self.help_panel = Static(
                "[b]y[/b]=include  [b]n[/b]=skip  [b]q[/b]=quit",
                classes="panel",
            )
            yield self.file_panel
            yield self.stats_panel
            yield self.help_panel
        yield Footer()

    def on_mount(self):
        self.refresh_ui()

    def refresh_ui(self):
        if self.index >= len(self.files):
            self.exit()
            return

        file = self.files[self.index]

        self.file_panel.update(f"[bold cyan]{file}[/bold cyan]")

        self.stats_panel.update(
            f"[green]Selected:[/green] {self.selected}/{self.n}\n"
            f"[yellow]Reviewed:[/yellow] {self.reviewed}/{len(self.files)}\n"
            f"[magenta]Last:[/magenta] {self.last_action}"
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
        # Update last_action
        self.last_action = f"Added: {file.name}"
        if self.selected >= self.n:
            self.exit()
        else:
            self.next_file()
    # Define action on keybinding n
    def action_skip(self):
        file = self.files[self.index]
        # Increase number of reviewed files
        self.reviewed += 1
        # Update last_action
        self.last_action = f"Skipped: {file.name}"
        self.next_file()
    # Define action on keybinding q
    def action_quit(self):
        # Update last_action
        self.last_action = "Quit"
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

    app = Kronos(files, n, kronos_dir)
    app.run()
            
    # Print final message
    print(f'\n[bold green]Done.[/bold green]')

# Entrypoint
if __name__ == '__main__':
    cli()