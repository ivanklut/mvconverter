import os
from utils import makeslug






# def get_web_path(link_obj, base_path: str = "", exporter_context=None) -> str:
# 	"""
# 	Универсальный сквозной калибратор путей.
# 	Приклеивает base_path (../) ТОЛЬКО к локальным абсолютным ссылкам проекта!
# 	Относительные локальные ссылки и глобальные (http) возвращает без изменений.
# 	"""
# 	if not link_obj:
# 		return "#"
		
# 	# 1. Проверяем тип ссылки		
# 	# 1. Если это локальная страница или файл на скачивание
# 	if link_obj.type in ["local", "download"]:
		
# 		# Извлекаем чистый латинский слаг пути (например: "osnovnaya_spetsifikatsiya/.../o_metadannyih.text")
# 		slug_path = link_obj.slug_path.lstrip("/")
		
# 		# === # СИНХРОНИЗАЦИЯ С ПРАВИЛOМ СХЛOПЫВАНИЯ СТРАНИЦ WEBPAGES
# 		# Если это обычная перекрёстная ссылка-переход (тип local) на .text-файл
# 		if link_obj.type == "local" and slug_path.endswith(".text"):
			
# 			# Сначала меняем техническое расширение на .html
# 			html_slug = slug_path[:-5] + ".html"
			
# 		# === # СИНХРОНИЗАЦИЯ С ПРАВИЛOМ СХЛOПЫВАНИЯ СТРАНИЦ WEBPAGES
# 		if link_obj.type == "local" and slug_path.endswith(".text"):
			
# 			# Сначала меняем техническое расширение на .html
# 			html_slug = slug_path[:-5] + ".html"
# 			url_parts = html_slug.split("/")
			
# 			# Начисто выжигаем технические цифры сортировки из всех компонентов
# 			url_parts = [makeslug.clean_sort_prefix(part) for part in url_parts]
			
# 			# ---	# ИСКЛЮЧЕНИЕ ДЛЯ ЭЛЕМЕНТОВ ХУДОЖЕСТВЕННЫХ КОЛЛЕКЦИЙ (item.text)
# 			# Вычисляем, на каком этаже сидит тильда ~ в оригинальном адресе автора
# 			orig_parts = [p for p in link_obj.address.split("/") if p]
# 			collection_idx = -1
# 			for idx, part in enumerate(url_parts):
# 				if idx < len(orig_parts) and "~" in orig_parts[idx]:
# 					collection_idx = idx
# 					break
			
# 			# УСЛОВИЕ АЙТЕМА: Тильда найдена, И после неё есть ЕЩЁ папки до самого файла!
# 			# (Например: .../3~Примеры/роман/стих.html)
# 			if collection_idx != -1 and len(url_parts) > (collection_idx + 2):
# 				item_file_name = url_parts[-1]
# 				# Оставляем всё до коллекции включительно + сам плоский айтем
# 				url_parts = url_parts[:collection_idx + 1] + [item_file_name]
# 				slug_path = "/".join(url_parts)

# 			# --- # СТАНДАРТНОЕ ПРАВИЛО ДЛЯ ОБЫЧНЫХ СТРАНИЦ И ОБЛОЖЕК КОЛЛЕКЦИЙ
# 			# Если тильды нет, ИЛИ тильда — это и есть предпоследний элемент (обложка списка!)
# 			else:
# 				if len(url_parts) > 1:
# 					# Имя родительской папки принудительно превращаем в .html файл
# 					url_parts[-2] = url_parts[-2] + ".html"
# 					# А имя самого файла полностью выкидываем из маршрута
# 					slug_path = "/".join(url_parts[:-1])
# 				else:
# 					slug_path = "/".join(url_parts)

# 		# =====================================================================
# 		# Если ссылка относительная, и у рабочего в кармане лежит путь текущей папки!
# 		if not link_obj.is_absolute and exporter_context and getattr(exporter_context, 'current_doc_dir', ''):
# 			current_dir = exporter_context.current_doc_dir
# 			raw_address = link_obj.address.lstrip("/\\")
			
# 			# Склеиваем и превращаем ссылку в честную абсолютную виртуальную!
# 			full_virtual_address = os.path.join(current_dir, raw_address).replace("\\", "/")
# 			if not full_virtual_address.startswith("/"):
# 				full_virtual_address = "/" + full_virtual_address
				
# 			link_obj.address = full_virtual_address
# 			link_obj.is_absolute = True
			
# 			# Пересчитываем латинский слаг от корня сайта

# 			link_obj.slug_path = makeslug.make_slug(full_virtual_address)

			
# 			return f"{base_path}{slug_path}"
		
# 	else:
# 		return link_obj.slug_path


# def get_web_path(link_obj, base_path: str = "", exporter_context=None) -> str:
# 	"""
# 	Универсальный сквозной калибратор путей.
# 	"""
# 	if not link_obj:
# 		return "#"
		
