import os
from utils import fileio
from utils import ptlog as pt
from exporters.html.exp_h_highlighter import PYGMENTS_LANGS
from exporters.html.exporter_html import MARKVAN_TO_HTML_TAG
# template_book.html — для одиночной книги.
# template_standalone.html — для обычной страницы сайта.
# template_collection.html — для обложки списка/архива.
# template_item.html — для конкретного стиха/статьи.

# Реестр подключаемых модулей (только имена файлов)
FEATURES_RESOURCES = {
	# Базовый стиль-заглушка для любых непредусмотренных языков программирования
	
	# Твои специфические стили
	"code-default": {"css": []},
	"code-markvan": {"css": ["css/highlighters/hg_markvan.css"]},
	"code-unotext": {"css": ["css/highlighters/hg_unotext.css"]},
	"code-*":       {"css": ["css/highlighters/hg_generic_code.css"]},
	"math-tex":     {"css": ["js/katex/katex.min.css"], "js": ["js/katex/katex.min.js"]},
	# "table-default": {"css": ["css/highlighters/table.css"]},
	# "table-freeze":
	# "table-stub":
	
	# Разные математические нотации и их движки
	"math-tex": {
		"css": ["js/katex/katex.min.css"],
		"js":  ["js/katex/katex.min.js"]
	},
	"math-asciimath": {
		"js":  ["js/asciimath/ASCIImathML.js"]
	}
}

#  Реестр доступных автопоключаемых стилей и скриптов


