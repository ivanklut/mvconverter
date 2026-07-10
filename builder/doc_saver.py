import os
from utils import fileio
from utils import ptlog as pt
from utils import mintrslt




def save_book_package_to_disk(export_result: dict, vfs, cfg) -> bool:
	"""
	СТАДИЯ 1: СЕЙВЕР ОСНОВНОГО КОНТЕНТА.
	Только очищает папку dist/ и записывает основные файлы книги по подпапкам.
	"""

	# 1. Очищаем общую выходную папку ОДИН раз перед началом всей записи
	fileio.clear_folder(cfg.output_path)

	# 2. Вычисляем латинское имя файла книги (Берем [0] от кортежа!)
	doc_source_name = os.path.splitext(os.path.basename(cfg.input_path))[0]
	out_file_name = mintrslt.trslt(doc_source_name)

	# 3. Бежим прямо по плоским ключам ("ast", "html-body", "html", "epub", "pdf")
	for fmt, content in export_result.items():
		# Создаем персональную подпапку для формата (dist/html/, dist/ast/)
		format_dir_path = os.path.join(cfg.output_path, fmt)
		os.makedirs(format_dir_path, exist_ok=True)
		
		if fmt == 'html-body':
			file_name = f"{out_file_name}.html"
		else:
			file_name = f"{out_file_name}.{fmt}"
		output_file_path = os.path.join(format_dir_path, file_name)

		# =====================================================================
		# ВОЗВРАЩАЕМ ТВОЙ СВЯЩЕННЫЙ БЛОК УПАКОВКИ EPUB
		# =====================================================================
		if fmt == "epub" and isinstance(content, dict):
			import zipfile
			import io
			
			zip_buffer = io.BytesIO()
			epub_package = content
			
			# Фиксируем строгое время для всех файлов (Calibre это любит)
			zip_time = (2026, 1, 1, 0, 0, 0)
			
			with zipfile.ZipFile(zip_buffer, 'w') as z:
				# 1. mimetype — строго ПЕРВЫМ, БЕЗ сжатия и БЕЗ лишних байт!
				if "mimetype" in epub_package:
					mime_info = zipfile.ZipInfo('mimetype')
					mime_info.compress_type = zipfile.ZIP_STORED
					mime_info.date_time = zip_time
					mime_info.external_attr = 0o644 << 16
					
					mime_bytes = epub_package["mimetype"].encode('ascii')
					z.writestr(mime_info, mime_bytes)
					
				# 2. Упаковываем все остальные файлы сжатием DEFLATED
				for file_path, file_content in epub_package.items():
					if file_path in ["mimetype", "assets"]: 
						continue
						
					clean_path = file_path.replace('\\', '/')
					
					f_info = zipfile.ZipInfo(clean_path)
					f_info.compress_type = zipfile.ZIP_DEFLATED
					f_info.date_time = zip_time
					f_info.external_attr = 0o644 << 16
					
					if isinstance(file_content, str):
						raw_data = file_content.encode('utf-8')
					else:
						raw_data = file_content
						
					z.writestr(f_info, raw_data)
			
			# Перезаписываем локальную переменную готовыми сжатыми байтами архива!
			content = zip_buffer.getvalue()

		# =====================================================================
		# ЗАПИСЬ КОНТЕНТА НА ДИСК ПО ТИПУ ДАННЫХ
		# =====================================================================
		if isinstance(content, str):
			success_save = fileio.write_text_file(output_file_path, content)
		else:
			success_save = fileio.write_binary_file(output_file_path, content)

		if not success_save:
			pt.err(f"Не удалось записать контент формата {fmt.upper()}", output_file_path)
			return False
			
		pt.ok(f"Файл контента {fmt.upper()} успешно сохранен", output_file_path)
		
	return True





# ========


def copy_theme_styles(export_result: dict, cfg) -> bool:
	"""
	СТАДИЯ 3: СИНХРOНИЗАТОР СТИЛЕЙ И ШРИФТOВ ТЕМЫ ОФОРМЛЕНИЯ КНИГИ.
	Берет содержимое папки темы и копирует его в корень веб-формата книги (HTML/).
	Если папки темы не существует — молча пропускает шаг.
	"""
	# 1. Железный предохранитель: если путь к теме не задан или физически пуст — выходим
	if not getattr(cfg, "theme_path", None) or not os.path.exists(cfg.theme_path):
		return True

	# 2. ШЛАГБАУМ КНИГИ: Проверяем, есть ли в мешке результатов формат "html"
	# Если мы собираем ТОЛЬКО epub или fb2, то стили темы на диск книги писать не нужно!
	if "html" not in export_result:
		return True

	# 3. Вычисляем целевую папку формата на диске (workspace/doc_result/HTML)
	# Копируем тему напрямую в папку HTML книги, сохраняя её внутреннюю структуру
	target_theme_folder = os.path.join(cfg.output_path, 'HTML')
	
	fileio.copy_resources(cfg.theme_path, target_theme_folder)
	pt.ok('Стили темы скопированы в папку:',  target_theme_folder)
			
	return True



