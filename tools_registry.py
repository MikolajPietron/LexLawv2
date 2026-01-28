"""
Rejestr narzędzi (Tool Registry) z walidacją schematów.
Implementacja allowlist + walidacja parametrów dla function-calling.
"""

from typing import Any, Callable, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum
import time
import json


# =============================================================================
# SCHEMATY NARZĘDZI (Tool Schemas)
# =============================================================================

class ToolCategory(str, Enum):
    """Kategorie narzędzi dla bezpieczeństwa."""
    SEARCH = "search"
    ANALYSIS = "analysis"
    RETRIEVAL = "retrieval"
    UTILITY = "utility"


class ToolParameter(BaseModel):
    """Schema parametru narzędzia."""
    name: str
    type: str  # "string", "integer", "boolean", "array"
    description: str
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_length: Optional[int] = None
    enum_values: Optional[list] = None


class ToolSchema(BaseModel):
    """Pełny schemat narzędzia."""
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    returns: str
    timeout_seconds: int = 30
    requires_auth: bool = False
    is_enabled: bool = True
    
    def to_openai_function(self) -> dict:
        """Konwertuje schemat do formatu OpenAI function-calling."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum_values:
                prop["enum"] = param.enum_values
            if param.type == "integer" or param.type == "number":
                if param.min_value is not None:
                    prop["minimum"] = param.min_value
                if param.max_value is not None:
                    prop["maximum"] = param.max_value
            
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class ToolExecutionResult(BaseModel):
    """Wynik wykonania narzędzia."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    error_category: Optional[str] = None  # "timeout", "validation", "execution", "security"
    execution_time_ms: float = 0
    timestamp: str = ""


# =============================================================================
# REJESTR NARZĘDZI (Tool Registry)
# =============================================================================