def render_site_page(body_content: str, menu_data: list, current_page, doc_obj, cfg) -> str:

	"""
	Главный Шаблонизатор Сайта.
	Берет голые HTML-теги тела страницы, склеивает с нужным шаблоном темы 
	и на лету настраивает относительные пути и дизайн-классы для body.
	"""
	# === 1. СТРАТЕГИЯ ВЫБОРА ШАБЛОНА (По твоей спецификации на будущее)
	# Пытаемся найти специализированный шаблон под тип страницы
	template_file_name = f"template_{current_page.type}.html"
	template_path = os.path.join(cfg.theme_path, template_file_name)
	
	# Если специального шаблона нет (или у пользователя дефолтная тема),
	# откатываемся на универсальный базовый шаблон standalone
	if not os.path.exists(template_path):
		template_path = os.path.join(cfg.theme_path, "template_standalone.html")
		
	# Если темы вообще нет на диске — выбрасываем защитную аварийную заглушку
	if not os.path.exists(template_path):
		pt.wrn("Шаблон темы оформления не найден. Использована базовая разметка.", template_path)
		mock_layout = "<html><head><title>{{title}}</title></head><body class='{{body_class}}'>{{menu}}{{content}}</body></html>"
		template_html = mock_layout
	else:
		# Читаем HTML-каркас темы оформления с диска (или VFS, если перенесем)
		with open(template_path, 'r', encoding='utf-8') as f:
			template_html = f.read()

	# === 2. МАТЕМАТИКА ОТНОСИТЕЛЬНЫХ ПУТЕЙ (Защита стилей темы от вложенности папок)
	# Если depth = 1 (корень), base_path = "". Если depth = 2 (proza/page.html), base_path = "../"
	base_path = getattr(current_page, "base_path", "")

	# === 3. ГЕНЕРАЦИЯ И СЕРВЕРНАЯ ПОДСВЕТКА ГЛОБАЛЬНОГО МЕНЮ
	html_menu = _generate_html_menu(menu_data, current_page) # Передаем объект целиком

	# === Шаг 4. СБОРКА ДИЗАЙН-КЛАССОВ ДЛЯ БОДИ (Твоя гениальная идея body class="slug")
	# На выходе получим, например: class="page-priklyucheniya type-standalone"
	body_class = f"page-{current_page.slug} type-{current_page.type}"

	# === Шаг 5. Подключение скриптов и стилей только для применяемых в документе.
	added_tags = []
	# Статистика по использованию включений в документе
	# Агрегатор собрал в doc.features = {'TableIncl': {'default', 'freeze'},'MediaIncl': {'image'}, ...}
	page_features = getattr(doc_obj, "features", {})
	# Сет-предохранитель от дублирования файлов между разными типами включений
	loaded_assets = set()
	# Перебираем имена классов Питона и списки их внутренних классов/типов
	# Cоглашение: имя файла состоит из стилей включения "incl-тип_включения-класс_включения"
	for node_tag, incl_classes in page_features.items():

		# Исключение в логике для кода, чтобы разные классы обрабатывались одним Pygments
		added_classes = set()
		for c_class in incl_classes:
			raw_class = str(c_class).strip().lower()

			if node_tag == "code" and raw_class in PYGMENTS_LANGS:
				added_classes.add("pygments")
			else:
				added_classes.add(raw_class)


		for c_class in added_classes:
			# 1. Сначала СЕЙЧАС ЖЕ проверяем базовый файл для ВСЕХ классов этого типа
			# (Например: "incl-grouping.css" или "incl-table.css")
			base_css = f'incl-{node_tag}.css'
			base_js  = f'incl-{node_tag}.js'
			
			if base_css in cfg.available_theme_css and base_css not in loaded_assets:
				loaded_assets.add(base_css)
				added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{base_css}">')

			if base_js in cfg.available_theme_js and base_js not in loaded_assets:
				loaded_assets.add(base_js)
				added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{base_js}"></script>')

			# 2. А теперь проверяем кастомный специфичный подкласс автора (если он не дефолтный)
			if c_class not in ["default", "none", ""]:
				spec_css = f'incl-{node_tag}-{c_class}.css'
				spec_js  = f'incl-{node_tag}-{c_class}.js'
				
				if spec_css in cfg.available_theme_css and spec_css not in loaded_assets:
					loaded_assets.add(spec_css)
					added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{spec_css}">')
				if spec_js in cfg.available_theme_js and spec_js not in loaded_assets:
					loaded_assets.add(spec_js)
					added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{spec_js}"></script>')

	

		# # --- КЕЙС 1: Работаем с объектами ТАБЛИЦ (TableIncl)
		# if incl_type == "TableIncl":
		# 	# Базовый CSS таблиц нужен всегда, если встретилась эта нода
		# 	css_file = "incl-table-.css"
		# 	if css_file and css_file not in loaded_assets:
		# 		loaded_assets.add(css_file)
		# 		added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{css_file}">')
		# 	# if js_file and js_file not in loaded_assets:
		# 	# 	loaded_assets.add(js_file)
		# 	# 	added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')
			
		# # --- КЕЙС 2: Работаем с МЕДИА-включениями (MediaIncl)
		# elif incl_type == "MediaIncl":
		# 	for i_class in incl_classes:
		# 		if i_class == "image":
		# 			css_file = "incl-media-image.css"
		# 			if css_file and css_file not in loaded_assets:
		# 				loaded_assets.add(css_file)
		# 				added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{css_file}">')
		# 			js_file = "incl-media-image.js"
		# 			if js_file and js_file not in loaded_assets:
		# 				loaded_assets.add(js_file)
		# 				added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')

		# 		# elif sub == "video":
		# 		# 	# А для видео — полноценный плеер!
		# 		# 	js_player = "js/auto/players/video-plyr.js"
		# 		# 		added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/{js_player}"></script>')


		# # --- КЕЙС 3: Работаем с объектами ПОДСВЕТКИ КОДА (CodeIncl)
		# elif incl_type == "CodeIncl":
		# 	for i_class in incl_classes:
		# 		if i_class == "default":
		# 			continue
		# 		elif i_class in ['text', 'uno', 'unos', 'unom']:
		# 			css_file = f"incl-code-{i_class}.css"
		# 			if css_file and css_file not in loaded_assets:
		# 				loaded_assets.add(css_file)
		# 				added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{css_file}">')
		# 			# if js_file and js_file not in loaded_assets:
		# 			# 	loaded_assets.add(js_file)
		# 			# 	added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')

		# 		elif i_class == 'mermaid':
		# 			js_file = "incl-code-mermaidmin.js"
		# 			if js_file and js_file not in loaded_assets:
		# 				loaded_assets.add(js_file)
		# 				added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')
		# 			js_file = "incl-code-mermaid.js"
		# 			if js_file and js_file not in loaded_assets:
		# 				loaded_assets.add(js_file)
		# 				added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')



				# else:
				# 	# Для всех остальных (python, c++) — pygments
				# 	css_file = "incl-code-pygments.css"
				# 	if css_file and css_file not in loaded_assets:
				# 		loaded_assets.add(css_file)
				# 		added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{css_file}">')
				# 	# if js_file and js_file not in loaded_assets:
				# 	# 	loaded_assets.add(js_file)
				# 	# 	added_tags.append(f'<script defer src="{{{{base_path}}}}_theme/js/{js_file}"></script>')


		# elif incl_type == "GroupingIncl":
		# 	css_file = "incl-grouping-.css"
		# 	if css_file and css_file not in loaded_assets:
		# 			loaded_assets.add(css_file)
		# 			added_tags.append(f'<link rel="stylesheet" href="{{{{base_path}}}}_theme/styles/css/{css_file}">')
					



	# Склеиваем всё накопленное для {{page_auto_assets}}
	page_auto_assets_html = "\n\t".join(added_tags)


	# === 6. ФИНАЛЬНАЯ ЗАМЕНА ПЛЕЙСХОЛДЕРОВ ВНУТРИ ШАБЛОНА
	# Вытаскиваем человеческий заголовок из метаданных страницы для тега <title>
	page_title = current_page.meta_data.get("title", current_page.raw_name.replace(".text", ""))

	output = template_html
	output = output.replace("{{page_auto_assets}}", page_auto_assets_html)
	output = output.replace("{{content}}", body_content)
	output = output.replace("{{menu}}", html_menu) 
	output = output.replace("{{body_class}}", body_class)
	output = output.replace("{{title}}", page_title)
	output = output.replace("{{base_path}}", base_path)
	
	return output





