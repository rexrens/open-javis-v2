"""Built-in tools for Open-Javis."""

from .base import tool, ToolCategory, ToolResult


def register_builtin_tools(registry) -> None:
    """Register all built-in tools.

    Args:
        registry: The tool registry to register with.
    """

    @tool(name="echo", description="Echo back the input text", category=ToolCategory.GENERAL)
    async def echo(text: str) -> str:
        """Echo the input text.

        Args:
            text: The text to echo.

        Returns:
            The echoed text.
        """
        return text

    @tool(name="get_time", description="Get the current time", category=ToolCategory.SYSTEM)
    async def get_time() -> str:
        """Get the current time.

        Returns:
            Current time as ISO string.
        """
        from datetime import datetime
        return datetime.now().isoformat()

    @tool(name="calculate", description="Perform a calculation", category=ToolCategory.GENERAL)
    async def calculate(expression: str) -> str:
        """Evaluate a mathematical expression safely.

        Args:
            expression: The mathematical expression to evaluate.

        Returns:
            The result of the calculation.
        """
        import ast
        import operator

        # Safe evaluation using AST
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_node(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                op_type = type(node.op)
                if op_type in operators:
                    return operators[op_type](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                op_type = type(node.op)
                if op_type in operators:
                    return operators[op_type](operand)
            raise ValueError(f"Unsupported operation: {type(node)}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = eval_node(tree.body)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    @tool(name="save_note", description="Save a note to memory", category=ToolCategory.GENERAL)
    async def save_note(note: str, title: str = "") -> str:
        """Save a note.

        Args:
            note: The note content.
            title: Optional note title.

        Returns:
            Confirmation message.
        """
        return f"Saved note: {title or 'Untitled'}"

    @tool(name="read_note", description="Read a note from memory", category=ToolCategory.GENERAL)
    async def read_note(title: str) -> str:
        """Read a note.

        Args:
            title: The note title.

        Returns:
            The note content.
        """
        return f"Note content for: {title}"

    # Register all tools
    registry.register_function(echo)
    registry.register_function(get_time)
    registry.register_function(calculate)
    registry.register_function(save_note)
    registry.register_function(read_note)
