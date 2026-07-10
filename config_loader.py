import os

from utils import ptlog as pt
from utils import unoparser

class Config:
	"""Специализированный класс для хранения жестких опций проекта"""
	def __init__(self, data_dict: dict):
		self.available_theme_css = set()
		self.available_theme_js = set()
		# Цикл слепо превращает ключи словаря в свойства класса (cfg.имя_параметра)
		for key, val in data_dict.items():
			setattr(self, key, val)

	def __str__(self):
		lines = ["---------- CONFIG DEBUG ----------"]
		for key, value in self.__dict__.items():
			if key != 'data':
				lines.append(f"	{key}: {repr(value)}")
		lines.append("----------------------------------")
		return "\n".join(lines)

def load_and_validate_config(config_path: str) -> Config:
	"""
	Полный цикл загрузки, нормализации и жесткой валидации конфигурации.
	Включает автоматический отладочный вывод всех параметров.
	"""
	if not os.path.exists(config_path):
		pt.err('Конфигурационный файл config.uno не найден в корне проекта', config_path)
		return None

	try:
		with open(config_path, 'r', encoding='utf-8') as f:
			raw_text = f.read()
		parsed_data = unoparser.parse_uno_to_dict(raw_text)
		#pt.deb('parsed_data', parsed_data)
	except Exception as e:
		pt.err('Критическая ошибка при чтении файла конфигурации', str(e))
		return None

	if not parsed_data:
		pt.err('Файл конфигурации пуст или не содержит валидных данных UNO', config_path)
		return None

	# Создаем рабочий объект класса Config
	cfg = Config(parsed_data)

	# Нормализуем пути (чистим от кавычек и делаем железно абсолютными)
	if hasattr(cfg, 'input_path'):
		cfg.input_path = os.path.abspath(cfg.input_path.strip('"').strip())
	else:
		pt.err('В конфигурации отсутствует обязательный параметр input_path')
		return None

	if hasattr(cfg, 'output_path'):
		cfg.output_path = os.path.abspath(cfg.output_path.strip('"').strip())
	else:
		pt.err('В конфигурации отсутствует обязательный параметр output_path')
		return None

	if hasattr(cfg, 'theme_path'):
		cfg.theme_path = os.path.abspath(cfg.theme_path.strip('"').strip())

		# =====================================================================
		# 🗺️ МАНИФЕСТ АССЕТОВ: СКАНИРОВАНИЕ ТЕМЫ В ОЗУ (ВЫПОЛНЯЕТСЯ СТРОГО 1 РАЗ)
		# =====================================================================
		# 1. Собираем и проверяем папку CSS
		css_dir = os.path.join(cfg.theme_path, 'styles', 'css')
		if os.path.exists(css_dir) and os.path.isdir(css_dir):
			# Выгребаем плоский список только .css файлов
			cfg.available_theme_css = set(
				f for f in os.listdir(css_dir) 
				if os.path.isfile(os.path.join(css_dir, f)) and f.endswith('.css')
			)
		else:
			pt.wrn(f"Целевая папка стилей темы не найдена: {css_dir}", "CONFIG")

		# 2. Собираем и проверяем папку JS
		js_dir = os.path.join(cfg.theme_path, 'js')
		if os.path.exists(js_dir) and os.path.isdir(js_dir):
			# Выгребаем плоский список только .js файлов
			cfg.available_theme_js = set(
				f for f in os.listdir(js_dir) 
				if os.path.isfile(os.path.join(js_dir, f)) and f.endswith('.js')
			)
		else:
			pt.wrn(f"Целевая папка скриптов темы не найдена: {js_dir}", "CONFIG")
		# =====================================================================

	# Валидируем режим сборки
	if not hasattr(cfg, 'build_mode') or cfg.build_mode not in ['site', 'book']:
		pt.err('Неопределённая задача конвертации (build_mode должен быть site или book)', getattr(cfg, 'build_mode', 'None'))
		return None

	# Проверяем физическое наличие источника данных на диске
	if not os.path.exists(cfg.input_path):
		pt.err('Указанный источник контента (input_path) не найден на диске', cfg.input_path)
		return None



	# ===
	# Отладочный вывод в консоль всех параметров класса Config
	for key, value in cfg.__dict__.items():
		pt.inf(f"{key} = {value}")
	pt.ok('Конфигурация успешно загружена и проверена')
	

	return cfg