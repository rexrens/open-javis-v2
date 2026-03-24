import typer
from pathlib import Path

from src.core.workspace import WorkspaceManager

app = typer.Typer(
    name="javis-bot",
    help="Personal AI Assistant",
    no_args_is_help=True,
)

agent_app = typer.Typer(help="Agent management commands")
workflow_app = typer.Typer(help="Workflow management commands")

app.add_typer(agent_app, name="agent")
app.add_typer(workflow_app, name="workflow")


# Top-level commands
@app.command()
def init():
    """
    Initialize Javis Bot.
    1. create configuration file 
    2. create default workspace
    """
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "javis.toml"
    example_file = Path(__file__).parent / "config" / "javis.toml.example"

    # Overwrite existing config
    if config_file.exists():
        if not typer.confirm("Config file already exists. Overwrite?"):
            return

    # create new config file
    if example_file.exists():
        import shutil
        shutil.copy(example_file, config_file)
        typer.echo(f"Created {config_file}")
        typer.echo("\nEdit the config file to set your API keys and preferences.")
    else:
        # Create default config
        config_file.write_text(
            """
            '[llm]\n'
            'provider = "deepseek"\n'
            'model = "deepseek-chat"\n'
            'api_key_env = "DEEPSEEK_API_KEY"\n\n'
            '[workspace]\n'
            'workspace_dir = "workspace-main"\n\n'
            '[channels.feishu]\n'
            'enabled = false\n'
            """
        )
        typer.echo(f"Created {config_file}")

    # Create workspace.
    typer.echo("\nCreating default main workspace...")
    workspace_dir = Path(__file__).parent/"workspaces"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    wm = WorkspaceManager()
    default_agent_id = "main"

    if wm.exists(default_agent_id):
        if not typer.confirm(f"Default workspace '{default_agent_id}' already exists. Recreate?"):
            typer.echo(f"Using existing workspace: {workspace_dir / default_agent_id}")
            return
        else:
            wm.delete_workspace(default_agent_id)

    # Create default workspace with templates
    agent_id = wm.create_workspace(default_agent_id, copy_templates=True)

    typer.echo(f"Created default workspace:")
    typer.echo("Workspace contains:")
    typer.echo("  - skills/       (for custom skills)")
    typer.echo("  - SOUL.md       (agent personality)")
    typer.echo("  - USER.md       (user preferences)")
    typer.echo("  - TOOLS.md      (tool preferences)")
    typer.echo("  - AGENTS.md     (agent delegation)")
    typer.echo("  - HEARTBEAT.md  (scheduled tasks)")
    typer.echo("  - memory/       (long-term memory)")


@app.command()
def start():
    """Start the daemon"""
    print("Start the daemon")


@app.command()
def status():
    """Check daemon status"""
    print("Check daemon status")


# Agent subcommands
@agent_app.command()
def spawn(manifest: str = typer.Argument(..., help="Path to manifest.toml")):
    """Spawn an agent"""
    print(f"Spawn an agent from {manifest}")


@agent_app.command()
def list():
    """List all agents"""
    print("List all agents")


@agent_app.command()
def chat(id: str = typer.Argument(..., help="Agent ID")):
    """Chat with an agent"""
    print(f"Chat with agent {id}")


@agent_app.command()
def kill(id: str = typer.Argument(..., help="Agent ID")):
    """Kill an agent"""
    print(f"Kill agent {id}")


# Workflow subcommands
@workflow_app.command()
def list():
    """List workflows"""
    print("List workflows")


@workflow_app.command()
def create(file: str = typer.Argument(..., help="Path to workflow JSON file")):
    """Create a workflow"""
    print(f"Create workflow from {file}")


@workflow_app.command()
def run(
    id: str = typer.Argument(..., help="Workflow ID"),
    input: str = typer.Argument(..., help="Input data for the workflow"),
):
    """Run a workflow"""
    print(f"Run workflow {id} with input: {input}")


if __name__ == "__main__":
    app()
