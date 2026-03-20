#!/usr/bin/env python
"""Open-Javis - Personal Agent System.

A Python-based agent system inspired by OpenFang with:
- Pluggable Channel System (Feishu/Lark)
- Multi-Agent & Subagent Mechanism
- LiteLLM Integration
- Tool System (MCP and Skills)
- Memory System
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.core.config import JavisConfig
from src.core.kernel import Kernel
from src.core.agent import AgentState


console = Console()


@click.group()
@click.version_option("0.1.0")
def cli():
    """Open-Javis - Personal Agent System."""
    pass


@cli.command()
@click.option("--file", "config_file", default="config/javis.toml", help="Path to config file")
def start(config_file: str):
    """Start the Javis daemon."""
    click.echo("Starting Open-Javis...")

    async def run_kernel():
        config = JavisConfig.load(config_file)
        kernel = Kernel(config)

        try:
            await kernel.run()
        except KeyboardInterrupt:
            click.echo("\nShutting down...")
            await kernel.stop()

    asyncio.run(run_kernel())


@cli.command()
def init():
    """Initialize Javis configuration."""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "javis.toml"
    example_file = Path(__file__).parent / "config" / "javis.toml.example"

    if config_file.exists():
        if not click.confirm("Config file already exists. Overwrite?"):
            return

    if example_file.exists():
        import shutil
        shutil.copy(example_file, config_file)
        click.echo(f"Created {config_file}")
        click.echo("\nEdit the config file to set your API keys and preferences.")
    else:
        # Create default config
        config_file.write_text(
            "[llm]\n"
            'provider = "anthropic"\n'
            'model = "claude-sonnet-4-20250514"\n'
            'api_key_env = "ANTHROPIC_API_KEY"\n\n'
            "[channels.feishu]\n"
            "enabled = false\n"
        )
        click.echo(f"Created {config_file}")

    # Create skills directory
    skills_dir = Path("skills")
    skills_dir.mkdir(exist_ok=True)

    # Create example skill
    example_skill = skills_dir / "hello.md"
    if not example_skill.exists():
        example_skill.write_text(
            "---\n"
            "name: hello\n"
            "description: A greeting skill\n"
            "---\n\n"
            "When greeting the user, be friendly and welcoming.\n"
        )
        click.echo(f"Created {example_skill}")

    click.echo("\nInitialization complete!")


@cli.command()
@click.option("--config", "config_file", default="config/javis.toml", help="Path to config file")
def agent_list(config_file: str):
    """List all agents."""
    async def list_agents():
        config = JavisConfig.load(config_file)
        kernel = Kernel(config)
        await kernel.start()

        agents = await kernel.list_agents()

        table = Table(title="Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("State", style="yellow")
        table.add_column("Session", style="blue")

        for agent_info in agents:
            state_color = "red" if agent_info.state == AgentState.TERMINATED.value else "green"
            table.add_row(
                agent_info.id[:8],
                agent_info.name,
                f"[{state_color}]{agent_info.state.value}[/{state_color}]",
                agent_info.session_id[:8],
            )

        console.print(table)
        console.print(f"\nTotal: {len(agents)} agent(s)")

        await kernel.stop()

    asyncio.run(list_agents())


@cli.command()
@click.argument("message")
@click.option("--agent", "agent_id", default=None, help="Agent ID (default: creates new)")
@click.option("--config", "config_file", default="config/javis.toml", help="Path to config file")
def chat(message: str, agent_id: str | None, config_file: str):
    """Send a message to an agent."""
    async def send_message():
        config = JavisConfig.load(config_file)
        kernel = Kernel(config)
        await kernel.start()

        console.print(f"[cyan]You:[/cyan] {message}")

        response = ""
        with console.status("[bold green]Thinking...", spinner="dots") as status:
            async for chunk in kernel.chat(message, agent_id):
                if chunk:
                    response += chunk
                    status.update(f"[bold green]Response:[/bold green] {response[:50]}...")

        console.print(f"[bold green]Assistant:[/bold green] {response}")

        await kernel.stop()

    asyncio.run(send_message())


@cli.command()
@click.argument("agent_id")
@click.option("--config", "config_file", default="config/javis.toml", help="Path to config file")
def agent_kill(agent_id: str, config_file: str):
    """Kill an agent."""
    async def kill_agent():
        config = JavisConfig.load(config_file)
        kernel = Kernel(config)
        await kernel.start()

        success = await kernel.kill_agent(agent_id)

        if success:
            click.echo(f"Agent {agent_id} killed.")
        else:
            click.echo(f"Agent {agent_id} not found.")

        await kernel.stop()

    asyncio.run(kill_agent())


@cli.command()
@click.option("--config", "config_file", default="config/javis.toml", help="Path to config file")
def tools_list(config_file: str):
    """List all available tools."""
    async def list_tools():
        config = JavisConfig.load(config_file)
        kernel = Kernel(config)
        kernel.register_builtin_tools()
        await kernel.start()

        tools = await kernel.list_tools()

        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Description")

        for tool in tools:
            table.add_row(tool.name, tool.category.value, tool.description[:50])

        console.print(table)
        console.print(f"\nTotal: {len(tools)} tool(s)")

        await kernel.stop()

    asyncio.run(list_tools())


@cli.command()
@click.argument("agent_id")
def shell(agent_id: str):
    """Interactive shell for an agent."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    history_file = Path.home() / ".javis_history"
    session = PromptSession(history=FileHistory(str(history_file)))

    async def run_shell():
        config = JavisConfig.load()
        kernel = Kernel(config)
        await kernel.start()

        console.print(f"[bold green]Open-Javis Shell[/bold green]")
        console.print(f"Agent: {agent_id}")
        console.print("Type 'exit' to quit.\n")

        while True:
            try:
                user_input = await session.prompt_async("> ")

                if user_input.lower() in ("exit", "quit"):
                    break

                if not user_input.strip():
                    continue

                console.print(f"[cyan]You:[/cyan] {user_input}")

                response = ""
                with console.status("[bold green]Thinking...", spinner="dots") as status:
                    async for chunk in kernel.chat(user_input, agent_id):
                        if chunk:
                            response += chunk
                            status.update(f"[bold green]Response:[/bold green] {response[:50]}...")

                console.print(f"[bold green]Assistant:[/bold green] {response}\n")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        await kernel.stop()

    try:
        asyncio.run(run_shell())
    except ImportError:
        console.print("[red]Error: prompt_toolkit is required for shell mode.[/red]")
        console.print("Install with: pip install prompt-toolkit")
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    # Handle legacy main() call
    if len(sys.argv) == 1:
        click.echo("Open-Javis - Personal Agent System")
        click.echo("Use 'python main.py --help' for usage information.")
        return

    cli()


if __name__ == "__main__":
    main()