def _generate_html_menu(menu_data: list, current_page) -> str: # 1. Передаем объект страницы целиком вместо только url
	"""
	Внутренний помощник. Превращает плоский список global_menu_registry 
	в красивое многоуровневое HTML-меню на основе датчиков глубины (depth).
	Автоматически вшивает класс 'active' для серверной подсветки!
	"""
	if not menu_data:
		return ""

	html_lines = ["<nav class='main-menu'>", "<ul>"]
	current_level = 1
	
	# Вычисляем базовый префикс возврата в корень для текущей страницы
	# Если мы на глубине 3 (proza/razm/page.html), то base_prefix = "../../"
	base_prefix = getattr(current_page, "base_path", "")


	for item in menu_data:
		target_level = item["depth"] + 1

		if target_level > current_level:
			html_lines.append("\t" * current_level + "<ul>")
			current_level = target_level
		elif target_level < current_level:
			while current_level > target_level:
				html_lines.append("\t" * (current_level - 1) + "</ul></li>")
				current_level -= 1

		classes = []
		# Добавляем класс уровня
		classes.append(f"lev-{target_level}")

		# Проверяем на активность, сравнивая чистые относительные URL		
		if item["url"] == current_page.url:
			classes.append("active")

		li_class_attr = f' class="{" ".join(classes)}"'

		

		# 2. МОДИФИЦИРУЕМ СТРОКУ ССЫЛКИ: Приклеиваем base_prefix перед item['url']!
		# Теперь для глубокой страницы ссылка станет: href='../../priklyucheniya.html' - ИДЕАЛЬНО!
		correct_href = f"{base_prefix}{item['url']}"

		html_lines.append(f'\t<li{li_class_attr}><a href="{correct_href}">{item["title"]}</a>')
		
	while current_level > 0:
		html_lines.append("\t" * (current_level - 1) + "</ul>")
		current_level -= 1
		
	html_lines.append("</nav>")
	return "\n".join(html_lines)
