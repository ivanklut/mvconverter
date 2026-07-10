import os
import shutil
import stat
import time
from utils import ptlog as pt  # Наш красивый логгер рядом

def _remove_readonly(func, path, exception):
	"""Внутренний помощник для принудительного снятия защиты Windows 'Только для чтения'"""
	try:
		os.chmod(path, stat.S_IWRITE)
		func(path)
	except Exception as e:
		pt.wrn("Не удалось снять атрибуты файла", f"{path}: {e}", True)

def clear_folder(folder_path: str):
	"""Полностью и безопасно удаляет содержимое папки (Очистка result)"""
	if os.path.exists(folder_path):
		pt.inf("Очистка целевой папки...", f"Путь: {folder_path}")
		try:
			shutil.rmtree(folder_path, onexc=_remove_readonly)
			time.sleep(0.1)  # Пауза для Windows, чтобы освободить дескрипторы
			os.makedirs(folder_path, exist_ok=True)
			pt.ok("Папка успешно очищена")
		except Exception as e:
			pt.err("Ошибка при очистке папки", str(e), True)
	else:
		os.makedirs(folder_path, exist_ok=True)

def read_text_file(file_path: str) -> list[str]:
	"""Безопасно читает файл, убирает мусор Windows \\r и возвращает список строк"""
	if not os.path.exists(file_path):
		pt.err("Файл не найден", f"Путь: {file_path}", True)
		return []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			# Читаем весь текст и нормализуем переносы строк
			content = f.read().replace('\r\n', '\n').replace('\r', '\n')
			# Возвращаем в виде списка строк, сохраняя пустые для логики Марквана
			return content.split('\n')
	except Exception as e:
		pt.err("Не удалось прочитать файл", f"{file_path}: {e}", True)
		return []

def write_text_file(file_path: str, content: str) -> bool:
	"""Записывает человеческий текст (HTML, TXT) в кодировке UTF-8"""
	try:
		dir_name = os.path.dirname(file_path)
		if dir_name: os.makedirs(dir_name, exist_ok=True)
			
		with open(file_path, 'w', encoding='utf-8') as f: # Режим 'w' (text)
			f.write(content)
		return True
	except Exception as e:
		pt.err("Ошибка записи текстового файла", f"{file_path}: {e}", True)
		return False


def write_binary_file(file_path: str, content: bytes) -> bool:
	"""Записывает сырые байты (PDF, DOCX, EPUB, Картинки) «как есть»"""
	try:
		dir_name = os.path.dirname(file_path)
		if dir_name: os.makedirs(dir_name, exist_ok=True)
			
		with open(file_path, 'wb') as f: # Режим 'wb' (binary). encoding запрещен!
			f.write(content)
		return True
	except Exception as e:
		pt.err("Ошибка записи бинарного файла", f"{file_path}: {e}", True)
		return False


def copy_resources(src_path: str, dest_folder_path: str) -> bool:
	"""
	Копирует физический файл (картинку, музыку, чертеж) или целую папку.
	Если целевой папки на диске еще не существует — создает её автоматически!
	"""
	try:
		# Железное правило: перед тем как копировать, проверяем и создаем 
		# всю цепочку целевых папок на диске, если их еще нет!
		if dest_folder_path:
			os.makedirs(dest_folder_path, exist_ok=True) # Папка img/ родится сама!

		# Если копируем одиночный файл (картинку)
		if os.path.isfile(src_path):
			shutil.copy2(src_path, dest_folder_path) # copy2 сохраняет дату создания файла
		else:
			# Если копируем целую папку (например, тему оформления _theme/)
			# Специфика shutil.copytree требует, чтобы целевой папки НЕ было, 
			# поэтому для папок логика чуть отличается, но суть та же
			shutil.copytree(src_path, dest_folder_path, dirs_exist_ok=True)
			
		return True
	except Exception as e:
		pt.err("Ошибка при физическом копировании ресурсов", f"Из {src_path} в {dest_folder_path}: {e}")
		return False

# def copy_file(src_file_path: str, dest_file_path: str) -> bool:
# 	"""
# 	Копирует одиночный физический файл с принудительным переименованием.
# 	На вход принимает ПОЛНЫЙ путь к исходному файлу и ПОЛНЫЙ путь к новому файлу на конце.
# 	Если целевой папки на диске еще не существует — создает её автоматически!
# 	"""
# 	try:
# 		# 1. Извлекаем из полного пути файла только путь его папки
# 		dest_folder = os.path.dirname(dest_file_path)
		
# 		# 2. Железное правило: автоматически создаем цепочку папок (img/), если их нет
# 		if dest_folder:
# 			os.makedirs(dest_folder, exist_ok=True)

# 		# 3. Физически копируем файл по точному адресу назначения.
# 		# В отличие от копирования в папку, shutil.copy2 примет dest_file_path 
# 		# как точное новое имя файла и запишет его поверх старого, если он там был!
# 		shutil.copy2(src_file_path, dest_file_path)
# 		return True
        
# 	except Exception as e:
# 		pt.err("Ошибка при физическом копировании и переименовании файла", f"Из {src_file_path} в {dest_file_path}: {e}")
# 		return False


from utils import image_optimizer

def copy_file(src_file_path: str, dest_file_path: str) -> bool:
	"""
	Умное копирование файла. 
	Копирует оригинал автора под транслитерированным именем.
	Если это картинка — дополнительно нарезает её на лёгкие WebP-пресеты.
	"""
	try:
		dest_folder = os.path.dirname(dest_file_path)
		if dest_folder:
			os.makedirs(dest_folder, exist_ok=True)

		# 1. ОБЯЗАТЕЛЬНО КОПИРУЕМ ИСХОДНИК АВТОРА
		# Он запишется под своим чистым английским именем, например, site/img/mauerlat.png
		shutil.copy2(src_file_path, dest_file_path)

		# Извлекаем имя файла и его расширение для проверки на графику
		file_name_with_ext = os.path.basename(dest_file_path) # Имеем "mauerlat.png"
		slug_name, ext = os.path.splitext(file_name_with_ext)  # Распилился на "mauerlat" и ".png"

		# Список расширений, которые мы автоматически оптимизируем в WebP
		GRAPHIC_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']

		if ext.lower() in GRAPHIC_EXTENSIONS:
			# === 2. ДОПОЛНИТЕЛЬНО ГЕНЕРИРУЕМ ЛЁГКИЕ ПРЕСЕТЫ ===
			# Передаем: русский исходник, целевую папку сайта и чистое английское имя-слаг
			# Функция создаст mauerlat~view.webp, mauerlat~thumb.webp и т.д.
			image_optimizer.generate_image_presets(src_file_path, dest_folder, slug_name)
			
		return True
        
	except Exception as e:
		pt.err("Ошибка при копировании/оптимизации файла", f"Из {src_file_path} в {dest_file_path}: {e}")
		return False
