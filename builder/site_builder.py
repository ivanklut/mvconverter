import os
import re


from utils import ptlog as pt
from utils.mintrslt import trslt
from utils import fileio
from utils import makeslug

from builder import doc_preparer
from builder import doc_saver
from builder import site_templater
from markvan import doc_aggregator
from exporters import doc_exporter
from markvan import converter




def build_site(vfs, cfg) -> bool:
	"""
	Сборщик сайта.
		-1 Создание виртуального дерева сайта
			- Выращивание дерева
			-> Обработчик документа	(doc_preparer)			
			- Формирование виртуальной страницы  /// В зависимости от роли
		-2 Обход дерева для создания навигации 
			- Сборка глобального меню
			- Сборка и встраивание меню списков
		-3. Создание и сохранение веб-страниц
			-> Конвертер
			-> Экспорт в html
			-> Шаблонизация
			-> Сохранение на диск
			-> Сохранение связанных файлов (assets) на диск
		-4 Копирование темы
	"""
	pt.run("Запуск сборщика Сайта")
	


	# === Проход 1: Сканирование VFS и выращивание иерархического дерева
	pt.run("Проход 1: Выращивание дерева страниц-контейнеров")

	# Создаем виртуальный корень сайта (Главная страница)
	site_root = WebPage(raw_name="root", virt_path="/", page_type='root')

	# Перебираем виртуальные пути исходного проекта.
	for virt_path in vfs.texts.keys():
		path_parts = [p for p in virt_path.split("/") if p]
		if not path_parts:
			continue
			
		current_webpage = site_root
		is_inside_hidden_folder = False  # Датчик служебной папки

		# --- Блок А: Выращиваем ветки (папки) нашего дерева
		for folder_name in path_parts[:-1]:

			if folder_name == "_theme":
				continue
			# ИСКЛЮЧЕНИЕ: если папка начинается с точки — взводим датчик,
			# но НЕ прерываем цикл, чтобы дерево могло закачть ресурсы!
			if folder_name.startswith('.'):
				is_inside_hidden_folder = True	

			# Вычисляем ключ-slug напрямую через функцию 
			folder_slug = makeslug.make_slug(folder_name)
			
			if folder_slug not in current_webpage.sub_pages:
				new_virt_path = current_webpage.virt_path + ("" if current_webpage.virt_path == "/" else "/") + folder_name
				
				# --- Явное определение типа папки
				if current_webpage.type in ["collection", "item"]:
					chosen_type = "item"
				# Тильда на первом месте, либо сразу после цифр сортировки.
				elif re.match(r'^\d*~', folder_name):
					chosen_type = "collection"
				else:
					chosen_type = "standalone"

				# Создаем узел, передавая ему вычисленный тип (даже если она скрытая)
				current_webpage.sub_pages[folder_slug] = WebPage(
					raw_name=folder_name, 
					virt_path=new_virt_path, 
					page_type=chosen_type, 
					parent=current_webpage
				)

			# Шагаем ползунком внутрь папки на каждом шаге цикла
			current_webpage = current_webpage.sub_pages[folder_slug]


		# --- Блок Б: Наполнение контентом

		# ЗАЩИТА: Если датчик взведен — этот текстовый файл служебный.
		# Мы категорически запрещаем генерировать из него HTML и наполнять контентом!
		if is_inside_hidden_folder:
			continue
		# Мы дошли до конца папок. В руках имя файла (.text)
		file_name = path_parts[-1]

		# ИСКЛЮЧЕНИЕ: Защита от скрытых файлов типа с точкой в начале
		if file_name.startswith('.'):
			continue
		
		# Подготавливаем контент (разделяем на метаинформацию и тело)
		doc_data = doc_preparer.prepare_document(virt_path, vfs, cfg)
		if not doc_data:
			continue

		# Обрабатываем файлы в зависимости от типа
		if current_webpage.type in ['root', 'standalone', 'collection']:
			current_webpage.meta_data = doc_data["meta_data"]
			current_webpage.markvan_text = doc_data["markvan_text"]


		elif current_webpage.type == 'item':
			# Создаем изолированный объект страницы для конкретного файла (стиха/повести)
			# Родитель для него — это сама папка-коллекция (current_webpage.parent), в которой он физически живет!
			item_page = WebPage(
				raw_name=file_name, 
				virt_path=virt_path, 
				page_type="item", 
				parent=current_webpage.parent
			)
			item_page.meta_data = doc_data["meta_data"]
			item_page.markvan_text = doc_data["markvan_text"]
			
			# Находим родительскую коллекцию (например, ~Моё)
			parent_collection = current_webpage.parent
			
			# И складываем этот стих/повесть в её внутренний архив под уникальным слагом файла
			parent_collection.collection_items[item_page.slug] = item_page

			
	pt.ok("Проход 1 завершен. Виртуальное дерево сайта успешно выращено в памяти!")
	
	
	# === ПРОХОД 2: РАБОТА АГРЕГАТОРОВ УРОВНЯ САЙТА

	# Мы рекурсивно проходим дерево и за один раз делаем два полезных дела: собираем глобальное меню и добавляем в концы файлов-списков перечни item`ов.
	pt.run("Проход 2: Сборка и встраивание локальных меню в Коллекции")
	# Реестр для глобального меню 
	global_menu_registry = []
	# Запускаем слепую рекурсию от самого корня сайта!
	_aggregate_menu(site_root, global_menu_registry)
	
	pt.ok("Проход 2 завершен. Все связи и меню навигации сохранены в память!")
	



	# === Проход 3: Финальная компиляция и выгрузка на жесткий диск
	fileio.clear_folder(cfg.output_path)

	# ОЧИСТКА РЕЕСТРА: Сбрасываем историю копирования картинок перед стартом рендера страниц!
	doc_saver.clear_assets_registry()

		# =========================================================================
	# ФИНАЛЬНЫЙ АККОРД: Накатываем общую папку темы сайта (_theme) в корень!
	# =========================================================================
	if hasattr(cfg, "theme_path") and os.path.exists(cfg.theme_path):
		pt.run("Синхронизация глобальной темы оформления сайта...")
		# Наша утилита copy_resources сама создаст папку _theme в корне сайта!
		fileio.copy_resources(cfg.theme_path, os.path.join(cfg.output_path, "_theme"))
	# =========================================================================


	pt.run("Проход 3: Финальная компиляция и выгрузка готовых страниц на диск")
	_render_page_tree(site_root, global_menu_registry, vfs, cfg)


	
	return True





