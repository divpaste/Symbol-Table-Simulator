from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Tuple

@dataclass
class Symbol:
    name: str
    data_type: str
    kind: str
    value: Optional[Any]
    line_number: int
    scope_id: str

class HashTable:
    def __init__(self, size: int = 7):
        self.size = size
        self.buckets: List[List[Symbol]] = [[] for _ in range(size)]

    def hash_function(self, name: str) -> int:
        return sum(ord(char) for char in name) % self.size

    def insert(self, symbol: Symbol) -> bool:
        index = self.hash_function(symbol.name)
        for existing in self.buckets[index]:
            if existing.name == symbol.name:
                return False
        self.buckets[index].append(symbol)
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        index = self.hash_function(name)
        for symbol in self.buckets[index]:
            if symbol.name == name:
                return symbol
        return None

    def display(self) -> None:
        for index, bucket in enumerate(self.buckets):
            print(f"Bucket {index}: {bucket}")

    def update(self, name: str, attributes: Dict[str, Any]) -> bool:
        index = self.hash_function(name)
        for symbol in self.buckets[index]:
            if symbol.name == name:
                for attribute, new_value in attributes.items():
                    if hasattr(symbol, attribute):
                        setattr(symbol, attribute, new_value)
                return True
        return False

    def delete(self, name: str) -> bool:
        index = self.hash_function(name)
        for position, symbol in enumerate(self.buckets[index]):
            if symbol.name == name:
                del self.buckets[index][position]
                return True
        return False

    def load_factor(self) -> float:
        total_symbols = sum(len(bucket) for bucket in self.buckets)
        return total_symbols / self.size

    def get_stats(self) -> Dict[str, Any]:
        occupied = sum(1 for b in self.buckets if len(b) > 0)
        total_symbols = sum(len(b) for b in self.buckets)
        collisions = sum(len(b) - 1 for b in self.buckets if len(b) > 1)
        max_chain = max((len(b) for b in self.buckets), default=0)
        return {
            "size": self.size,
            "total_symbols": total_symbols,
            "occupied_buckets": occupied,
            "empty_buckets": self.size - occupied,
            "collisions": collisions,
            "max_chain_length": max_chain,
            "load_factor": self.load_factor(),
        }

class Scope:
    def __init__(
        self, scope_id: str, scope_name: str, parent: Optional["Scope"] = None, table_size: int = 7
    ):
        self.scope_id = scope_id
        self.scope_name = scope_name
        self.parent = parent
        self.hash_table = HashTable(table_size)
        self.children: List["Scope"] = []

        if parent is not None:
            parent.children.append(self)

    def get_parent(self) -> Optional["Scope"]:
        return self.parent

    def get_symbols(self) -> List[Symbol]:
        symbols = []
        for bucket in self.hash_table.buckets:
            symbols.extend(bucket)
        return symbols

class SymbolTableManager:
    def __init__(self, table_size: int = 7):
        self.table_size = table_size
        self.global_scope = Scope("S0", "Global", table_size=table_size)
        self.current_scope = self.global_scope
        self.all_scopes: List[Scope] = [self.global_scope]
        self.next_scope_number = 1

    def create_scope(self, scope_name: str) -> Scope:
        scope_id = f"S{self.next_scope_number}"
        self.next_scope_number += 1
        scope = Scope(
            scope_id,
            scope_name,
            parent=self.current_scope,
            table_size=self.table_size
        )
        self.all_scopes.append(scope)
        return scope

    def enter_scope(self, scope: Scope) -> None:
        if scope not in self.all_scopes:
            raise ValueError("Scope does not belong to this manager")
        self.current_scope = scope

    def exit_scope(self) -> None:
        if self.current_scope.parent is None:
            raise ValueError("Cannot exit the global scope")
        self.current_scope = self.current_scope.parent

    def get_parent(self, scope: Optional[Scope] = None) -> Optional[Scope]:
        if scope is None:
            scope = self.current_scope
        return scope.get_parent()

    def get_current_scope(self) -> Scope:
        return self.current_scope

    def insert_symbol(self, symbol: Symbol) -> bool:
        symbol.scope_id = self.current_scope.scope_id
        return self.current_scope.hash_table.insert(symbol)

    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        scope = self.current_scope
        while scope is not None:
            symbol = scope.hash_table.lookup(name)
            if symbol is not None:
                return symbol
            scope = scope.parent
        return None

    def lookup_symbol_with_path(self, name: str, start_scope: Optional[Scope] = None) -> Tuple[Optional[Symbol], List[str]]:
        """Performs lexical scoping lookup and records the scope search path."""
        scope = start_scope if start_scope is not None else self.current_scope
        path = []
        while scope is not None:
            path.append(f"{scope.scope_id} ({scope.scope_name})")
            symbol = scope.hash_table.lookup(name)
            if symbol is not None:
                return symbol, path
            scope = scope.parent
        return None, path

    def detect_shadowing(self) -> List[Dict[str, Any]]:
        """Identifies inner identifiers that shadow declarations in outer scopes."""
        shadow_events = []
        for scope in self.all_scopes:
            if scope.parent is None:
                continue
            for symbol in scope.get_symbols():
                parent_scope = scope.parent
                while parent_scope is not None:
                    shadowed = parent_scope.hash_table.lookup(symbol.name)
                    if shadowed:
                        shadow_events.append({
                            "name": symbol.name,
                            "inner_scope": f"{scope.scope_id} ({scope.scope_name})",
                            "inner_line": symbol.line_number,
                            "shadowed_scope": f"{parent_scope.scope_id} ({parent_scope.scope_name})",
                            "shadowed_line": shadowed.line_number,
                        })
                    parent_scope = parent_scope.parent
        return shadow_events

    def update_symbol(self, name: str, attributes: Dict[str, Any]) -> bool:
        symbol = self.lookup_symbol(name)
        if symbol is None:
            return False
        for attribute, value in attributes.items():
            if hasattr(symbol, attribute):
                setattr(symbol, attribute, value)
        return True

    def delete_symbol(self, name: str, scope: Optional[Scope] = None) -> bool:
        if scope is None:
            scope = self.current_scope
        return scope.hash_table.delete(name)

    def get_all_symbols(self) -> List[Symbol]:
        symbols = []
        for scope in self.all_scopes:
            symbols.extend(scope.get_symbols())
        return symbols

    def get_scope_by_id(self, scope_id: str) -> Optional[Scope]:
        for scope in self.all_scopes:
            if scope.scope_id == scope_id:
                return scope
        return None

    def reset(self) -> None:
        self.__init__(table_size=self.table_size)