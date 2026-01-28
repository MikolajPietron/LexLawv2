"""
Dispatcher narzędzi z bezpieczeństwem wykonania.
Implementuje: timeout, sanitację, kategoryzację błędów, function-calling loop.
"""

import asyncio
import concurrent.futures
import json
import time
import traceback
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
import threading

from tools_registry import (
    ToolRegistry, ToolSchema, ToolExecutionResult, 
    ToolCategory, ToolParameter
)


# =============================================================================
# KONFIGURACJA DISPATCHERA
# =============================================================================

DEFAULT_TIMEOUT = 30  # sekundy
MAX_RETRIES = 2
MAX_TOOL_CALLS_PER_REQUEST = 5  # Limit wywołań narzędzi w jednym zapytaniu


# =============================================================================
# KATEGORIE BŁĘDÓW
# =============================================================================

class ErrorCategory:
    """Kategorie błędów dla obsługi wyjątków."""
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    EXECUTION = "execution"
    SECURITY = "security"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


# =============================================================================
# OBSERVABILITY - LOGGING
# =============================================================================

@dataclass
class ToolCallLog:
    """Log pojedynczego wywołania narzędzia."""
    call_id: str
    tool_name: str
    parameters: dict
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0
    success: bool = False
    result_summary: str = ""
    error: Optional[str] = None
    error_category: Optional[str] = None
    retries: int = 0


class ObservabilityLogger:
    """
    Logger dla observability - śledzi wywołania narzędzi, metryki, błędy.
    """
    
    def __init__(self, max_logs: int = 1000):
        self._logs: list[ToolCallLog] = []
        self._max_logs = max_logs
        self._lock = threading.Lock()
        self._call_counter = 0
    
    def _generate_call_id(self) -> str:
        """Generuje unikalny ID wywołania."""
        self._call_counter += 1
        return f"call_{int(time.time())}_{self._call_counter}"
    
    def start_call(self, tool_name: str, parameters: dict) -> ToolCallLog:
        """Rozpoczyna logowanie wywołania."""
        log = ToolCallLog(
            call_id=self._generate_call_id(),
            tool_name=tool_name,
            parameters=self._sanitize_params_for_log(parameters),
            start_time=datetime.now()
        )
        return log
    
    def end_call(self, log: ToolCallLog, success: bool, 
                 result_summary: str = "", error: str = None,
                 error_category: str = None) -> None:
        """Kończy logowanie wywołania."""
        log.end_time = datetime.now()
        log.duration_ms = (log.end_time - log.start_time).total_seconds() * 1000
        log.success = success
        log.result_summary = result_summary[:500] if result_summary else ""
        log.error = error
        log.error_category = error_category
        
        with self._lock:
            self._logs.append(log)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
    
    def _sanitize_params_for_log(self, params: dict) -> dict:
        """Sanityzuje parametry do logowania (ukrywa wrażliwe dane)."""
        sanitized = {}
        sensitive_keys = {"password", "api_key", "token", "secret"}
        
        for key, value in params.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[truncated]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def get_logs(self, limit: int = 100, tool_name: str = None) -> list[ToolCallLog]:
        """Pobiera logi wywołań."""
        with self._lock:
            logs = self._logs[-limit:]
            if tool_name:
                logs = [l for l in logs if l.tool_name == tool_name]
            return logs
    
    def get_metrics(self) -> dict:
        """Zwraca metryki wywołań."""
        with self._lock:
            if not self._logs:
                return {
                    "total_calls": 0,
                    "success_rate": 0.0,
                    "avg_duration_ms": 0.0,
                    "by_tool": {},
                    "by_error_category": {}
                }
            
            total = len(self._logs)
            success_count = sum(1 for l in self._logs if l.success)
            avg_duration = sum(l.duration_ms for l in self._logs) / total
            
            by_tool = {}
            for log in self._logs:
                if log.tool_name not in by_tool:
                    by_tool[log.tool_name] = {
                        "calls": 0, 
                        "success": 0, 
                        "total_duration_ms": 0,
                        "errors": 0
                    }
                by_tool[log.tool_name]["calls"] += 1
                if log.success:
                    by_tool[log.tool_name]["success"] += 1
                else:
                    by_tool[log.tool_name]["errors"] += 1
                by_tool[log.tool_name]["total_duration_ms"] += log.duration_ms
            
            by_error = {}
            for log in self._logs:
                if log.error_category:
                    by_error[log.error_category] = by_error.get(log.error_category, 0) + 1
            
            return {
                "total_calls": total,
                "success_rate": success_count / total,
                "avg_duration_ms": avg_duration,
                "by_tool": by_tool,
                "by_error_category": by_error
            }
    
    def format_logs_for_display(self, limit: int = 20) -> str:
        """Formatuje logi do wyświetlenia."""
        logs = self.get_logs(limit)
        if not logs:
            return "Brak logów wywołań."
        
        lines = []
        for log in reversed(logs):
            status = "✅" if log.success else "❌"
            time_str = log.start_time.strftime("%H:%M:%S")
            line = f"{status} [{time_str}] {log.tool_name} ({log.duration_ms:.0f}ms)"
            if log.error:
                line += f" - {log.error[:50]}"
            lines.append(line)
        
        return "\n".join(lines)