class WebPage:
	"""Универсальный класс веб-страницы и контейнера."""
	def __init__(self, raw_name: str, virt_path: str, page_type: str, parent=None):
		self.raw_name = raw_name
		self.virt_path = virt_path
		self.parent = parent
		self.type = page_type  # root, standalone, collection, item	

		# Вычисляем имя html-страницы в зависимости от её типа
		if page_type == "root":
			self.html_name = "index.html"
			self.slug = "index"
		elif page_type == "item":
			self.slug = trslt(raw_name.replace(".text", ""))
			self.html_name = f"{self.slug}.html"
		else:
			self.slug = makeslug.make_slug(raw_name)
			self.html_name = f"{self.slug}.html"

		# Назначение веб-адреса (URL)
		if parent and parent.virt_path != "/":
			# имя родительского узла очищаем от расширения чтобы сформировать текущее имя в иерархии
			parent_dir_url = parent.url.replace(".html", "")
			self.url = f"{parent_dir_url}/{self.html_name}"

		else:
			# если корень
			self.url = self.html_name

		# Контент
		self.meta_data = {}
		self.markvan_text = ""
		self.sub_pages = {}         
		self.collection_items = {}  

		# =====================================================================
		# ИСПРАВЛЕННЫЙ РАСЧЕТ ВЛОЖЕННОСТИ И ПУТЕЙ СAЙТA (Железный контрак!)
		# =====================================================================
		# Считаем реальное количество слэшей в итоговом веб-адресе URL
		url_slash_count = self.url.count("/")
		
		# 1. Честная глубина для генератора меню (0 для корня, 1 для папки, 2 для вложенных)
		self.depth = url_slash_count
		
		# 2. Относительный префикс возврата в корень для калибратора путей
		self.base_path: str = "../" * url_slash_count if url_slash_count > 0 else ""
		
		# =====================================================================
		# 🗺️ ВЫЧИСЛЕНИЕ ЛАТИНСКОГО СЛАГА РОДИТЕЛЬСКОЙ ПАПКИ (ТВОЯ ФИЧА!)
		# =====================================================================
		# Если страница лежит глубоко (в URL есть слэши, например: 'osnovnaya_spetsifikatsiya/page.html')
		# Откусываем имя файла исходника, оставляя только директорию в VFS
		v_dir = os.path.dirname(self.virt_path).lstrip("/\\") if self.virt_path.endswith('.text') else self.virt_path.lstrip("/\\")
		
		if v_dir:
			# Латинизируем компоненты папки автора ОДИН РАЗ при рождении страницы!
			# Из '/2-Основная спецификация' получится: 'osnovnaya_spetsifikatsiya'
			self.dir_slug = "/".join([makeslug.make_slug(p) for p in v_dir.split("/") if p])
		else:
			# Если файл лежит в самом корне исходников
			self.dir_slug = ""
		# =====================================================================



