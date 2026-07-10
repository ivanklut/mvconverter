"""
Упрощённый конвертер для демо

"""

# import sys
# sys.path.append('.') 

from markvan import converter
from exporters.html import exporter_html

def markvan_to_html_live(markvan_text: str) -> str:
    """
    Прямой шлюз для textarea песочницы. 
    Без VFS, без конфигов, без Pygments. Только хардкорное AST-дерево!
    """
    try:
        # 1. Строим абстрактное синтаксическое дерево (AST)
        doc_obj = converter.convert_document(markvan_text=markvan_text, meta_data={})
        
        # 2. Напрямую вызываем чистый экспорт тела документа в HTML
        html_body = exporter_html.export_docbody_to_html(doc_obj)
        
        return html_body
        
    except Exception as e:
        return f"<pre style='color:red;'>[Ошибка Маркван-Парсера]: {str(e)}</pre>"
