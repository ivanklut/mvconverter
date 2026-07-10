import os
import re
from html import escape as escape_html

from utils import fileio
from utils import ptlog as pt

def render_book_page(body_content: str, metadata: dict, theme_path: str) -> str:
	"""
	Шаблонизатор книги.
	Файл темы template_book.html
	Слепо находит {{переменные}} в HTML-шаблоне и берёт их значения из метаданных
	"""

	# === Шаг 1. Подготовка шаблона.
	# Ищем файл шаблона книги в папке темы
	themplate_path = os.path.join(theme_path, "template_book.html")

	template_html = fileio.read_text_file(themplate_path)
	template_html = "\n".join(template_html) # конвертируем в строку
	if not template_html:
		pt.wrn('Шаблон отсутствует!', 'Выдан голый контент')
		return body_content


	# === Шаг 2. Встраивание.
	# ВАЖНО: Сразу безусловно заменяем тело документа, так как это системная переменная
	final_html = template_html.replace('{{content}}', body_content)

	# Заменяем заглушки в шаблоне данными 
	# 2. РЕГУЛЯРКА-ИСКАТЕЛЬ: ищет любые конструкции {{слово}}
	# ([a-zA-Z0-9_\-]+) — ловит буквы, цифры, дефисы и нижние подчеркивания
	VARIABLE_REGEX = re.compile(r'\{\{\s*([a-zA-Z0-9_\-]+)\s*\}\}')

	# Локальная функция-заменитель для re.sub
	def replace_match(match):
		var_name = match.group(1) # Получаем чистое имя переменной (например, "author")
		
		# Ищем значение переменной в словаре метаданных книги
		if var_name in metadata:
			# Обязательно экранируем кастомные строки автора для безопасности HTML
			return escape_html(str(metadata[var_name]))
		
		# Если автор шаблона попросил переменную, которой нет в метаданных книги.
		return f"{{{{[Wrn] {var_name} не найдена!}}}}"

	# 3. Запускаем глобальную замену всех найденных тегов на лету!
	final_html = VARIABLE_REGEX.sub(replace_match, final_html)

	return final_html


