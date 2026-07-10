import os


from utils import ptlog as pt
from builder import doc_preparer
from builder import doc_saver
from markvan import converter
from exporters import doc_exporter


def build_book(vfs, cfg) -> dict:
	"""
	Управляет сборкой и муьтиформатной конвертацией документа в памяти.
	"""

	# === Шаг 1. Подготовка единого текста и метаданных в памяти VFS.
	# 1.1. Вычисляем виртуальный путь к мастер-файлу от корня VFS
	v_master_path = "/" + os.path.basename(cfg.input_path)

	# 1.2. Передаем в подготовитель виртуальный путь, саму VFS и конфиг
	pt.inf("Передаём в подготовитель виртуальный путь:", f"{v_master_path}")
	prepared_data = doc_preparer.prepare_document(v_master_path, vfs, cfg)
	
	if not prepared_data:
		pt.err("Не удалось подготовить данные документа", v_master_path)
		return None
	
	# Раздельно Маркван-текст и метаданные
	markvan_text = prepared_data["markvan_text"]
	meta_data = prepared_data["meta_data"]

	pt.ok("Разделены метаданные (титульная информация) и содержимое книги", v_master_path)
	
	pt.run('Конвертация содержимого книги')
	# === Шаг 2: ВЫЗОВ ЯДРА (Один раз для всей сессии сборки).
	# Получаем чистое, универсальное Абстрактное дерево элементов в памяти!
	doc_obj = converter.convert_document(markvan_text=markvan_text, meta_data=meta_data)

	pt.fin('Получено абстрактное дерево документа')

	
	# === Шаг 3. Мультиформатный экспорт

	pt.run('Экспорт книги')
	export_result = doc_exporter.export_to_formats(
		doc_obj=doc_obj,
		vfs=vfs,                     # Передаем VFS на случай, если FB2/EPUB захотят читать файлы
		cfg=cfg                      # Сам конфиг на крайний случай, если экспортерам нужны специфические флаги
	)

	pt.fin("Экспорт книги завершен")


	# === Шаг 4. Сохранение документа и его окружения
	if export_result:
		pt.run('Сохранение книги, сопутствующих файлов и тем оформления')
		
		# 1. Записываем файлы (html, ast, fb2 и т.д.) через твой saver
		build_ok = doc_saver.save_book_package_to_disk(export_result, vfs, cfg)
		
		if build_ok:
			# Сбрасываем историю защиты от дублей перед каждым новым запуском сборщика книги
			# (Если эта функция объявлена внутри doc_saver)
			if hasattr(doc_saver, 'clear_assets_registry'):
				doc_saver.clear_assets_registry()

			# Пробегаемся по тем форматам, которые РЕАЛЬНО скомпилировались в мешке результатов
			for fmt in export_result.keys():		
				# Картинки на диск нужно копировать ТОЛЬКО для html и fb2!
				if fmt not in ["html", "html-body", "fb2"]:
					continue
					
				# Вычисляем папку конкретного формата (например, workspace/doc_result/HTML)
				folder_name = 'HTML' if fmt.lower() in ['html', 'html-body'] else fmt.upper()
				format_dir_path = os.path.join(cfg.output_path, folder_name)
				
				# =========================================================================
				# ОДИН ЕДИНСТВЕННЫЙ, ЧИСТЫЙ ВЫЗOВ УНИВЕРСАЛЬНОГО ЗАВХОЗА (KISS!)
				# =========================================================================
				# Никаких внешних циклов for link_item! 
				# Функция сама заглянет в doc_obj, сама уберет дубли и все скопирует!
				doc_saver.copy_document_media_assets(
					doc_obj=doc_obj, 
					vfs=vfs, 
					dest_root_path=format_dir_path,  # Папка конкретного формата
					current_page_virt_path=""         # Для автономной книги путь абсолютный
				)
				# =========================================================================

			# 3. Накатываем стили темы оформления
			doc_saver.copy_theme_styles(export_result, cfg)

		pt.fin('Данные сохранены!')
	else:
		build_ok = False

	return build_ok