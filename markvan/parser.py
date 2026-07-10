"""
parser.py
Главный управляющий цикл построчного синтаксического анализа разметки Маркван.
Строит AST-дерево. Управляет иерархией через стек разделов.
Для удобочитаемости разделил код в следующие файлы:
parser_nodes.py (Заголовки и секции, разделители, списки)
parser_incl.py (Блочные включения [X ... X])
parser_textlines.py (Вывления в текстовых строках термина, контекстной пары или абзаца)
parser_inline.py (Выделение внутри строк включений и стилей)
"""

import re
from utils import ptlog as pt

from markvan.models import Section
from markvan import parser_nodes
from markvan import parser_incl


def parse_body(lines: list[str], stack_sections: list = None) -> list:
	"""
	Главный парсер разметки Маркван.
	Обрабатывает последовательно по одной строке, но делегирует "жадный" сбор объекта другим функциям.
	Детектирование типа строки вынесено в отдельную подфункцию def detect_node_type.
	Поддерживает сквозной проброс стека для рекурсивной обработки.

	"""

	# Стек — это линейный массив, внутри него лежат только объекты Section.
	# Если стек отсутствет, значит функция запускается впервые 
	# и мы на самом верхнем уровне документа.
	if stack_sections is None:
		# Инициализируем базовый корень документа.
		root_section = Section(level=0)
		stack_sections = []
		stack_sections.append(root_section)

	line_num = 0
	total_lines = len(lines)

	while line_num < total_lines:
		current_line = lines[line_num]
		clean_current_line = current_line.strip()
		
		# Пропускаем пустые строки («вертикальный воздух» разметки)
		if not clean_current_line:
			line_num += 1
			continue
		
		# === ШАГ 1: ОПРЕДЕЛЕНИЕ ТИПА ТЕКУЩЕЙ СТРОКИ
		node_type, marker = detect_node_type(current_line)
		
		# === ШАГ 2: ПЕРЕДАЧА СООТВЕТСТВУЮЩЕМУ ОБРАБОТЧИКУ
		match node_type:
			case "GROUP_SPACER":
				line_num = parser_nodes.parse_gspacer(lines, line_num, stack_sections, marker)
			case "HEADING":
				line_num = parser_nodes.parse_heading(lines, line_num, stack_sections, marker)

			case "PAUSE":
				line_num = parser_nodes.parse_pause(lines, line_num, stack_sections)

			case "SEPARATOR":
				line_num = parser_nodes.parse_separator(lines, line_num, stack_sections)

			case "LIST_ITEM":
				line_num = parser_nodes.parse_list(lines, line_num, stack_sections, marker)

			case "INCL_START":
				line_num = parser_incl.parse_inclusion(lines, line_num, stack_sections, marker)

			case "ATTACHMENT":
				line_num = parser_nodes.parse_attachment(lines, line_num, stack_sections, marker)
			case "TEXT_LINE":
				line_num = parser_nodes.anayz_textline(lines, line_num, stack_sections)
			case _:
				# Защита от неизвестного маркера
				line_num += 1

	# Возвращаем наполненный текущий стек (или ноды из корня stack[0].nodes)
	return stack_sections[0].nodes

# ===
# Для detect_node_type

# Перечень соответствий текстовых маркеров заголовков и их системных имён
MARKERS_HEADING = {
	'^^^': 'part',
	'"""': 'chapter',
	'===': 'header', 
	'---': 'subheader', 
	'...': 'th3', 
	',,,': 'th4', 
	':::': 'th5', 
	';;;': 'th6',
}

# Быстрые маркеры начала блочных включений [X ... X]
MARKERS_INCL = {
	'[(': 'text', 
	'[=': 'pre', 
	'[&': 'code', 
	'[%': 'math', 
	'[|': 'table', 
	'[/': 'comment', 
	'[[': 'img', 
	'[`': 'notes', 
	'[.': 'group', 
	'[_': 'spoiler', 
	'[$': 'input',
	'{&': 'rawcode',
	'{§': 'embed'      # Динамические встраивания и блоки агрегации данных	
}

# Маркеры прикреплений (сноски и гиперссылки)
MARKERS_ATTACH = {
	'|*': 'footnote', 
	'|>>': 'link_glob',
	'|->': 'link_downl', 
	'|>': 'link_loc'
}
# Универсальное сито для списков Марквана. 
# Строго требует дефис в начале, валидный маркер и ОБЯЗАТЕЛЬНЫЙ пробел после него!
# (-#+пробел)  Дефис с буквами, точкой или скобкой (-буквы...) Иерархические автосписки (1.1.4.2.а))
# Ограничим общую длину технического маркера, например, 15-ю символами
LIST_MARKER_REGEX = re.compile(r'^-(?:[a-zA-Zа-яА-ЯёЁ]{1,4}[\.\)]|[0-9a-zA-Zа-яА-ЯёЁ\.\)]{1,15}|\#|\s)\s*')


def detect_node_type(line: str) -> tuple[str, any]:
	"""
	Определяет, содержит ли строка технический признак маркван-разметки.
	Возвращает кортеж: (Имя_Типа_Ноды, Служебный_Маркер)
	"""
	clean_line = line.strip()
	if not clean_line: 
		return "EMPTY", None
	
	if clean_line == ".[].":
		return "GROUP_SPACER", clean_line

	# Берем безопасные срезы разной длины для проверки префиксов
	prefix3 = clean_line[:3]
	prefix2 = clean_line[:2]
	prefix1 = clean_line[:1]

	# === Проверяем заголовки (^^^, """, ===)
	if prefix3 in MARKERS_HEADING:
		return "HEADING", MARKERS_HEADING[prefix3]
	
	# ===
	if prefix3 == '~~~':
		return "PAUSE", None
	
	# === Проверяем блочные включения ([(, [[, [&)
	if prefix2 in MARKERS_INCL:
		return "INCL_START", prefix2

	# === Проверяем признак элемента списка
	list_match = LIST_MARKER_REGEX.match(clean_line)
	if list_match:
		# Забираем сырой маркер автора вместе с его дефисом (например: "-", "-1.", "-a)")
		raw_marker = list_match.group(0).strip()
			
		# Просто возвращаем тип и сырой маркер. Всё! Никакой очистки на подлёте.
		return "LIST_ITEM", raw_marker
	
	# === Проверяем сноски и ссылки (|*, |>, |-> |>>)
	if prefix3 in MARKERS_ATTACH:
		return "ATTACHMENT", prefix3
	if prefix2 in MARKERS_ATTACH: 
		return "ATTACHMENT", prefix2

	# === Окончание раздела
	if clean_line == '___': 
		return "SEPARATOR", None

	# === ИНАЧЕ
	# Если ни один маркер не совпал — это предположительно абзац,
	# но может быть и контекстной парой и термином с определением.
	return "TEXT_LINE", None