# =============================================================================
# DISPATCHER NARZĘDZI
# =============================================================================

class ToolDispatcher:
    """
    Dispatcher odpowiedzialny za bezpieczne wykonywanie narzędzi.
    
    Funkcje:
    - Walidacja parametrów przed wykonaniem
    - Timeout dla każdego wywołania
    - Kategoryzacja i obsługa błędów
    - Retry logic
    - Logging/observability
    """
    
    def __init__(self, registry: ToolRegistry, logger: ObservabilityLogger = None):
        self.registry = registry
        self.logger = logger or ObservabilityLogger()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def execute(self, tool_name: str, parameters: dict, 
                timeout: int = None) -> ToolExecutionResult:
        """
        Wykonuje narzędzie z pełnym bezpieczeństwem.
        
        Args:
            tool_name: Nazwa narzędzia
            parameters: Parametry wywołania
            timeout: Timeout w sekundach (opcjonalny)
            
        Returns:
            ToolExecutionResult z wynikiem lub błędem
        """
        start_time = time.time()
        log_entry = self.logger.start_call(tool_name, parameters)
        
        # 1. Sprawdź czy narzędzie jest na allowlist
        if not self.registry.is_allowed(tool_name):
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Narzędzie '{tool_name}' nie jest dozwolone",
                error_category=ErrorCategory.SECURITY,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            self.logger.end_call(log_entry, False, error=result.error, 
                                error_category=ErrorCategory.SECURITY)
            return result
        
        # 2. Pobierz schemat i handler
        schema = self.registry.get_tool(tool_name)
        handler = self.registry.get_handler(tool_name)
        
        if not handler:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Brak handlera dla narzędzia '{tool_name}'",
                error_category=ErrorCategory.NOT_FOUND,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            self.logger.end_call(log_entry, False, error=result.error,
                                error_category=ErrorCategory.NOT_FOUND)
            return result
        
        # 3. Waliduj parametry
        is_valid, validation_error = self.registry.validate_parameters(tool_name, parameters)
        if not is_valid:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=validation_error,
                error_category=ErrorCategory.VALIDATION,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            self.logger.end_call(log_entry, False, error=result.error,
                                error_category=ErrorCategory.VALIDATION)
            return result
        
        # 4. Sanityzuj parametry
        sanitized_params = self._sanitize_parameters(schema, parameters)
        
        # 5. Wykonaj z timeout
        effective_timeout = timeout or schema.timeout_seconds or DEFAULT_TIMEOUT
        
        try:
            future = self._executor.submit(handler, **sanitized_params)
            result_data = future.result(timeout=effective_timeout)
            
            execution_time = (time.time() - start_time) * 1000
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                result=result_data,
                execution_time_ms=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
            self.logger.end_call(log_entry, True, 
                                result_summary=str(result_data)[:200])
            self.registry.log_execution(result)
            return result
            
        except concurrent.futures.TimeoutError:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Timeout po {effective_timeout}s",
                error_category=ErrorCategory.TIMEOUT,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            self.logger.end_call(log_entry, False, error=result.error,
                                error_category=ErrorCategory.TIMEOUT)
            self.registry.log_execution(result)
            return result
            
        except Exception as e:
            error_msg = str(e)
            error_category = self._categorize_error(e)
            
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=error_msg,
                error_category=error_category,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            self.logger.end_call(log_entry, False, error=error_msg,
                                error_category=error_category)
            self.registry.log_execution(result)
            return result
    
    def execute_with_retry(self, tool_name: str, parameters: dict,
                           max_retries: int = MAX_RETRIES) -> ToolExecutionResult:
        """
        Wykonuje narzędzie z retry logic.
        """
        last_result = None
        
        for attempt in range(max_retries + 1):
            result = self.execute(tool_name, parameters)
            
            if result.success:
                return result
            
            # Nie retry dla błędów walidacji i security
            if result.error_category in (ErrorCategory.VALIDATION, ErrorCategory.SECURITY):
                return result
            
            last_result = result
            
            # Exponential backoff
            if attempt < max_retries:
                time.sleep(0.5 * (2 ** attempt))
        
        return last_result
    
    def _sanitize_parameters(self, schema: ToolSchema, params: dict) -> dict:
        """Sanityzuje parametry przed wykonaniem."""
        sanitized = {}
        
        for param_schema in schema.parameters:
            name = param_schema.name
            
            if name not in params:
                if param_schema.default is not None:
                    sanitized[name] = param_schema.default
                continue
            
            value = params[name]
            
            # Sanityzacja stringów
            if param_schema.type == "string" and isinstance(value, str):
                # Usuń niebezpieczne znaki
                value = value.replace('\x00', '')
                # Ogranicz długość
                if param_schema.max_length:
                    value = value[:param_schema.max_length]
                sanitized[name] = value
            
            # Sanityzacja liczb
            elif param_schema.type == "integer":
                try:
                    value = int(value)
                    if param_schema.min_value is not None:
                        value = max(value, int(param_schema.min_value))
                    if param_schema.max_value is not None:
                        value = min(value, int(param_schema.max_value))
                    sanitized[name] = value
                except (ValueError, TypeError):
                    sanitized[name] = param_schema.default or 0
            
            else:
                sanitized[name] = value
        
        return sanitized
    
    def _categorize_error(self, exception: Exception) -> str:
        """Kategoryzuje błąd na podstawie wyjątku."""
        error_str = str(exception).lower()
        
        if "timeout" in error_str:
            return ErrorCategory.TIMEOUT
        if "permission" in error_str or "unauthorized" in error_str:
            return ErrorCategory.SECURITY
        if "not found" in error_str or "404" in error_str:
            return ErrorCategory.NOT_FOUND
        if "rate limit" in error_str or "429" in error_str:
            return ErrorCategory.RATE_LIMIT
        if "validation" in error_str or "invalid" in error_str:
            return ErrorCategory.VALIDATION
        
        return ErrorCategory.UNKNOWN


