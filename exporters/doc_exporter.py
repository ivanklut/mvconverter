import os
from utils import ptlog as pt
from utils import makeslug
from exporters.html import exporter_html

try:
	from weasyprint import HTML
	HAS_WEASY = True
except (ImportError, OSError):
	# OSError может вылететь на Windows, если пакет pip стоит, но системный GTK не найден!
	HAS_WEASY = False

	CURRENT_BASE_PATH = ""       # Сюда запишется возврат в корень (../../)
	CURRENT_DOC_DIR_SLUG = ""    # Сюда запишется латинское имя папки
	HIDE_COMMENTS = False  
	

def export_to_formats(doc_obj, vfs, cfg, base_path: str = "", virt_path: str = "") -> dict:
	""" 
	Мультиформатный экспорт в оперативной памяти.
	Аргументы:
		doc_obj (Document): Наполненный объект абстрактного документа (паспорт контента).
		formats (list): Список строк-маркеров затребованных форматов, например:
		                ['html-body', 'html', 'pdf', 'fb2', 'epub', 'ast', 'mvml']
		vfs (VFS): Ссылка на виртуальную файловую систему проекта (нужна для FB2/EPUB).
		cfg (Config): Глобальный объект конфигурации (отсюда экспортеры берут theme_path, 
		              input_path и кастомные флаги сборки).

	Возвращает:
		dict: Плоский словарь результатов, где ключом является имя формата,
		      а значением — готовый откомпилированный контент в памяти.
		      
		Пример структуры возвращаемого "мешка":
		{
			"ast":       "Текстовое дерево нод в формате AST...",
			"html-body": "<div>...чистое 'мясо' HTML-тегов статьи...</div>",
			"html":      "<!DOCTYPE html>...полная страница книги с шаблоном...",
			"fb2":       "<?xml version='1.0' encoding='utf-8'?>...готовый XML FB2...",
			"epub":      {словарь виртуального пакета файлов EPUB для ZIP-архива},
			"pdf":       b"\\x25\\x50\\x44\\x46... (Сырые байты PDF-файла в памяти)"
		}
	"""
	# Объявляем Python, что пишем данные в общие ячейки модуля
	global CURRENT_BASE_PATH, CURRENT_DOC_DIR_SLUG, HIDE_COMMENTS
		# 1. Запоминаем текущий base_path (../../) этой конкретной страницы!

	CURRENT_BASE_PATH = base_path

	HIDE_COMMENTS = getattr(cfg, 'hide_comments', False)

	# 2. Вычисляем латинскую папку текущей страницы (как мы и договаривались)
	CURRENT_DOC_DIR_SLUG = ""
	if virt_path:
		virt_dir = os.path.dirname(virt_path).lstrip("/\\") if virt_path.endswith('.text') else virt_path.lstrip("/\\")
		if virt_dir:
			CURRENT_DOC_DIR_SLUG = "/".join([makeslug.make_slug(p) for p in virt_dir.split("/") if p])
	


	# Вложенный словарь результатов для передачи наверх в main/saver
	export_result = {}

		# Список всех поддерживаемых расширений
	all_formats = ["ast", "html-body", "html", "pdf", "docx", "epub", "fb2"]
	
	# Собираем форматы, у которых в конфиге флаг ``true``. 
	formats_to_build = [fmt for fmt in all_formats if getattr(cfg, fmt, False)]
	if not formats_to_build:
		pt.err('Формат вывода результата не указан в файле настроек')
		return None
	

	for fmt in formats_to_build:
		
		if fmt == "ast":
			from exporters import exporter_ast
			final_content = exporter_ast.export_to_ast(doc_obj)
			# Для AST ассеты (картинки) не нужны — передаем пустой список
			export_result["ast"] = {
				"content": final_content, 
				"assets": []
			}
			
		# Хитрость в том, что мы генерируем PDF не напрямую, а конвертируем html.
		elif fmt in ["html-body", "html", "pdf"]:
			pure_html_body = exporter_html.export_docbody_to_html(doc_obj)
			
			# Упаковываем в структуру, т.к. форматов может быть несколько
			if fmt == "html-body":
				
				export_result["html-body"] = pure_html_body			
			if fmt in ["html", "pdf"]:
				# Запускаем шаблонизатор (doc_templater)
				from builder import doc_templater
				metadata = getattr(doc_obj, 'metadata', {})
				theme_path = cfg.theme_path
				final_html = doc_templater.render_book_page(
					body_content=pure_html_body,
					metadata=metadata,
					theme_path=theme_path
				)
				
				if fmt == "html":
					# Упаковываем в структуру
					export_result["html"] = final_html
					#? А где мы копируем саму тему???
				if fmt == "pdf":
					# Для PDF мы СЛЕПО берем тот же самый final_html, который только что получили!
					
					# Проверяем наличие WeasyPrint в системе
					if 'HAS_WEASY' in globals() and HAS_WEASY:
						try:
							# Создаем буфер для сырых байт PDF
							import io
							pdf_buffer = io.BytesIO()
							
							# Запускаем WeasyPrint прямо в памяти!
							# base_url смотрит на папку с текстом cfg.input_path, чтобы он без проблем нашел картинки!
							HTML(string=final_html, base_url=cfg.input_path).write_pdf(pdf_buffer)
							
							# Упаковываем сырые байты в пакет результатов для сейвера
							export_result["pdf"] = {
								"content": pdf_buffer.getvalue(), # Передаем СЫРЫЕ БАЙТЫ PDF-файла!
								"assets": [] # Для PDF картинки копировать на диск не нужно, они уже вшиты внутрь!
							}
							pt.ok("Печатный PDF-документ успешно сформирован в памяти")
						except Exception as e:
							pt.err(f"Ошибка компиляции WeasyPrint PDF: {e}")
							export_result["pdf"] = {"content": "", "assets": []}
					else:
						pt.wrn("Компилятор WeasyPrint недоступен в текущей системе! PDF пропущен.", "Билдер")
						export_result["pdf"] = {"content": "", "assets": []}

		elif fmt == "fb2":
			from exporters.exporter_fb2 import FB2Exporter
			
			fb2_renderer = FB2Exporter()
			final_content = fb2_renderer.export_to_fb2(doc_obj, vfs)
			# Упаковываем в твою умную структуру: берем ассеты напрямую из doc_obj!
			export_result["fb2"] = final_content
	
		elif fmt == "epub":
			from exporters.exporter_epub import EPUBExporter
			
			# 1. Создаем объект виртуального экспортера в памяти
			epub_renderer = EPUBExporter()
			
			# 2. Вызываем метод сборки пакета в памяти. Он возвращает словарь файлов!
			epub_package = epub_renderer.export_to_epub(doc_obj, vfs, cfg)
			
			# 3. Упаковываем весь этот мешок в наш универсальный результат
			export_result["epub"] = {
				"content": epub_package, # Передаем весь словарь виртуального пакета файлов!
				"assets": [] # Сразу отдаем пустой список, так как все картинки уже вшиты внутрь ZIP!
			}

	return export_result




