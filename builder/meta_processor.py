import os
import re
from utils import unoparser
from utils import ptlog as pt
from markvan import parser

def process_file_meta(lines: list[str], file_path: str):
	"""
	1. Поэтапно собирает метаданные:
	- В начале файла (###) 
	- Титульный комплекс (***) + дата.
	- Загружает из внешнего файла.
	2. Выделяет тело документа.

	"""
	title_data = {}
	internal_data = {}
	external_data = {}
	
	idx = 0
	total_lines = len(lines)
	# ===
	# ЭТАП 1: Чтение и вырезание машинной шапки ### (Абсолютный приоритет)
	if total_lines > 0 and lines[0].strip() == "###":
		hash_block_lines = []
		idx = 1  # Начинаем со второй строки
		stop_markers = ("___", "***", "^^^", '"""', "===", "---")
		
		while idx < total_lines:
			line = lines[idx].strip()
			if any(line.startswith(m) for m in stop_markers):
				if line.startswith("___"):
					idx += 1  # Пропускаем разделительную черту '___'
				break
			hash_block_lines.append(lines[idx])
			idx += 1
			
		if hash_block_lines:
			internal_data = unoparser.parse_uno_to_dict("\n".join(hash_block_lines))

	# ===
	# ЭТАП 2: Поиск титульного комплекса *** (Цикл на 30 строк)
	search_limit = min(idx + 30, total_lines)
	for scan_idx in range(idx, search_limit):
		
		strip_line = lines[scan_idx].strip()
		
		if strip_line[:3] in parser.MARKERS_HEADING or strip_line[:2] in parser.MARKERS_INCL:
			# Это значит, что маркер заголовка внутри включения или нарушены рекомендации стандарта по его расположению.
			break
		if strip_line == "***":
			# Мы нашли маркер! Проверяем строки по принципу домино (вложенности)
			
			# 1. Строки НАД маркером (Идем снизу вверх: сначала Автор, потом Credits)
			if scan_idx - 1 >= idx:
				line_minus_1 = lines[scan_idx - 1].strip()
				if line_minus_1 and line_minus_1 != "___":
					title_data["author"] = line_minus_1
					
					# Ищем credits ТОЛЬКО если нашли автора
					if scan_idx - 2 >= idx:
						line_minus_2 = lines[scan_idx - 2].strip()
						if line_minus_2 and line_minus_2 != "___":
							title_data["credits"] = line_minus_2

			# 2. Строки ПОД маркером (Идем сверху вниз: сначала Название, потом Жанр)
			if scan_idx + 1 < total_lines:
				line_plus_1 = lines[scan_idx + 1].strip()
				if line_plus_1:
					title_data["title"] = line_plus_1
					
					# Ищем жанр ТОЛЬКО если нашли название
					if scan_idx + 2 < total_lines:
						line_plus_2 = lines[scan_idx + 2].strip()
						if line_plus_2:
							title_data["genre"] = line_plus_2

			# Сдвигаем ползунок idx, полностью отрезая весь этот блок от художественного тела
			idx = scan_idx + 3
			break
	# ===
	# ЭТАП 2.5: Прицельный поиск года по последней непустой строке
	detected_year = _extract_year_from_last_line(lines)
	if detected_year:
		title_data["date"] = detected_year

	# ===
	# ЭТАП 3: Чтение внешнего файла meta.uno (Средний приоритет)
	current_dir = os.path.dirname(file_path)

	meta_uno_path = os.path.join(current_dir, "meta.uno")
	if os.path.exists(meta_uno_path):
		try:
			with open(meta_uno_path, 'r', encoding='utf-8') as f:
				external_data = unoparser.parse_uno_to_dict(f.read())
		except Exception:
			pass

	# ===
	# ЭТАП 4: Финальный мердж (Титульник -> meta.uno -> Шапка ###)
	final_meta = {}
	final_meta.update(title_data)     # 1. Неточные метаданные
	final_meta.update(external_data)  # 2. Точные из внешнего файла
	final_meta.update(internal_data)  # 3. Точные из шапки

	# Чистое тело произведения
	clean_body_lines = lines[idx:]

	if "title" not in final_meta:
		final_meta["title"] = os.path.basename(file_path).replace(".text", "")

	return final_meta, clean_body_lines




def _extract_year_from_last_line(lines: list[str]) -> str:
	"""
	Прицельно проверяет только самую последнюю непустую строку файла.
	Если там обнаруживается год — возвращает его, иначе пустую строку.
	"""
	# Ищем последнюю непустую строку
	for i in range(len(lines) - 1, -1, -1):
		last_line = lines[i].strip()
		if not last_line:
			continue
			
		# Если строка длиннее 20 символов — это точно художественный текст, а не дата
		if len(last_line) > 20:
			return ""
			
		clean = last_line.lower().rstrip('.')
		markers = ['г', 'год', 'гг', 'y', 'year', 'yy']
		
		# Проверка 1: Заканчивается на маркер (г., год)
		ends_with_marker = any(clean.endswith(m) for m in markers)
		# Проверка 2: Состоит строго из 4 цифр (1800-2099)
		is_four_digits = bool(re.match(r'^(18|19|20)\d{2}$', last_line))
		
		if ends_with_marker or is_four_digits:
			return last_line
			
		# Наткнулись на текст — значит даты в конце файла нет
		break
		
	return ""
