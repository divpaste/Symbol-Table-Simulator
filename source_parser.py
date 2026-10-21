from pycparser import c_parser, c_ast
from symbol_table import Symbol, SymbolTableManager
from typing import Tuple, List, Optional, Any

class SourceParser:
    def __init__(self, table_size: int = 7):
        self.parser = c_parser.CParser()
        self.symbol_table = SymbolTableManager(table_size=table_size)
        self.errors: List[str] = []

    def get_initial_value(self, node: Optional[c_ast.Node]) -> Optional[Any]:
        if node is None:
            return None

        if isinstance(node, c_ast.Constant):
            value = node.value
            if node.type == "int":
                try:
                    return int(value, 0)
                except ValueError:
                    return value
            if node.type in ("float", "double"):
                try:
                    return float(value)
                except ValueError:
                    return value
            if node.type == "char":
                return value.strip("'")
            if node.type == "string":
                return value.strip('"')

        if isinstance(node, c_ast.UnaryOp):
            inner = self.get_initial_value(node.expr)
            return f"{node.op}{inner}" if inner is not None else None

        return None

    def get_data_type(self, node: Any) -> str:
        while isinstance(node, (c_ast.Decl, c_ast.TypeDecl)):
            node = node.type

        if isinstance(node, c_ast.IdentifierType):
            return " ".join(node.names)

        if isinstance(node, c_ast.PtrDecl):
            return self.get_data_type(node.type) + "*"

        if isinstance(node, c_ast.ArrayDecl):
            dim = node.dim.value if hasattr(node, "dim") and node.dim else ""
            return f"{self.get_data_type(node.type)}[{dim}]"

        if isinstance(node, c_ast.FuncDecl):
            return self.get_data_type(node.type)

        return "unknown"

    def process_declaration(
        self, node: c_ast.Decl, kind: str = "variable", data_type_override: Optional[str] = None
    ) -> None:
        if not node.name:
            return

        data_type = (
            data_type_override
            if data_type_override is not None
            else self.get_data_type(node)
        )

        symbol = Symbol(
            name=node.name,
            data_type=data_type,
            kind=kind,
            value=self.get_initial_value(node.init),
            line_number=node.coord.line if node.coord else 1,
            scope_id=self.symbol_table.get_current_scope().scope_id,
        )

        if not self.symbol_table.insert_symbol(symbol):
            self.errors.append(
                f"Duplicate declaration of '{node.name}' at line {symbol.line_number} in scope {symbol.scope_id}"
            )

    def process_parameters(self, function_node: c_ast.FuncDef) -> None:
        function_type = function_node.decl.type
        if not isinstance(function_type, c_ast.FuncDecl):
            return

        args = function_type.args
        if args is None:
            return

        for parameter in args.params:
            if isinstance(parameter, c_ast.Decl) and parameter.name:
                self.process_declaration(parameter, kind="parameter")

    def process_compound(self, node: c_ast.Compound, create_scope: bool = False, scope_name: str = "Block") -> None:
        if create_scope:
            scope = self.symbol_table.create_scope(scope_name)
            self.symbol_table.enter_scope(scope)

        for item in node.block_items or []:
            self.process_node(item)

        if create_scope:
            self.symbol_table.exit_scope()

    def process_node(self, node: c_ast.Node) -> None:
        if isinstance(node, c_ast.Decl):
            self.process_declaration(node)

        elif isinstance(node, c_ast.FuncDef):
            return_type = self.get_data_type(node.decl.type.type)
            self.process_declaration(
                node.decl, kind="function", data_type_override=return_type
            )

            function_scope = self.symbol_table.create_scope(node.decl.name)
            self.symbol_table.enter_scope(function_scope)
            self.process_parameters(node)
            self.process_compound(node.body, create_scope=False)
            self.symbol_table.exit_scope()

        elif isinstance(node, c_ast.Compound):
            self.process_compound(node, create_scope=True)

        elif isinstance(node, (c_ast.If, c_ast.While, c_ast.For, c_ast.DoWhile)):
            for child_name, child_node in node.children():
                if isinstance(child_node, c_ast.Compound):
                    self.process_compound(child_node, create_scope=True, scope_name=f"{type(node).__name__}_Block")
                else:
                    self.process_node(child_node)

    def parse(self, source_code: str) -> Tuple[SymbolTableManager, List[str]]:
        self.symbol_table.reset()
        self.errors = []

        try:
            ast = self.parser.parse(source_code)
        except Exception as error:
            self.errors.append(f"Syntax/Parsing error: {error}")
            return self.symbol_table, self.errors

        for node in ast.ext:
            self.process_node(node)

        return self.symbol_table, self.errors