def _render_page_tree(current_page: WebPage, global_menu_registry: list, vfs, cfg):
	"""
	Финальный рекурсивный процесс создания физического дерева сайта (Проход 3).
	"""	
	# === 1. Обработка контента текущей страницы через ядро в ОЗУ
	doc_obj = converter.convert_document(
		markvan_text=current_page.markvan_text, 
		meta_data=current_page.meta_data
	)
	doc_obj.dir_slug = current_page.dir_slug

	# === ШАГ 4: АГРЕГАЦИЯ И АНАЛИТИКА ДАННЫХ
	# Собираем оглавление, сноски
	# Заменяем переменные {{key}} в тексте
	doc_aggregator.process_document_aggregations(doc_obj)

	# === 2. Запуск Диспетчера Экспорта контента
	# Передаем уже готовое, посчитанное при рождении свойство current_page.base_path!
	export_result = doc_exporter.export_to_formats(
		doc_obj=doc_obj, 
		vfs=vfs,                     
		cfg=cfg,
		base_path=current_page.base_path,
		virt_path=current_page.virt_path               
	)
	# Вытаскиваем чистое HTML-«тело» из вернувшегося мешка результатов
	pure_html_body = export_result.get("html-body", "")

	# === 3. Напрягаем Шаблонизатор склеить "тело" с Мастер-Шаблоном сайта и Меню
	final_html_page = site_templater.render_site_page(
		body_content=pure_html_body,
		menu_data=global_menu_registry,
		current_page=current_page,
		doc_obj=doc_obj,
		cfg=cfg
	)
	
	# === 4. ЗАПИСЬ HTML НА ДИСК
	output_html_path = os.path.join(cfg.output_path, current_page.url)
	
	if fileio.write_text_file(output_html_path, final_html_page):
		pt.ok(f"Страница сайта создана на диске", output_html_path)
	else:
		pt.err(f"Не удалось записать страницу сайта", output_html_path)

	# === 5. ПЕРЕНОС И ОПТИМИЗАЦИЯ МЕДИАФАЙЛОВ (Вызов выделенного Завхоза!)
	# Передаем всю рутину с картинками в изолированный модуль
	# process_and_copy_page_assets(current_page, doc_obj, output_html_path, vfs, cfg)

	# Вместо старой process_and_copy_page_assets:
	doc_saver.copy_document_media_assets(
		doc_obj=doc_obj, 
		vfs=vfs, 
		dest_root_path=cfg.output_path,  # Скидывает все ассеты в латинский корень сайта!
		current_page_virt_path=current_page.virt_path
	)


	# === 6. ОПТИМИЗАЦИЯ ПАМЯТИ В VFS
	if current_page.virt_path in vfs.texts:
		vfs.texts[current_page.virt_path] = []  

	# === 7. РЕКУРСИВНЫЕ СПУСКИ ГЛУБЖЕ ПО ДЕРЕВУ ===
	for child_page in current_page.sub_pages.values():
		_render_page_tree(child_page, global_menu_registry, vfs, cfg)

	if current_page.type == "collection" and current_page.collection_items:
		for item_page in current_page.collection_items.values():
			_render_page_tree(item_page, global_menu_registry, vfs, cfg)




"""
Агрегаторы сайта
"""




