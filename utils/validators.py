"""
Validadores customizados para dados brasileiros.
"""
import re
from typing import Optional


def validate_cpf(cpf: str) -> bool:
    """
    Valida CPF brasileiro.
    
    Args:
        cpf: String com CPF (pode conter pontuação)
    
    Returns:
        True se válido, False caso contrário
    
    Examples:
        >>> validate_cpf("123.456.789-09")
        True
        >>> validate_cpf("12345678909")
        True
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Valida primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 11 - (soma % 11)
    digito1 = 0 if digito1 > 9 else digito1
    
    if int(cpf[9]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 11 - (soma % 11)
    digito2 = 0 if digito2 > 9 else digito2
    
    return int(cpf[10]) == digito2


def validate_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ brasileiro.
    
    Args:
        cnpj: String com CNPJ (pode conter pontuação)
    
    Returns:
        True se válido, False caso contrário
    """
    # Remove caracteres não numéricos
    cnpj = re.sub(r'\D', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Valida primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    digito1 = 0 if digito1 > 9 else digito1
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    digito2 = 0 if digito2 > 9 else digito2
    
    return int(cnpj[13]) == digito2


def validate_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: String com email
    
    Returns:
        True se válido, False caso contrário
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Remove caracteres perigosos de uma string.
    
    Args:
        text: Texto a sanitizar
        max_length: Tamanho máximo
    
    Returns:
        Texto sanitizado
    """
    if not text:
        return ""
    
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    # Trim
    text = text.strip()
    
    # Limita tamanho
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def is_valid_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Valida se senha atende requisitos de segurança.
    
    Args:
        password: Senha a validar
    
    Returns:
        Tupla (é_válida, mensagem_erro)
    """
    if len(password) < 8:
        return False, "Senha deve ter no mínimo 8 caracteres"
    
    if not any(char.isdigit() for char in password):
        return False, "Senha deve conter pelo menos um número"
    
    if not any(char.isupper() for char in password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
    
    if not any(char.islower() for char in password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
    
    # Opcional: caracteres especiais
    # if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
    #     return False, "Senha deve conter pelo menos um caractere especial"
    
    return True, None