# Единый реестр защиты от повторного сжатия/копирования
_ALREADY_COPIED_ASSETS = set()

def clear_assets_registry():
	"""Очищает историю скопированных файлов перед новой сборкой."""
	global _ALREADY_COPIED_ASSETS
	_ALREADY_COPIED_ASSETS.clear()



def copy_document_media_assets(doc_obj, vfs, dest_root_path: str, current_page_virt_path: str = ""):
	"""
	УНИВЕРСАЛЬНЫЙ ЗАВХОЗ МЕДИАФАЙЛОВ.
	Берет связанные ассеты документа doc_obj, находит оригиналы в VFS,
	и копирует их на жесткий диск строго от указанного корня dest_root_path.
	"""
	linked_assets = getattr(doc_obj, 'linked_assets', [])
	if not linked_assets:
		return

	# Убираем дубликаты ссылок внутри одного документа
	try:
		unique_assets = list(set(linked_assets))
	except TypeError:
		unique_assets = []
		seen = set()
		for x in linked_assets:
			if x.address not in seen:
				seen.add(x.address)
				unique_assets.append(x)
	
	for link_obj in unique_assets:
		# === 0 Не копируем локальные ссылки .text, т.к. они образуют веб-страницы
		if getattr(link_obj, 'type', '') == 'local' and link_obj.address.endswith('.text'):
			continue

		# === 1. ПОИСК В VFS: Считаем виртуальный путь по сырому адресу автора

		# === 1. ПОИСК В VFS: Считаем виртуальный путь по сырому адресу автора
		# ИСПРАВЛЕНИЕ: Проверяем реальный текст адреса автора, а не флаг из ОЗУ!
		if link_obj.address.startswith("/") or not current_page_virt_path:
			full_v_asset_path = link_obj.address.replace("\\", "/")
		else:
			# Если относительная (без слэша) — честно склеиваем с русской папкой!
			clean_address = link_obj.address.lstrip("/\\")
			if current_page_virt_path.endswith('.text'):
				current_doc_dir = os.path.dirname(current_page_virt_path)
			else:
				current_doc_dir = current_page_virt_path
				
			full_v_asset_path = os.path.join(current_doc_dir, clean_address).replace("\\", "/")

		# === 2. СОХРАНЕНИЕ НА ДИСК ===========================================
		# Очищаем латинский слаг от ведущих слэшей для пути сохранения на диске сайта
		clean_v_slug = link_obj.slug_path.lstrip("/")
		full_dest_file_path = os.path.join(dest_root_path, clean_v_slug)

		# ---------------------------------------------------------------------
		# РЕЖИМ А: Стандартный поиск бинарного файла в ассетах VFS (Корзина 3)
		# ---------------------------------------------------------------------


		real_src_path = vfs.get_real_media_path(full_v_asset_path)

		if real_src_path and os.path.exists(real_src_path):
			# Железобетонная защита от повторного копирования
			if real_src_path in _ALREADY_COPIED_ASSETS:
				continue
			_ALREADY_COPIED_ASSETS.add(real_src_path)

			# Просто копируем файл (картинку, pdf, архив) с диска на диск
			if fileio.copy_file(real_src_path, full_dest_file_path):
				pt.inf("[+asset]", f"Локальный ресурс скопирован с диска: {clean_v_slug}")

		# ---------------------------------------------------------------------
		# РЕЖИМ Б: ПЛАН Б — Выгружаем Маркван-исходник живой главы прямо из ОЗУ!
		# ---------------------------------------------------------------------
		else:
			# Выделяем имя файла и его родительскую виртуальную папку
			vfs_dir = os.path.dirname(full_v_asset_path)
			file_name = os.path.basename(full_v_asset_path)
			
			# Если имя файла начинается с нашей технической точки скачивания исходника

			
			# Склеиваем чистый виртуальный ключ для проверки Корзины 1 (vfs.texts)
			pure_text_v_key = os.path.join(vfs_dir, file_name).replace("\\", "/")
			if not pure_text_v_key.startswith("/"):
				pure_text_v_key = "/" + pure_text_v_key

			# Заглядываем в твой плоский словарь сохранённых текстов в ОЗУ!
			if pure_text_v_key in vfs.texts:
				
				# Проверяем защиту от повторного создания файла
				if pure_text_v_key in _ALREADY_COPIED_ASSETS:
					continue
				_ALREADY_COPIED_ASSETS.add(pure_text_v_key)
				
				# Достаем массив строк этой главы из памяти VFS
				lines_array = vfs.texts[pure_text_v_key]
				
				# Склеиваем массив обратно в один монолитный Маркван-текст
				full_text_content = "\n".join(lines_array)
				
				# Принудительно создаем папки назначения на диске сайта, если их еще нет
				os.makedirs(os.path.dirname(full_dest_file_path), exist_ok=True)
				
				# Выгружаем данные из ОЗУ на жесткий диск готового сайта
				if fileio.write_text_file(full_dest_file_path, full_text_content):
					pt.ok(f"Исходник страницы успешно сгенерирован из ОЗУ: {clean_v_slug}")
		# =====================================================================
