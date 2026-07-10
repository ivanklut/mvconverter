"""
Модуль markvan/parser_attach.py
Обработчик строк-прикреплений (|*, |>, |>>).
Распределяет сноски в секции и привязывает ссылки к нодам по правилу FIFO.
"""

from markvan.models import Section, Attachment, Paragraph

def handle_attachment(lines: list[str], line_num: int, stack: list[Section]) -> int:
	"""
	Обрабатывает строки прикреплений.
	Сноски убирает в контекст секции, ссылки жадно крепит к последней ноде.
	Возвращает индекс следующей строки для главного цикла.
	"""
	current_line = lines[line_num]
	clean_line = current_line.strip()
	
	# Извлекаем маркер (|*, |>, |>>) и полезное содержимое строки
	parts = clean_line.split(maxsplit=1)
	marker = parts[0]
	content = parts[1] if len(parts) > 1 else ""
	
	# === СЦЕНАРИЙ А: ТЕЛО СНОСКИ (|*) ===
	if marker.startswith("|*"):
		# Выкусываем имя сноски (например, из "|*2" достаем "2", из "|**" достаем "**")
		footnote_name = marker[1:] 
		if not footnote_name:
			footnote_name = "*" # Дефолтное имя, если просто |*
			
		# Создаем объект прикрепления сноски
		attach_node = Attachment(type_="footnote", target=content)
		
		# По нашей договоренности: сноски складываем прямо в текущую секцию
		# Мы добавим в класс Section словарь self.footnotes = {} на этапе интеграции,
		# либо просто прикрепим её как ноду, но со специальным флагом.
		# Для простоты пока кладем в специальный реестр сносок текущей секции:
		current_section = stack[-1]
		if not hasattr(current_section, 'footnotes'):
			current_section.footnotes = {}
			
		current_section.footnotes[footnote_name] = attach_node
		return line_num + 1

	# === СЦЕНАРИЙ Б: ГИПЕРССЫЛКИ (|> и |>>) ===
	# Ссылки должны «жадно» прикрепиться к последней ноде контента в секции
	current_section = stack[-1]
	
	# Гарантия безопасности: если ссылке не к чему крепиться, создаем пустой абзац-заглушку
	if not current_section.nodes:
		current_section.nodes.append(Paragraph())
		
	target_node = current_section.nodes[-1]
	
	# Запускаем жадный цикл сбора ссылок, идущих подряд друг за другом
	scan_idx = line_num
	while scan_idx < len(lines):
		scan_line = lines[scan_idx].strip()
		if not scan_line:
			scan_idx += 1
			continue
			
		# Проверяем, является ли следующая строка ссылкой
		if scan_line.startswith("|>") or scan_line.startswith("|>>"):
			sub_parts = scan_line.split(maxsplit=1)
			sub_marker = sub_parts[0]
			sub_content = sub_parts[1] if len(sub_parts) > 1 else ""
			
			# Определяем тип ссылки
			link_type = "link_global" if sub_marker == "|>>" else "link_local"
			
			# Создаем объект ссылки
			link_attach = Attachment(type_=link_type, target=sub_content)
			
			# Записываем ссылку в список attachments целевой ноды (Paragraph или ListBlock)
			if hasattr(target_node, 'attachments'):
				target_node.attachments.append(link_attach)
				
			scan_idx += 1
		else:
			# Встретили обычный текст или заголовок — ссылки кончились
			break
			
	return scan_idx


def parse_attachment(lines: list[str], line_num: int, stack: list, marker: str) -> int:
	"""
	Универсальный цех обработки прикреплений.
	Сноски (|*) убирает в текущую секцию, а ссылки (|>, |>>) жадно вяжет к последней ноде контента.
	"""
	from markvan.models import Attachment, Paragraph
	
	current_line = lines[line_num]
	clean_line = current_line.strip()
	
	# Разрываем по первому пробелу
	parts = clean_line.split(maxsplit=1)
	actual_marker = parts[0]
	content = parts[1] if len(parts) > 1 else ""
	
	# СЦЕНАРИЙ А: ТЕЛО СНОСКИ (|*)
	if actual_marker.startswith("|*"):
		footnote_name = actual_marker[1:]
		if not footnote_name:
			footnote_name = "*"
			
		# Отрезаем звездочку от имени, если это нумерованная сноска вида "*9"
		if footnote_name.startswith('*') and len(footnote_name) > 1 and footnote_name[1:].isdigit():
			footnote_name = footnote_name[1:]
			
		attach_node = Attachment(type_="footnote", target=content)
		current_section = stack[-1]
		if not hasattr(current_section, "footnotes"):
			current_section.footnotes = {}
		current_section.footnotes[footnote_name] = attach_node
		return line_num + 1

	# СЦЕНАРИЙ Б: ГИПЕРССЫЛКИ (|> и |>>) — ЖАДНЫЙ СБОР ПО FIFO
	current_section = stack[-1]
	if not current_section.nodes:
		current_section.nodes.append(Paragraph())
		
	target_node = current_section.nodes[-1]
	scan_idx = line_num
	total_lines = len(lines)
	
	while scan_idx < total_lines:
		scan_line = lines[scan_idx].strip()
		if not scan_line:
			scan_idx += 1
			continue
			
		from markvan.parser_helpers import detect_node_type
		type_check, sub_info = detect_node_type(scan_line)
		
		if type_check == "ATTACHMENT" and not sub_info.startswith("|*"):
			sub_parts = scan_line.split(maxsplit=1)
			sub_marker = sub_parts[0]
			sub_content = sub_parts[1] if len(sub_parts) > 1 else ""
			
			link_type = "link_global" if sub_marker == "|>>" else "link_local"
			link_attach = Attachment(type_=link_type, target=sub_content)
			
			if hasattr(target_node, 'attachments'):
				target_node.attachments.append(link_attach)
			scan_idx += 1
		else:
			break
			
	return scan_idx