# =============================================================================
# FUNCTION-CALLING LOOP (Call → Execute → Finalize)
# =============================================================================

class FunctionCallingLoop:
    """
    Implementacja pętli function-calling:
    1. CALL - Model wybiera narzędzie
    2. EXECUTE - Dispatcher wykonuje narzędzie
    3. FINALIZE - Wynik wraca do modelu dla finalnej odpowiedzi
    """
    
    def __init__(self, dispatcher: ToolDispatcher, openai_client, registry: ToolRegistry):
        self.dispatcher = dispatcher
        self.openai_client = openai_client
        self.registry = registry
        self.logger = dispatcher.logger
    
    def run(self, user_query: str, system_prompt: str = None,
            max_iterations: int = MAX_TOOL_CALLS_PER_REQUEST) -> dict:
        """
        Uruchamia pętlę function-calling.
        
        Args:
            user_query: Zapytanie użytkownika
            system_prompt: Opcjonalny system prompt
            max_iterations: Max liczba wywołań narzędzi
            
        Returns:
            dict z final_response, tool_calls, context
        """
        messages = []
        tool_calls_history = []
        context_chunks = []
        
        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": self._get_default_system_prompt()
            })
        
        # User query
        messages.append({"role": "user", "content": user_query})
        
        # Pobierz dostępne narzędzia
        tools = self.registry.get_openai_tools()
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            
            # CALL - Model wybiera narzędzie
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.3,
                    max_tokens=1000
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Błąd API OpenAI: {str(e)}",
                    "final_response": None,
                    "tool_calls": tool_calls_history,
                    "context": context_chunks
                }
            
            assistant_message = response.choices[0].message
            
            # Sprawdź czy model chce wywołać narzędzie
            if not assistant_message.tool_calls:
                # Model nie chce używać narzędzi - zwróć odpowiedź
                return {
                    "success": True,
                    "final_response": assistant_message.content,
                    "tool_calls": tool_calls_history,
                    "context": context_chunks
                }
            
            # Dodaj odpowiedź asystenta do historii
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # EXECUTE - Wykonaj każde narzędzie
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                
                # Wykonaj przez dispatcher (z walidacją, timeout, etc.)
                result = self.dispatcher.execute(tool_name, arguments)
                
                tool_calls_history.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": result.success,
                    "result": result.result if result.success else result.error,
                    "execution_time_ms": result.execution_time_ms
                })
                
                # Zbierz kontekst
                if result.success and result.result:
                    if isinstance(result.result, list):
                        for item in result.result[:5]:  # Max 5 fragmentów
                            if isinstance(item, dict) and 'content' in item:
                                context_chunks.append(item['content'])
                    elif isinstance(result.result, str):
                        context_chunks.append(result.result)
                
                # FINALIZE - Dodaj wynik do kontekstu modelu
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result.result if result.success else {"error": result.error},
                        ensure_ascii=False,
                        default=str
                    )[:4000]  # Limit długości
                }
                messages.append(tool_response)
        
        # Ostateczna odpowiedź po wszystkich tool calls
        try:
            final_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            return {
                "success": True,
                "final_response": final_response.choices[0].message.content,
                "tool_calls": tool_calls_history,
                "context": context_chunks
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Błąd finalizacji: {str(e)}",
                "final_response": None,
                "tool_calls": tool_calls_history,
                "context": context_chunks
            }
    
    def _get_default_system_prompt(self) -> str:
        """Domyślny system prompt dla asystenta prawnego."""
        return """Jesteś ekspertem od polskiego prawa, asystentem prawnym pomagającym w wyszukiwaniu i analizie orzeczeń sądowych.

Twoje możliwości:
1. Wyszukiwanie orzeczeń sądowych w bazie danych
2. Analiza dokumentów PDF z orzeczeniami
3. Wyjaśnianie artykułów kodeksów
4. Analiza statystyk wyroków

Zasady:
- Zawsze używaj dostępnych narzędzi do wyszukiwania informacji
- Odpowiadaj po polsku
- Cytuj źródła (sygnatury orzeczeń)
- Bądź precyzyjny i merytoryczny
- NIE wymyślaj informacji - opieraj się tylko na wynikach wyszukiwania

Gdy użytkownik pyta o orzeczenia, ZAWSZE użyj narzędzia search_judgments.
Gdy użytkownik przesyła PDF, użyj analyze_pdf.
"""