class ToolRegistry:
    """
    Centralny rejestr narzędzi z allowlist i walidacją.
    Implementuje wzorzec Singleton dla globalnego dostępu.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: dict[str, ToolSchema] = {}
        self._handlers: dict[str, Callable] = {}
        self._execution_logs: list[ToolExecutionResult] = []
        self._initialized = True
    
    def register(self, schema: ToolSchema, handler: Callable) -> None:
        """
        Rejestruje narzędzie w allowlist.
        
        Args:
            schema: Schemat narzędzia
            handler: Funkcja obsługująca narzędzie
        """
        if schema.name in self._tools:
            raise ValueError(f"Narzędzie '{schema.name}' już zarejestrowane")
        
        self._tools[schema.name] = schema
        self._handlers[schema.name] = handler
    
    def get_tool(self, name: str) -> Optional[ToolSchema]:
        """Pobiera schemat narzędzia z allowlist."""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """Pobiera handler narzędzia."""
        return self._handlers.get(name)
    
    def is_allowed(self, name: str) -> bool:
        """Sprawdza czy narzędzie jest na allowlist."""
        tool = self._tools.get(name)
        return tool is not None and tool.is_enabled
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> list[ToolSchema]:
        """Lista dostępnych narzędzi."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return [t for t in tools if t.is_enabled]
    
    def get_openai_tools(self) -> list[dict]:
        """Zwraca narzędzia w formacie OpenAI function-calling."""
        return [t.to_openai_function() for t in self.list_tools()]
    
    def validate_parameters(self, tool_name: str, params: dict) -> tuple[bool, str]:
        """
        Waliduje parametry wywołania narzędzia.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        schema = self._tools.get(tool_name)
        if not schema:
            return False, f"Nieznane narzędzie: {tool_name}"
        
        if not schema.is_enabled:
            return False, f"Narzędzie '{tool_name}' jest wyłączone"
        
        # Sprawdź wymagane parametry
        for param in schema.parameters:
            if param.required and param.name not in params:
                return False, f"Brak wymaganego parametru: {param.name}"
            
            if param.name in params:
                value = params[param.name]
                
                # Walidacja typu
                if param.type == "string" and not isinstance(value, str):
                    return False, f"Parametr {param.name} musi być stringiem"
                if param.type == "integer" and not isinstance(value, int):
                    return False, f"Parametr {param.name} musi być liczbą całkowitą"
                if param.type == "boolean" and not isinstance(value, bool):
                    return False, f"Parametr {param.name} musi być boolean"
                if param.type == "array" and not isinstance(value, list):
                    return False, f"Parametr {param.name} musi być listą"
                
                # Walidacja zakresu
                if param.type in ("integer", "number"):
                    if param.min_value is not None and value < param.min_value:
                        return False, f"Parametr {param.name} poniżej minimum ({param.min_value})"
                    if param.max_value is not None and value > param.max_value:
                        return False, f"Parametr {param.name} powyżej maximum ({param.max_value})"
                
                # Walidacja długości
                if param.type == "string" and param.max_length:
                    if len(value) > param.max_length:
                        return False, f"Parametr {param.name} zbyt długi (max {param.max_length})"
                
                # Walidacja enum
                if param.enum_values and value not in param.enum_values:
                    return False, f"Parametr {param.name} musi być jednym z: {param.enum_values}"
        
        return True, ""
    
    def log_execution(self, result: ToolExecutionResult) -> None:
        """Loguje wykonanie narzędzia."""
        self._execution_logs.append(result)
        # Zachowaj ostatnie 1000 logów
        if len(self._execution_logs) > 1000:
            self._execution_logs = self._execution_logs[-1000:]
    
    def get_execution_logs(self, limit: int = 100) -> list[ToolExecutionResult]:
        """Pobiera logi wykonań."""
        return self._execution_logs[-limit:]
    
    def get_metrics(self) -> dict:
        """Zwraca metryki narzędzi."""
        if not self._execution_logs:
            return {"total_calls": 0}
        
        total = len(self._execution_logs)
        success = sum(1 for r in self._execution_logs if r.success)
        avg_time = sum(r.execution_time_ms for r in self._execution_logs) / total
        
        by_tool = {}
        for log in self._execution_logs:
            if log.tool_name not in by_tool:
                by_tool[log.tool_name] = {"calls": 0, "success": 0, "total_time": 0}
            by_tool[log.tool_name]["calls"] += 1
            if log.success:
                by_tool[log.tool_name]["success"] += 1
            by_tool[log.tool_name]["total_time"] += log.execution_time_ms
        
        return {
            "total_calls": total,
            "success_rate": success / total if total > 0 else 0,
            "avg_execution_time_ms": avg_time,
            "by_tool": by_tool
        }


# =============================================================================
# DEFINICJE NARZĘDZI DLA WYSZUKIWARKI PRAWNEJ
# =============================================================================

# Narzędzie 1: Wyszukiwanie semantyczne
SEARCH_JUDGMENTS_SCHEMA = ToolSchema(
    name="search_judgments",
    description="Wyszukuje orzeczenia sądowe w bazie danych na podstawie zapytania semantycznego. Używaj gdy użytkownik pyta o wyroki, orzeczenia, sprawy sądowe.",
    category=ToolCategory.SEARCH,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Zapytanie wyszukiwania - opis sprawy, artykuł kodeksu, typ przestępstwa itp.",
            max_length=2000
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="Liczba wyników do zwrócenia",
            required=False,
            default=5,
            min_value=1,
            max_value=20
        ),
        ToolParameter(
            name="use_reranking",
            type="boolean",
            description="Czy użyć re-rankingu dla lepszej trafności",
            required=False,
            default=True
        ),
        ToolParameter(
            name="date_from",
            type="string",
            description="Data początkowa (format: YYYY-MM-DD)",
            required=False
        ),
        ToolParameter(
            name="date_to",
            type="string",
            description="Data końcowa (format: YYYY-MM-DD)",
            required=False
        )
    ],
    returns="Lista orzeczeń z sygnaturą, datą, treścią i oceną trafności",
    timeout_seconds=60
)

# Narzędzie 2: Analiza dokumentu PDF
ANALYZE_PDF_SCHEMA = ToolSchema(
    name="analyze_pdf",
    description="Analizuje przesłany dokument PDF i znajduje podobne orzeczenia w bazie. Używaj gdy użytkownik przesyła plik PDF.",
    category=ToolCategory.ANALYSIS,
    parameters=[
        ToolParameter(
            name="pdf_text",
            type="string",
            description="Tekst wyodrębniony z dokumentu PDF",
            max_length=50000
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="Liczba podobnych orzeczeń do zwrócenia",
            required=False,
            default=5,
            min_value=1,
            max_value=20
        )
    ],
    returns="Lista podobnych orzeczeń z oceną podobieństwa",
    timeout_seconds=90
)

# Narzędzie 3: Pobieranie szczegółów orzeczenia
GET_JUDGMENT_DETAILS_SCHEMA = ToolSchema(
    name="get_judgment_details",
    description="Pobiera pełne szczegóły konkretnego orzeczenia na podstawie ID lub sygnatury.",
    category=ToolCategory.RETRIEVAL,
    parameters=[
        ToolParameter(
            name="judgment_id",
            type="integer",
            description="ID orzeczenia w bazie danych",
            required=False
        ),
        ToolParameter(
            name="signature",
            type="string",
            description="Sygnatura orzeczenia (np. II K 123/20)",
            required=False,
            max_length=100
        )
    ],
    returns="Pełny tekst orzeczenia z metadanymi",
    timeout_seconds=30
)

# Narzędzie 4: Wyjaśnienie artykułu kodeksu
EXPLAIN_ARTICLE_SCHEMA = ToolSchema(
    name="explain_legal_article",
    description="Wyjaśnia znaczenie artykułu kodeksu karnego/cywilnego. Używaj gdy użytkownik pyta o znaczenie konkretnego artykułu.",
    category=ToolCategory.UTILITY,
    parameters=[
        ToolParameter(
            name="article",
            type="string",
            description="Numer artykułu (np. 'art. 286 kk', 'art. 415 kc')",
            max_length=50
        )
    ],
    returns="Wyjaśnienie artykułu z przykładami zastosowania",
    timeout_seconds=20
)

# Narzędzie 5: Statystyki wyroków
GET_STATISTICS_SCHEMA = ToolSchema(
    name="get_verdict_statistics",
    description="Pobiera statystyki wyroków dla danego typu przestępstwa lub artykułu.",
    category=ToolCategory.ANALYSIS,
    parameters=[
        ToolParameter(
            name="crime_type",
            type="string",
            description="Typ przestępstwa (np. 'kradzież', 'oszustwo', 'rozbój')",
            required=False,
            max_length=100
        ),
        ToolParameter(
            name="article",
            type="string",
            description="Artykuł kodeksu (np. 'art. 286 kk')",
            required=False,
            max_length=50
        )
    ],
    returns="Statystyki: średnia kara, rozkład wyroków, trendy",
    timeout_seconds=45
)


def get_default_registry() -> ToolRegistry:
    """Tworzy i zwraca domyślny rejestr z zarejestrowanymi narzędziami."""
    registry = ToolRegistry()
    
    # Narzędzia są rejestrowane w search_app.py z odpowiednimi handlerami
    return registry