# 	# Если ссылка глобальная (http://...) — возвращаем её как есть без изменений
# 	if link_obj.type not in ["local", "download"]:
# 		return link_obj.slug_path
		
# 	# 1. Извлекаем латинский слаг пути, который честно подготовило Ядро на Шаге 1
# 	slug_path = link_obj.slug_path.lstrip("/")
	
# 	# =====================================================================
# 	# СИНХРОНИЗАЦИЯ С ПРАВИЛOМ СХЛOПЫВАНИЯ СТРАНИЦ WEBPAGES
# 	# =====================================================================
# 	if link_obj.type == "local" and slug_path.endswith(".text"):
# 		html_slug = slug_path[:-5] + ".html"
# 		url_parts = html_slug.split("/")
		
# 		# Очищаем все папки от цифр сортировки "01-"
# 		url_parts = [makeslug.clean_sort_prefix(part) for part in url_parts]
		
# 		# Проверка А: Исключение для элементов художественных коллекций (item)
# 		if "~" in link_obj.address:
# 			orig_parts = [p for p in link_obj.address.split("/") if p]
# 			collection_idx = -1
# 			for idx, part in enumerate(url_parts):
# 				if idx < len(orig_parts) and "~" in orig_parts[idx]:
# 					collection_idx = idx
# 					break
			
# 			if collection_idx != -1 and len(url_parts) > (collection_idx + 2):
# 				item_file_name = url_parts[-1]
# 				url_parts = url_parts[:collection_idx + 1] + [item_file_name]
# 				slug_path = "/".join(url_parts)
# 			else:
# 				slug_path = "/".join(url_parts)
				
# 		# Проверка Б: Стандартное правило для обычных плоских страниц (standalone)
# 		else:
# 			if len(url_parts) > 1:
# 				url_parts[-2] = url_parts[-2] + ".html"
# 				slug_path = "/".join(url_parts[:-1])
# 			else:
# 				slug_path = "/".join(url_parts)

# 	# =====================================================================
# 	# ✨ ТВОЙ ЛИНЕЙНЫЙ МОСТ ПОДМЕШИВАНИЯ ТЕКУЩЕЙ ПАПКИ (KISS)
# 	# =====================================================================
# 	# Если ссылка автора изначально была относительной (без слэша на старте)
# 	if not link_obj.is_absolute and exporter_context:
# 		# Вытаскиваем из кармана экспортера очищенное имя текущей латинской папки
# 		# Например, 'osnovnaya_spetsifikatsiya' (мы его очистим от ведущих слэшей)
# 		current_dir = getattr(exporter_context, 'current_doc_dir', '').lstrip("/")
		
# 		# Если мы сидим внутри какой-то папки, и наш слаг ещё не содержит её имени
# 		if current_dir and not slug_path.startswith(current_dir):
# 			# В ОДНУ СТРОЧКУ подставляем название текущей папки перед адресом ссылки!
# 			# Было: 'razdelyi_i_zagolovki.html' -> Стало: 'osnovnaya_spetsifikatsiya/razdelyi_i_zagolovki.html'
# 			slug_path = f"{current_dir}/{slug_path}"

# 	# Все локальные веб-адреса сайта всегда собираются от единого корня готового проекта!
# 	return f"{base_path}{slug_path}"








# # def get_web_path(link_obj, base_path: str = "") -> str:
# # 	"""
# # 	Универсальный сквозной калибратор путей.
# # 	Приклеивает base_path (../) ТОЛЬКО к локальным абсолютным ссылкам проекта!
# # 	Относительные локальные ссылки и глобальные (http) возвращает без изменений.
# # 	"""
# # 	if not link_obj:
# # 		return "#"
		
# # 	# 1. Проверяем тип ссылки		
# # 	if getattr(link_obj, "type", "local") in ["local", "download"]:
# # 		# =====================================================================
# # 		# ТОЧНЫЙ ШЛАГБАУМ ПО ТВОЕМУ СОГЛАШЕНИЮ:
# # 		# =====================================================================
# # 		# Если автор написал ссылку от текущего файла (например, img/photo.jpg),
# # 		# то свойство is_absolute будет False. Мы ОСТАВЛЯЕМ её как есть!
# # 		if not getattr(link_obj, "is_absolute", False):
# # 			return getattr(link_obj, "slug_path", "")
			
# # 		# Если же ссылка абсолютная (от корня проекта), мы честно подкручиваем base_path (../)
# # 		slug_path = getattr(link_obj, "slug_path", "")
# # 		final_url = f"{base_path}{slug_path}"

# # 		if getattr(link_obj, "type", "local") == "local" and final_url.endswith(".text"):
# # 			final_url = final_url[:-5] + ".html"
			
# # 		return final_url
# # 		# =====================================================================
		
# # 	else:
# # 		# Для внешних ссылок (http, https) отдаем оригинальный глобальный адрес
# # 		return getattr(link_obj, "slug_path", "#")