def get_web_path(link_obj) -> str:
	"""
	УНИВЕРСАЛЬНЫЙ СКВОЗНОЙ КАЛИБРАТОР ПУТЕЙ (KISS).
	Собирает и относительные, и абсолютные ссылки строго в одном месте.
	"""


	# === ШАГ 1: ЖЕЛЕЗОБЕТОННЫЕ ФИЛЬТРЫ И ХЭШ-ЯКОРЯ ===
	if not link_obj:
		return "#"
		
	# Хэш-якоря страниц (#media) отдаем как есть, это дело браузера
	if str(link_obj.address).startswith("#"):
		return link_obj.address
		
	# === ШАГ 2: КЛАССИФИКАЦИЯ (Глобальная или Локальная) ===
	# Если ссылка внешняя (http/https) — полностью пропускаем её, отдавая как есть
	if link_obj.type not in ["local", "download"]:
		return link_obj.slug_path

	# === ШАГ 3: ОПРЕДЕЛЯЕМ МАРШРУТ (Абсолютная или Относительная у автора) ===
	raw_address = link_obj.address.replace("\\", "/").strip()
	is_author_absolute = raw_address.startswith("/")
	
	# Извлекаем базовый слаг, который приготовил Агрегатор
	slug_path = link_obj.slug_path.lstrip("/")

	# === ШАГ 4: СИНХРОНИЗАЦИЯ С ПРАВИЛOМ СХЛOПЫВАНИЯ СТРАНИЦ WEBPAGES ===
	# Это правило колдовства работает СТРОГО для текстовых файлов контента (.text)!
	# Картинки (.jpg, .png, .webp) и файлы на скачивание этот блок пролетают мимо без изменений!
	if link_obj.type == "local" and raw_address.endswith(".text"):
		

		# # -----------------------------------------------------------------
		# # КЕЙС А: АБСОЛЮТНАЯ ССЫЛКА АВТОРА (Начинается со слэша /)
		# # -----------------------------------------------------------------
		# if is_author_absolute:
		# 	# Для абсолютных ссылок нам абсолютно плевать на dir_slug Агрегатора!
		# 	# Мы берем чистый ОРИГИНАЛЬНЫЙ адрес автора, меняем расширение на .html
		# 	html_path = raw_address[:-5] + ".html"
			
		# 	# Расщепляем путь по слэшам на русские кусочки
		# 	raw_parts = [p for p in html_path.split("/") if p]
			
		# 	# Линейно переводим каждый русский кусочек в чистый латинский слаг.
		# 	# Твой makeslug.make_slug САМ внутри вызовет очистку от цифр '01-'!
		# 	url_parts = []
		# 	for p in raw_parts:
		# 		lat_slug = makeslug.make_slug(p)
		# 		url_parts.append(lat_slug)
			
		# 	# Применяем твое железное правило плоских страниц standalone
		# 	if len(url_parts) > 1:
		# 		url_parts[-2] = url_parts[-2] + ".html"
		# 		slug_path = "/".join(url_parts[:-1])
		# 	else:
		# 		slug_path = "/".join(url_parts)
				# -----------------------------------------------------------------
		# КЕЙС А: АБСОЛЮТНАЯ ССЫЛКА АВТОРА (Начинается со слэша /)
		# -----------------------------------------------------------------
		if is_author_absolute:
			# 1. Сначала берем оригинальный адрес КАК ЕСТЬ и режем по слэшам на чистые русские куски
			raw_parts = [p for p in raw_address.split("/") if p]
			
			# 2. Линейно переводим каждый чистый русский кусочек в латинский слаг.
			# Твой makeslug.make_slug работает со стерильными именами без расширений веба!

			url_parts = []
			for p in raw_parts:
				lat_slug = makeslug.make_slug(p)
				url_parts.append(lat_slug)
				
			# 3. И вот теперь, когда url_parts содержит чистую латиницу,
			# мы берем самый последний элемент (имя файла) и меняем ему расширение контента на .html!
			if url_parts:
				last_part = url_parts[-1]
				if last_part.endswith(".text"):
					url_parts[-1] = last_part[:-5] + ".html"
				elif not last_part.endswith(".html"):
					# На случай, если расширения вообще не было в адресе
					url_parts[-1] = last_part + ".html"
			
			# 4. Применяем твое железное правило плоских страниц standalone
			if len(url_parts) > 1:
				url_parts[-2] = url_parts[-2] + ".html"
				slug_path = "/".join(url_parts[:-1])
			else:
				slug_path = "/".join(url_parts)


		# -----------------------------------------------------------------
		# КЕЙС Б: ОТНОСИТЕЛЬНАЯ ССЫЛКА АВТОРА (Идёт из dir_slug Агрегатора)
		# -----------------------------------------------------------------
		else:
			html_slug = slug_path[:-5] + ".html" if slug_path.endswith(".text") else slug_path
			raw_parts = html_slug.split("/")
			
			# Линейно очищаем каждый компонент относительного пути от цифр '01-'
			url_parts = []
			for part in raw_parts:
				clean_part = makeslug.clean_sort_prefix(part)
				url_parts.append(clean_part)

			# Твое неизменяемое правило коллекций с тильдой ~
			if "~" in link_obj.address:
				orig_parts = [p for p in link_obj.address.split("/") if p]
				collection_idx = -1
				for idx, part in enumerate(url_parts):
					if idx < len(orig_parts) and "~" in orig_parts[idx]:
						collection_idx = idx
						break
				if collection_idx != -1 and len(url_parts) > (collection_idx + 2):
					item_file_name = url_parts[-1]
					url_parts = url_parts[:collection_idx + 1] + [item_file_name]
					slug_path = "/".join(url_parts)
				else:
					slug_path = "/".join(url_parts)
			# Обычное каноничное схлопывание папок
			else:
				if len(url_parts) > 1:
					url_parts[-2] = url_parts[-2] + ".html"
					slug_path = "/".join(url_parts[:-1])
				else:
					slug_path = "/".join(url_parts)

	# === ШАГ 5: ФИНАЛЬНАЯ СБОРКА ВЕБ-ПУТИ ===
	# Абсолютно любой локальный ассет (и текст, и картинки, и абсолютные, и относительные)
	# на финише склеивается с CURRENT_BASE_PATH (../../) текущей страницы!
	return f"{CURRENT_BASE_PATH}{slug_path}"
