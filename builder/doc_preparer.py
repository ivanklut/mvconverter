"""
Модуль builder/doc_preparer.py
Препроцессор разметки Маркван. Выполняет фазу макро-расширения до парсинга [INDEX].
Бесследно сшивает внешние и локальные встраивания нод, полностью растворяя скобки {{ ... }} [INDEX].
"""

import os
from utils import ptlog as pt
from builder import meta_processor

def prepare_document(v_file_path: str, vfs, cfg) -> dict:
	"""
	Главная точка входа препроцессора. 
	Проверяет файлы, отсекает метаданные *** и запускает сшивку вложений [INDEX].
	"""
	# 1. Безопасная проверка: существует ли файл в виртуальной памяти VFS [INDEX]
	if not vfs.exists(v_file_path):
		pt.err("Файл физически отсутствует в виртуальной памяти VFS", v_file_path)
		return None
		
	lines = vfs.get_file_lines(v_file_path)
	
	# 2. Метапроцессор отделяет глобальный блок *** от текстового тела книги [INDEX]
	main_meta, body_lines = meta_processor.process_file_meta(lines, v_file_path)
	
	# 3. Запускаем рекурсивный обход и сшивку всех блоков {{ ... }}
	final_lines_list = _resolve_embeddings(
		lines=body_lines, 
		v_file_path=v_file_path, 
		vfs=vfs, 
		history=[v_file_path]
	)

	# 4. Единственное законное место во всей системе, где строки превращаются в текст для Ядра [INDEX]
	full_markvan_text = "\n".join(final_lines_list)

	return {
		"markvan_text": full_markvan_text,
		"meta_data": main_meta
	}


def _resolve_embeddings(lines: list[str], v_file_path: str, vfs, history: list[str]) -> list[str]:
	"""
	Рекурсивный препроцессор. Жадно сматывает блоки {{ ... }}, 
	заменяя их живым хронологическим текстом автора [INDEX].
	"""
	inside_protected_block = False
	current_closing_marker = ""
	protection_rules = {"[/": "/]", "[`": "`]", "[&": "&]", "{$": "$}"}

	resolved_lines = []
	idx = 0
	total_lines = len(lines)

	while idx < total_lines:
		line = lines[idx]
		stripped = line.strip()

		# ШАГ 1: ЗАЩИТА — Пропускаем защищенные технические блоки без изменений [INDEX]
		if not inside_protected_block:
			for start_marker, end_marker in protection_rules.items():
				if stripped.startswith(start_marker):
					inside_protected_block = True
					current_closing_marker = end_marker
					break
			if inside_protected_block:
				resolved_lines.append(line)
				idx += 1
				continue
		else:
			if stripped.startswith(current_closing_marker):
				inside_protected_block = False
				current_closing_marker = ""
			resolved_lines.append(line)
			idx += 1
			continue

		# ШАГ 2: ПОИСК БЛОЧНОГО ВСТРАИВАНИЯ {{
		# Проверяем, что это СТАРТ блока, а не ленивая внутристрочная переменная {{key}} [INDEX]
		if stripped.startswith("{{") and not stripped.endswith("}}"):
			# Читаем мета-строку паспорта встраивания (отрезаем "{{")
			tech_string = stripped[2:].strip()
			
			# Извлекаем логический класс-режим (body или all) и #id
			parts = tech_string.split()
			raw_mode = parts[0].lower() if parts and not parts[0].startswith('#') else ""
			
			target_id = ""
			for p in parts:
				if p.startswith('#'):
					target_id = p[1:]
					break

			# ЖАДНЫЙ СБОР СТРОК ТЕЛА ВСТРАИВАНИЯ ДО ЗАКРЫВАШКИ }} [INDEX]
			embed_body_lines_raw = []
			scan_block_idx = idx + 1
			
			while scan_block_idx < total_lines:
				block_line = lines[scan_block_idx]
				if block_line.strip().startswith("}}"):
					scan_block_idx += 1 # Шагнули за закрывающую скобку
					break
				embed_body_lines_raw.append(block_line)
				scan_block_idx += 1

			# Выковыриваем целевой путь к файлу из строк с маркером |> [INDEX]
			target_file = ""
			for b_line in embed_body_lines_raw:
				if b_line.strip().startswith("|>"):
					target_file = b_line.strip()[2:].strip()
					break

			# ПРАВИЛА УМОЛЧАНИЙ МАРКВАНА:
			# Если указан ID ноды — по умолчанию забираем её целиком ("all") [INDEX]
			# Если указан просто файл — забираем только его текстовое тело ("body") [INDEX]
			mode = "body" if not target_id else "all"
			if raw_mode in ["all", "body"]:
				mode = raw_mode

			# Определяем источник строк: внешний файл или локальный текст
			source_lines = []
			next_history_path = v_file_path
			
			if target_file:
				# --- ВАРИАНТ А: ВСТРАИВАНИЕ ВНЕШНЕГО ФАЙЛА ---
				if target_file.startswith("/") or target_file.startswith("\\"):
					v_target_path = target_file
				else:
					v_current_dir = os.path.dirname(v_file_path)
					v_target_path = v_current_dir + "/" + target_file
				
				v_target_path = "/" + v_target_path.replace("\\", "/").lstrip("/")

				# Железобетонная защита от циклической рекурсии файлов [INDEX]
				if v_target_path in history:
					pt.err("Циклическая ссылка вложения файлов в VFS!", f"Пропуск: {target_file}")
					idx = scan_block_idx
					continue

				file_lines = vfs.get_file_lines(v_target_path)
				if file_lines is None:
					pt.wrn("Файл встраивания не найден в виртуальной памяти VFS", v_target_path)
					idx = scan_block_idx
					continue

				# Если импортируем весь файл в режиме body, отрезаем у него метаданные *** [INDEX]
				if not target_id and mode == "body":
					_, source_lines = meta_processor.process_file_meta(file_lines, v_target_path)
				else:
					source_lines = file_lines
					
				next_history_path = v_target_path
			else:
				# --- ВАРИАНТ Б: ТОЧЕЧНОЕ ЛОКАЛЬНОЕ ВСТРАИВАНИЕ ИЗ ТЕКУЩЕГО ФАЙЛА ---
				# Чтобы полностью исключить зацикливание, мы берем текущие строки [INDEX],
				# но гарантированно стираем саму текущую команду-триггер {{, которая нас вызвала! [INDEX]
				safe_lines = list(lines)
				safe_lines[idx] = "" 
				source_lines = safe_lines

			# МАНЕВР ВЫКУСЫВАНИЯ: если указан точечный #id ноды или целой секции главы [INDEX]
			if target_id:
				source_lines = _extract_node_by_id(source_lines, target_id, mode)

			# ГЛУБОКАЯ РЕКУРСИЯ: отправляем чистые добытые строки на раскрытие внутренних матрешек [INDEX]
			new_history = history + [next_history_path] if target_file else history
			nested_content = _resolve_embeddings(
				lines=source_lines, 
				v_file_path=next_history_path, 
				vfs=vfs, 
				history=new_history
			)
			
			# ТВОЙ ИДЕАЛЬНЫЙ ОБМАН: вклеиваем распарсенный контент, а скобки {{ и }} полностью ИСЧЕЗАЮТ [INDEX]!
			resolved_lines.extend(nested_content)
			
			# Сдвигаем главный индекс цикла сразу за закрывающую скобку }} [INDEX]
			idx = scan_block_idx
			continue

		# ШАГ 3: ОБЫЧНАЯ ТЕКСТОВАЯ СТРОКА ПРОЗЫ
		else:
			resolved_lines.append(line)
			idx += 1

	return resolved_lines


