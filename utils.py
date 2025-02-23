from typing import Dict, Any

def format_analysis_response(analysis: str) -> Dict[str, Any]:
    """Форматирует ответ анализа в структурированный JSON"""
    try:
        sections = analysis.split('\n\n')
        response = {
            "matching_points": [],
            "discrepancies": [],
            "missing_points": [],
            "recommendations": []
        }
        
        current_section = None
        for section in sections:
            if "Соответствующие пункты:" in section:
                current_section = "matching_points"
            elif "Несоответствия:" in section:
                current_section = "discrepancies"
            elif "Пропущенные пункты:" in section:
                current_section = "missing_points"
            elif "Рекомендации:" in section:
                current_section = "recommendations"
            
            if current_section and section.strip():
                response[current_section].append(section.strip())
        
        return response
    except Exception as e:
        return {"error": f"Ошибка форматирования: {str(e)}"}

def validate_document_size(file_size: int, max_size: int = 10 * 1024 * 1024) -> bool:
    """Проверяет размер документа"""
    return file_size <= max_size 