def _aggregate_menu(current_page: WebPage, global_menu_registry: list):
	"""
	Внутренний рекурсивный агрегатор. 
	1. Собирает глобальное меню по коротким raw_name. 
	2. Генерирует локальные списки элементов на языке разметки Маркван.
	"""
	# ===
	# 1. Сборка данных для Главного Меню сайта (по короткому raw_name)

	if current_page.raw_name.startswith('.'):
		return

	if current_page.type in ["standalone", "collection"]:
		# Берем строго наименование папки/файла на диске, чтобы меню было коротким
		raw_name = current_page.raw_name
		page_title = makeslug.clean_sort_prefix(raw_name)

		global_menu_registry.append({
			"title": page_title,
			"url": current_page.url,
			"depth": current_page.depth,
			"slug": current_page.slug
		})

	# ===
	# 2. Агрегация локального меню Коллекций через МАРКВАН-РАЗМЕТКУ

	if current_page.type == "collection" and current_page.collection_items:

		# Запускаем сборку сетки-галереи на языке Маркван
		# Используем твой блочный маркер [.g-2-1 (сетка в две колонки, адаптивная)
		mv_lines = ["\n[.g-2-1"]

		for item_slug, item_page in current_page.collection_items.items():
			item_title = item_page.meta_data.get("title", item_page.raw_name.replace(".text", ""))

			# =================================================================
			# ИСПРАВЛЕНИЕ: Меняем внешний маркер |>> на наш локальный маркер |> !
			# И подставляем оригинальный адрес .text (чтобы сработала калибровка), 
			# либо его virt_path, смотря что у тебя сопряжено с link_obj.address!
			# =================================================================
			# Если в item_page.url уже лежит .html, а get_web_path ждет .text, 
			# лучше передать туда виртуальный путь исходника: item_page.virt_path
			mv_lines.append(f"- {item_title} |> {item_page.virt_path}")
			# =================================================================


		mv_lines.append(".]\n")

		# Склеиваем Маркван-блок в одну строку
		local_menu_markvan = "\n".join(mv_lines)

		# Приклеиваем Маркван-разметку в конец текста обложки!
		current_page.markvan_text += local_menu_markvan

	# ===
	# 3. Рекурсивный обход дерева дальше

	for child_page in current_page.sub_pages.values():
		_aggregate_menu(child_page, global_menu_registry)




# ===



















# def process_and_copy_page_assets(current_page, doc_obj, output_html_path, vfs, cfg):
# 	"""
# 	Завхоз медиафайлов сайта.
# 	"""
# 	linked_assets = getattr(doc_obj, 'linked_assets', [])
# 	if not linked_assets:
# 		return

# 	for link_obj in linked_assets:
		
# 		# =====================================================================
# 		# ИДЕАЛЬНЫЙ РАДИКАЛЬНЫЙ ФИЛЬТР (Убираем endswith('.text'))
# 		# =====================================================================
# 		# Если это обычная перекрёстная ссылка (local), ведущая на другую главу, 
# 		# её копировать на диск как файл контента не нужно — её сайт отрендерит сам.
# 		# Мы пропускаем ТОЛЬКО тип 'download' (и картинки, у которых тип тоже 'local', но они пройдут)!
# 		if getattr(link_obj, 'type', '') == 'local' and link_obj.address.endswith('.text'):
# 			continue
# 		# =====================================================================

# 		# 1. ПОИСК В VFS: Работаем СТРОГО С СЫРЫМ АДРЕСОМ (link_obj.address)
# 		clean_address = link_obj.address.lstrip("/\\")
		
# 		if getattr(link_obj, "is_absolute", False):
# 			full_v_asset_path = clean_address
# 		else:
# 			if current_page.type == "item":
# 				current_doc_dir = os.path.dirname(current_page.virt_path)
# 			else:
# 				current_doc_dir = current_page.virt_path
# 			full_v_asset_path = os.path.join(current_doc_dir, clean_address).replace("\\", "/")

# 		real_src_path = vfs.get_real_media_path(full_v_asset_path)

# 		# 2. СОХРАНЕНИЕ НА ДИСК
# 		if real_src_path and os.path.exists(real_src_path):
# 			if real_src_path in _ALREADY_COPIED_ASSETS:
# 				continue
				
# 			_ALREADY_COPIED_ASSETS.add(real_src_path)

# 			clean_v_slug = link_obj.slug_path.lstrip("/")
# 			full_dest_file_path = os.path.join(cfg.output_path, clean_v_slug)
			
# 			if fileio.copy_file(real_src_path, full_dest_file_path):
# 				pt.inf("[+asset]", f"Локальный ресурс скопирован в корень сайта: {clean_v_slug}")



