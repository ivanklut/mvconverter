import os

from utils import ptlog as pt

class VirtualFileSystem:
	"""
	Виртуальное плоское дерево проекта.
	Предназначено для упрощения кода — считываение происходит один раз в начале работы.
	Состоит из простых словарей:
	{relative_path: [string, string, ...], ...},  /// для файлов .text, .uno
	{relative_path: full_path, ...} /// для остальных	
	"""
	def __init__(self):
		self.texts = {} # Хранилище текстов - будущих страниц в виде: { '/виртуальный_путь.text': [список строк] }
		self.uno = {} # хранит только технические файлы (.uno)в виде: { '/виртуальный_путь.uno': [список строк] }.
		# Запись о путях остальных файлов: 		
		self.assets = {} # Структура: { '/виртуальный_путь_к_картинке.jpg': абсолютный_физический_путь_на_диске' }

	def get_texts_count(self) -> int:
		"""Возвращает количество загруженных текстовых файлов"""
		return len(self.texts)

	def get_assets_count(self) -> int:
		"""Возвращает количество проиндексированных медиа и внешних ресурсов"""
		return len(self.assets)
	
	def _debug_output(self):
		"""Отладочный вывод содержимого VFS в консоль"""
		pt.deb("Вывод проиндексированных текстов и ресурсов VFS")
		for virt_path in self.texts.keys():
			pt.deb("[VFS-Text]", f"Виртуальный путь: {virt_path}")
		for virt_path, real_path in self.assets.items():
			pt.deb("[VFS-Asset]", f"Виртуальный: {virt_path} -> Физический: {real_path}")

	def load_from_disk(self, input_path: str):
		"""
		Сканирует всю родительскую или целевую папку и загружает тексты в память.
		Для остальных файлов просто фиксирует их физические пути.
		"""
		input_path = os.path.abspath(input_path)
		
		# === ОПРЕДЕЛЯЕМ ЗОНУ СКАНИРОВАНИЯ:
		# Если это файл, то базовым проектом и зоной поиска является его родительская папка
		if os.path.isfile(input_path):
			# Сохраняем базовый путь в self, чтобы не передавать аргументом
			self._project_dir = os.path.dirname(input_path)
		else:
			self._project_dir = input_path
			
		pt.inf(f"Считывается папка: {self._project_dir}")

		# === Поиск
		for root, dirs, files in os.walk(self._project_dir):
			# Защитный барьер: игнорируем системные папки результатов и тем оформления
			if any(p in root for p in ["_theme", ".theme", "theme_default"]):
				continue
				
			for f in files:
				full_file_path = os.path.join(root, f)
				# Передаем файл и общую базовую папку для правильного вычисления виртуального пути
				self._process_node(full_file_path)
				
		# Финальный вызов твоего нового отладочного блока, который мы написали шагом ранее
		#self._debug_output()
	


	def _process_node(self, full_path: str):
		"""Внутренний распределитель: раскладывает файлы по трем чистым корзинам"""
		rel_path = os.path.relpath(full_path, self._project_dir)
		virt_path = self._normalize_path(rel_path)
		
		lower_path = full_path.lower()

		try:
			# =========================================================================
			# ШЛЮЗ-ПЕРЕХВАТЧИК ДЛЯ СКРЫТЫХ ФАЙЛОВ И ПАПОК (KISS!)
			# =========================================================================
			# Разрезаем виртуальный путь по слэшам на чистые компоненты.
			# Из 'osnovnaya/.resources/.shablon.text' получим: ['osnovnaya', '.resources', '.shablon.text']
			path_parts = [p for p in virt_path.split("/") if p]
			
			# Датчик: если ХОТЬ ОДИН элемент пути начинается с точки — файл считается скрытым ресурсом!
			is_hidden_resource = any(part.startswith(".") for part in path_parts)
			
			if is_hidden_resource:
				# КОРЗИНА 3: Скрытый ресурс (отправляем в ассеты, память не тратим!)
				self.assets[virt_path] = full_path
				return # Мгновенно выходим, закрывая шлюз для Корзин 1 и 2!
			# =========================================================================

			# ДЛЯ ВСЕХ ОСТАЛЬНЫХ СТАНДАРТНЫХ ФАЙЛОВ:
			if lower_path.endswith('.text'):
				# КОРЗИНА 1: Чистый художественный контент
				with open(full_path, 'r', encoding='utf-8') as file:
					self.texts[virt_path] = file.read().splitlines()
					
			elif lower_path.endswith('.uno'):
				# КОРЗИНА 2: Чистые технические настройки проекта
				with open(full_path, 'r', encoding='utf-8') as file:
					self.uno[virt_path] = file.read().splitlines()
					
			else:
				# КОРЗИНА 3: Внешние сопутствующие ресурсы
				self.assets[virt_path] = full_path
		except Exception:
			pass


	def _normalize_path(self, v_path: str) -> str:
		"""
		Внутренний хелпер. Намертво чистит путь от невидимого мусора, 
		пробелов и гарантирует один ведущий слэш.
		"""
		return "/" + v_path.strip().replace("\\", "/").lstrip("/")


	def get_file_lines(self, v_path: str) -> list | None:
		"""
		Возвращает текстовые строки из памяти. 
		Если файла физически нет на складе VFS — возвращает None!
		"""
		clean_path = self._normalize_path(v_path)
		# Использован дефолтный возврат None, чтобы препарер сразу видел пустоту
		return self.texts.get(clean_path, None)


	def has_media(self, v_path: str) -> bool:
		"""Проверяет, существует ли картинка в проекте"""
		return self._normalize_path(v_path) in self.assets

	def get_real_media_path(self, v_path: str) -> str | None:
		"""Возвращает физический путь к картинке. Если файла нет — None"""
		return self.assets.get(self._normalize_path(v_path), None)


	def exists(self, v_path: str) -> bool:
		"""Проверяет существование любого файла (текста или ассета) в VFS"""
		clean_path = self._normalize_path(v_path)
		return (clean_path in self.texts) or (clean_path in self.assets)