def _extract_node_by_id(lines: list[str], target_id: str, mode: str) -> list[str]:
	"""
	Сканирует строки, находит элемент с #target_id и вырезает его [INDEX].
	Умеет забирать как блочные включения [...], так и целые секции глав [INDEX]!
	"""
	total_lines = len(lines)
	found_start_idx = -1
	is_heading = False
	heading_marker = ""
	
	# Веса для определения логических границ глав
	heading_weights = {'part': 1, 'chapter': 2, 'header': 3, 'subheader': 4, 'h3': 5, 'h4': 6, 'h5': 7, 'h6': 8}
	markers_heading = {'^^^': 'part', '"""': 'chapter', '===': 'header', '---': 'subheader'}

	# Поиск начальной строки ноды по #ID
	for i in range(total_lines):
		clean_l = lines[i].strip()
		# Игнорируем технические команды встраивания, чтобы случайно не выкусить саму команду {{ [INDEX]
		if clean_l.startswith("{{"):
			continue
			
		if f"#{target_id}" in clean_l:
			found_start_idx = i
			prefix3 = clean_l[:3]
			if prefix3 in markers_heading:
				is_heading = True
				heading_marker = prefix3
			break
			
	if found_start_idx == -1:
		return []

	extracted = []

	# СЦЕНАРИЙ А: ВЫКУСЫВАЕМ ЦЕЛУЮ ГЛАВУ/СЕКЦИЮ (до следующего равного заголовка) [INDEX]
	if is_heading:
		current_kind = markers_heading[heading_marker]
		current_weight = heading_weights.get(current_kind, 99)
		
		# Заголовок двухстрочный по канону Марквана
		if mode == "all":
			extracted.append(lines[found_start_idx])
			if found_start_idx + 1 < total_lines:
				extracted.append(lines[found_start_idx + 1])
				
		scan_idx = found_start_idx + 2
		while scan_idx < total_lines:
			scan_clean = lines[scan_idx].strip()
			next_prefix3 = scan_clean[:3]
			if next_prefix3 in markers_heading:
				next_kind = markers_heading[next_prefix3]
				if heading_weights.get(next_kind, 99) <= current_weight:
					break # Встретилась следующая глава — стоп! [INDEX]
			extracted.append(lines[scan_idx])
			scan_idx += 1
			
		return extracted

	# СЦЕНАРИЙ Б: ВЫКУСЫВАЕМ ОБЫЧНЫЙ БЛОК ВКЛЮЧЕНИЯ [... ] [INDEX]
	start_line = lines[found_start_idx].strip()
	open_marker = start_line[:2]
	close_marker = ')]' if open_marker == '[(' else open_marker[::-1].replace('[', ']')
	if open_marker == '[$': close_marker = '$]'
	
	if mode == "all":
		extracted.append(lines[found_start_idx])
		
	scan_idx = found_start_idx + 1
	while scan_idx < total_lines:
		current_line = lines[scan_idx]
		if current_line.strip().startswith(close_marker):
			if mode == "all":
				extracted.append(current_line)
			break
		extracted.append(current_line)
		scan_idx += 1
		
	return extracted
