"""
Output Guardrails - walidacja wyjścia z LLM i narzędzi.
Chroni przed wyciekiem danych, niebezpieczną zawartością, hallucynacjami.
"""

import re
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum


class OutputRiskLevel(str, Enum):
    """Poziomy ryzyka wyjścia."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


@dataclass
class OutputValidationResult:
    """Wynik walidacji wyjścia."""
    is_valid: bool
    risk_level: OutputRiskLevel
    issues: list[str]
    sanitized_output: str
    original_output: str


# =============================================================================
# WZORCE DO WYKRYWANIA NIEBEZPIECZNEJ ZAWARTOŚCI
# =============================================================================

# Wzorce wycieków danych
DATA_LEAK_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{11}\b',  # PESEL
    r'\b\d{2}-\d{3}\b',  # Kod pocztowy PL
    r'\b(?:\d[ -]*?){13,16}\b',  # Numer karty kredytowej
    r'\bPL\d{2}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}\b',  # IBAN PL
    r'\b\d{3}-\d{3}-\d{2}-\d{2}\b',  # NIP
    r'\b\d{9,10}\b(?=.*(?:telefon|tel\.|nr tel))',  # Numer telefonu
]

# Wzorce prompt leakage
PROMPT_LEAK_PATTERNS = [
    r'system\s*prompt',
    r'moje\s*instrukcje',
    r'my\s*instructions',
    r'jestem\s*zaprogramowany',
    r'i\s*am\s*programmed',
    r'mój\s*prompt',
    r'zostałem\s*skonfigurowany',
]

# Wzorce niebezpiecznej treści
HARMFUL_CONTENT_PATTERNS = [
    r'jak\s*(zrobić|przygotować|stworzyć)\s*(bombę|truciznę|narkotyk)',
    r'how\s*to\s*(make|create|build)\s*(bomb|poison|drug)',
    r'instrukcja\s*(zabijania|kradzieży|włamania)',
]

# Wzorce hallucynacji prawniczych
LEGAL_HALLUCINATION_PATTERNS = [
    r'art\.\s*\d{4,}',  # Nieistniejący artykuł (za duży numer)
    r'kodeks\s+\w+\s+z\s+\d{4}\s+roku',  # Potencjalnie zmyślona data kodeksu
    r'zgodnie\s+z\s+ustawą\s+z\s+dnia\s+\d{1,2}\s+\w+\s+20[3-9]\d',  # Przyszłe ustawy
]


class OutputGuardrails:
    """
    Walidator wyjścia z LLM i narzędzi.
    """
    
    def __init__(self, 
                 block_pii: bool = True,
                 block_prompt_leak: bool = True,
                 check_hallucinations: bool = True,
                 max_output_length: int = 50000):
        self.block_pii = block_pii
        self.block_prompt_leak = block_prompt_leak
        self.check_hallucinations = check_hallucinations
        self.max_output_length = max_output_length
    
    def validate(self, output: str) -> OutputValidationResult:
        """
        Główna funkcja walidacji wyjścia.
        
        Args:
            output: Tekst wyjściowy do walidacji
            
        Returns:
            OutputValidationResult z wynikami walidacji
        """
        if not output:
            return OutputValidationResult(
                is_valid=True,
                risk_level=OutputRiskLevel.SAFE,
                issues=[],
                sanitized_output="",
                original_output=""
            )
        
        issues = []
        risk_level = OutputRiskLevel.SAFE
        sanitized = output
        
        # 1. Sprawdź długość
        if len(output) > self.max_output_length:
            issues.append(f"Wyjście przekracza limit długości ({self.max_output_length})")
            sanitized = output[:self.max_output_length] + "...[skrócono]"
            risk_level = self._elevate_risk(risk_level, OutputRiskLevel.LOW)
        
        # 2. Sprawdź wycieki danych osobowych
        if self.block_pii:
            pii_issues, sanitized = self._check_pii(sanitized)
            if pii_issues:
                issues.extend(pii_issues)
                risk_level = self._elevate_risk(risk_level, OutputRiskLevel.MEDIUM)
        
        # 3. Sprawdź prompt leakage
        if self.block_prompt_leak:
            leak_issues = self._check_prompt_leak(sanitized)
            if leak_issues:
                issues.extend(leak_issues)
                risk_level = self._elevate_risk(risk_level, OutputRiskLevel.HIGH)
        
        # 4. Sprawdź niebezpieczną treść
        harmful_issues = self._check_harmful_content(sanitized)
        if harmful_issues:
            issues.extend(harmful_issues)
            risk_level = OutputRiskLevel.BLOCKED
        
        # 5. Sprawdź potencjalne hallucynacje
        if self.check_hallucinations:
            hallucination_issues = self._check_hallucinations(sanitized)
            if hallucination_issues:
                issues.extend(hallucination_issues)
                risk_level = self._elevate_risk(risk_level, OutputRiskLevel.LOW)
        
        is_valid = risk_level != OutputRiskLevel.BLOCKED
        
        return OutputValidationResult(
            is_valid=is_valid,
            risk_level=risk_level,
            issues=issues,
            sanitized_output=sanitized if is_valid else "[ZABLOKOWANO]",
            original_output=output
        )
    
    def validate_tool_output(self, tool_name: str, output: Any) -> OutputValidationResult:
        """
        Waliduje wyjście konkretnego narzędzia.
        """
        # Konwertuj do stringa jeśli potrzeba
        if isinstance(output, (list, dict)):
            import json
            output_str = json.dumps(output, ensure_ascii=False, default=str)
        else:
            output_str = str(output)
        
        result = self.validate(output_str)
        
        # Dodatkowe sprawdzenia dla konkretnych narzędzi
        if tool_name == "search_judgments":
            # Sprawdź czy wyniki mają wymagane pola
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict):
                        if 'signature' not in item or 'content' not in item:
                            result.issues.append("Brak wymaganych pól w wyniku wyszukiwania")
        
        return result
    
    def _check_pii(self, text: str) -> tuple[list[str], str]:
        """Sprawdza i maskuje dane osobowe."""
        issues = []
        sanitized = text
        
        pii_types = {
            "email": (DATA_LEAK_PATTERNS[0], "[EMAIL]"),
            "PESEL": (DATA_LEAK_PATTERNS[1], "[PESEL]"),
            "kod_pocztowy": (DATA_LEAK_PATTERNS[2], "[KOD]"),
            "karta_kredytowa": (DATA_LEAK_PATTERNS[3], "[KARTA]"),
            "IBAN": (DATA_LEAK_PATTERNS[4], "[IBAN]"),
            "NIP": (DATA_LEAK_PATTERNS[5], "[NIP]"),
        }
        
        for pii_name, (pattern, mask) in pii_types.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.append(f"Wykryto potencjalne {pii_name}: {len(matches)} wystąpień")
                sanitized = re.sub(pattern, mask, sanitized, flags=re.IGNORECASE)
        
        return issues, sanitized
    
    def _check_prompt_leak(self, text: str) -> list[str]:
        """Sprawdza wycieki promptu systemowego."""
        issues = []
        text_lower = text.lower()
        
        for pattern in PROMPT_LEAK_PATTERNS:
            if re.search(pattern, text_lower):
                issues.append("Wykryto potencjalny wyciek promptu systemowego")
                break
        
        return issues
    
    def _check_harmful_content(self, text: str) -> list[str]:
        """Sprawdza niebezpieczną treść."""
        issues = []
        text_lower = text.lower()
        
        for pattern in HARMFUL_CONTENT_PATTERNS:
            if re.search(pattern, text_lower):
                issues.append("Wykryto potencjalnie niebezpieczną treść")
                break
        
        return issues
    
    def _check_hallucinations(self, text: str) -> list[str]:
        """Sprawdza potencjalne hallucynacje prawnicze."""
        issues = []
        
        for pattern in LEGAL_HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.append(f"Potencjalna hallucynacja prawnicza: {matches[0]}")
        
        return issues
    
    def _elevate_risk(self, current: OutputRiskLevel, new: OutputRiskLevel) -> OutputRiskLevel:
        """Podnosi poziom ryzyka do wyższego."""
        risk_order = [
            OutputRiskLevel.SAFE,
            OutputRiskLevel.LOW,
            OutputRiskLevel.MEDIUM,
            OutputRiskLevel.HIGH,
            OutputRiskLevel.BLOCKED
        ]
        
        current_idx = risk_order.index(current)
        new_idx = risk_order.index(new)
        
        return risk_order[max(current_idx, new_idx)]


# =============================================================================
# WALIDACJA ODPOWIEDZI RAG
# =============================================================================

class RAGOutputValidator:
    """
    Walidator specyficzny dla odpowiedzi RAG.
    Sprawdza czy odpowiedź jest oparta na kontekście.
    """
    
    def __init__(self, min_context_overlap: float = 0.1):
        self.min_context_overlap = min_context_overlap
        self.base_guardrails = OutputGuardrails()
    
    def validate_rag_response(self, response: str, context_chunks: list[str]) -> OutputValidationResult:
        """
        Waliduje odpowiedź RAG względem kontekstu.
        """
        # Najpierw podstawowa walidacja
        base_result = self.base_guardrails.validate(response)
        
        if not base_result.is_valid:
            return base_result
        
        issues = list(base_result.issues)
        
        # Sprawdź overlap z kontekstem
        if context_chunks:
            overlap_score = self._calculate_context_overlap(response, context_chunks)
            
            if overlap_score < self.min_context_overlap:
                issues.append(f"Niska zgodność z kontekstem ({overlap_score:.1%})")
                base_result.risk_level = self._elevate_risk(
                    base_result.risk_level, OutputRiskLevel.MEDIUM
                )
        
        # Sprawdź czy odpowiedź nie jest zbyt ogólna
        if len(response) < 50 and context_chunks:
            issues.append("Odpowiedź może być zbyt ogólna")
        
        return OutputValidationResult(
            is_valid=base_result.is_valid,
            risk_level=base_result.risk_level,
            issues=issues,
            sanitized_output=base_result.sanitized_output,
            original_output=base_result.original_output
        )
    
    def _calculate_context_overlap(self, response: str, context_chunks: list[str]) -> float:
        """
        Oblicza overlap między odpowiedzią a kontekstem.
        Prosty algorytm oparty na n-gramach.
        """
        if not response or not context_chunks:
            return 0.0
        
        # Wyodrębnij słowa z odpowiedzi
        response_words = set(re.findall(r'\b\w{4,}\b', response.lower()))
        
        if not response_words:
            return 0.0
        
        # Wyodrębnij słowa z kontekstu
        context_words = set()
        for chunk in context_chunks:
            context_words.update(re.findall(r'\b\w{4,}\b', chunk.lower()))
        
        if not context_words:
            return 0.0
        
        # Oblicz overlap
        overlap = response_words.intersection(context_words)
        
        return len(overlap) / len(response_words)
    
    def _elevate_risk(self, current: OutputRiskLevel, new: OutputRiskLevel) -> OutputRiskLevel:
        """Podnosi poziom ryzyka."""
        risk_order = [
            OutputRiskLevel.SAFE,
            OutputRiskLevel.LOW,
            OutputRiskLevel.MEDIUM,
            OutputRiskLevel.HIGH,
            OutputRiskLevel.BLOCKED
        ]
        
        current_idx = risk_order.index(current)
        new_idx = risk_order.index(new)
        
        return risk_order[max(current_idx, new_idx)]


# Singleton dla łatwego dostępu
_output_guardrails = None

def get_output_guardrails() -> OutputGuardrails:
    """Zwraca singleton OutputGuardrails."""
    global _output_guardrails
    if _output_guardrails is None:
        _output_guardrails = OutputGuardrails()
    return _output_guardrails


def get_rag_validator() -> RAGOutputValidator:
    """Zwraca walidator RAG."""
    return RAGOutputValidator()