# =============================================================================
# LOCAL STUB dla testowania bez OpenAI
# =============================================================================

class LocalFunctionCallingStub:
    """
    Lokalny stub do testowania function-calling bez API OpenAI.
    Symuluje wybór narzędzia na podstawie słów kluczowych.
    """
    
    def __init__(self, dispatcher: ToolDispatcher, registry: ToolRegistry):
        self.dispatcher = dispatcher
        self.registry = registry
        self.logger = dispatcher.logger
    
    def run(self, user_query: str, **kwargs) -> dict:
        """
        Symuluje function-calling lokalnie.
        """
        tool_calls_history = []
        context_chunks = []
        
        # Prosty wybór narzędzia na podstawie słów kluczowych
        tool_name, arguments = self._select_tool(user_query)
        
        if tool_name:
            # Wykonaj narzędzie
            result = self.dispatcher.execute(tool_name, arguments)
            
            tool_calls_history.append({
                "tool": tool_name,
                "arguments": arguments,
                "success": result.success,
                "result": result.result if result.success else result.error,
                "execution_time_ms": result.execution_time_ms
            })
            
            if result.success and result.result:
                # Zbierz kontekst
                if isinstance(result.result, list):
                    for item in result.result[:5]:
                        if isinstance(item, dict) and 'content' in item:
                            context_chunks.append(item['content'])
                
                # Generuj prostą odpowiedź
                final_response = self._generate_response(user_query, result.result)
            else:
                final_response = f"Wystąpił błąd: {result.error}"
        else:
            final_response = "Nie znaleziono odpowiedniego narzędzia dla tego zapytania."
        
        return {
            "success": True,
            "final_response": final_response,
            "tool_calls": tool_calls_history,
            "context": context_chunks
        }
    
    def _select_tool(self, query: str) -> tuple[Optional[str], dict]:
        """Wybiera narzędzie na podstawie zapytania."""
        query_lower = query.lower()
        
        # Słowa kluczowe dla każdego narzędzia
        tool_keywords = {
            "search_judgments": [
                "wyrok", "orzeczenie", "sprawa", "sąd", "kara", 
                "oskarżony", "skazany", "artykuł", "art.", "kk", "kc"
            ],
            "explain_legal_article": [
                "co znaczy art", "wyjaśnij art", "co mówi art",
                "znaczenie artykułu", "interpretacja"
            ],
            "get_verdict_statistics": [
                "statystyki", "ile wyroków", "średnia kara",
                "jak często", "procent"
            ]
        }
        
        for tool_name, keywords in tool_keywords.items():
            if any(kw in query_lower for kw in keywords):
                # Domyślne argumenty
                if tool_name == "search_judgments":
                    return tool_name, {"query": query, "num_results": 5}
                elif tool_name == "explain_legal_article":
                    # Ekstrakcja artykułu z zapytania
                    import re
                    match = re.search(r'art\.?\s*(\d+)', query_lower)
                    article = f"art. {match.group(1)}" if match else query
                    return tool_name, {"article": article}
                elif tool_name == "get_verdict_statistics":
                    return tool_name, {"crime_type": query}
        
        # Domyślnie - wyszukiwanie
        return "search_judgments", {"query": query, "num_results": 5}
    
    def _generate_response(self, query: str, result: Any) -> str:
        """Generuje prostą odpowiedź na podstawie wyników."""
        if isinstance(result, list) and len(result) > 0:
            response_parts = [f"Znaleziono {len(result)} wyników dla zapytania: '{query}'\n"]
            
            for i, item in enumerate(result[:3], 1):
                if isinstance(item, dict):
                    sig = item.get('signature', 'Brak sygnatury')
                    date = item.get('date', 'Brak daty')
                    content = item.get('content', '')[:200]
                    response_parts.append(f"\n{i}. **{sig}** ({date})\n{content}...")
            
            return "\n".join(response_parts)
        
        return str(result)
