"""
Простая система логирования с использованием маркеров.
В листинге программы делаем вставки, например:
pt.bgn('Наша программа стартовала', f'С параметрами из {init_path}', False)
Признак типа сообщения передаём после точки, а в скобках событие(суть сообщения), затем подробная информация, в конце передаём булево значение для отображения файла из которого была вызвана функция (эти дополнительные параметры не обязательны).

Маркеры объединяют в логические пары. 
- Глобальный уровень (Начало/Конец всей утилиты):[BGN] ➔ [END]
	- begin — bgn — [BGN]
	- end   — end — [END]
- Локальный уровень (Старт/Финал крупного этапа):[RUN] ➔ [FIN]
	- run   — run — [RUN]
	- finish — fin — [FIN]

Отчёт о выполнении отдельных важных процедур:
- okey    — ok  — [Ok ] — успешное выполнение операции
- warning — wrn — [Wrn] — некритичная ошибка (программа продолжает работу)
- error   — err — [Err] — критическая ошибка, остановка процесса или пропуск шага

Прочие:
- info — i — [i] — информация

Дебаг:
- debug — dbg — [DBG] — для временного отображения отладочной информации

"""

import inspect
import os
import re
from datetime import datetime

# Коды цветов ANSI
fiol = '\x1b[38;5;54m' 
blue = '\x1b[38;5;109m'
green = '\x1b[38;5;107m'
#green_l = '\x1b[38;5;107m'
yellow = '\x1b[38;5;179m'
red = '\x1b[38;5;174m' 
grey = '\x1b[38;5;145m'
x = '\x1b[38;5;235m'
brown = '\x1b[38;5;94m'
RST = f'\033[0m'

LOG_FILE_PATH = "/app.log"
IGNORE_FILES = []
DEBUG_MODE = True

# --- ОЧИСТКА ФАЙЛА ПРИ СТАРТЕ ---
try:
	with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
		f.write(f"--- НОВЫЙ ЗАПУСК ПРОГРАММЫ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
except Exception:
	pass


# --- ВНУТРЕННИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def _get_caller_info():
	"""Определяет имя файла и уровень вложенности функций проекта"""
	try:
		stack = inspect.stack()
		
		# НАХОДИМ ПЕРВЫЙ ФАЙЛ СНАРУЖИ, КОТОРЫЙ ВЫЗВАЛ ПЕЧАТЬ
		caller_filename = ""
		start_index = 2
		
		for i, frame in enumerate(stack[2:], start=2):
			frame_file = os.path.basename(frame.filename)
			# ДОБАВЛЕНО ИСКЛЮЧЕНИЕ: файл не должен быть равен "pt.py"
			if frame_file and frame_file != "ptlog.py" and not any(x in frame.filename.lower() for x in ["python", "lib", "site-packages"]):
				caller_filename = frame_file
				start_index = i
				break
		
		# Если мы запускаем тест внутри самого pt.py, то внешних файлов не найдем.
		# В таком случае принудительно ставим имя "pt.py"
		if not caller_filename:
			caller_filename = "pt.py"
			start_index = 2
		
		# Теперь считаем глубину только от этого файла и глубже
		depth = 0
		for frame in stack[start_index + 1:]:
			frame_file = os.path.basename(frame.filename)
			if frame_file and not any(x in frame.filename.lower() for x in ["python", "lib", "site-packages"]):
				if frame.function != '<module>':
					depth += 1
					
		return caller_filename, depth
	except Exception:
		return "", 0

def _write_to_file(raw_string):
	try:
		clean_text = re.sub(r'\x1b\[[0-9;]*m|\033\[[0-9;]*m', '', raw_string)
		timestamp = datetime.now().strftime('%H:%M:%S')
		with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
			f.write(f"[{timestamp}] {clean_text}\n")
	except Exception:
		pass


def _log(marker_name, marker_label, color, event, message, show_file):
	filename, level = _get_caller_info()

	if filename.lower() in IGNORE_FILES:
		return

	if marker_name == 'dbg' and not DEBUG_MODE:
		return

	indent = '  ' * level
	marker_text = f'{color}{marker_label}{RST}'
	event_text = f' {event}' if event else ''
	message_text = f' {x}{message}{RST}' if message else ''
	file_context = f' {grey}[{filename}]{RST}' if (show_file and filename) else ''

	full_console_line = f'{indent}{marker_text}{event_text}{message_text}{file_context}'
	print(full_console_line)
	_write_to_file(full_console_line)


# --- ПУБЛИЧНЫЕ ФУНКЦИИ МОДУЛЯ ---

def bgn(event, message='', show_file=False): _log('bgn', '[BGN]', fiol, event, message, show_file)
def run(event, message='', show_file=True):  _log('run', '[RUN', blue, event, message, show_file)
def inf(event, message='', show_file=True):  _log('inf', '  (i)', green, event, message, show_file)
def ok(event, message='', show_file=True):   _log('ok',  '  -Ok', green, event, message, show_file)
def fin(event, message='', show_file=True):  _log('fin', 'FIN]', blue, event, message, show_file)
def wrn(event, message='', show_file=True):  _log('wrn', '[Wrn]', yellow, event, message, show_file)
def err(event, message='', show_file=True):  _log('err', '[Err]', red, event, message, show_file)
def end(event, message='', show_file=False): _log('end', '[END]', fiol, event, message, show_file)
def deb(event, message='', show_file=True):  _log('deb', '[Deb]', brown, event, message, show_file)



# ===
# Определение цветов

def print_colors():
	for i in range(256):
		color = (f'\x1b[38;5;{i}m')
		#print(f'\x1b[38;5;{i}m')
		#print(f'{color}{i} = test text 01234')
		print(f'{color}text {i:<4}{RST}  ', end='')
		# Каждые 8 цветов переносим строку
		if (i + 1) % 8 == 0:
			print()


# --- БЛОК ДЛЯ ТЕСТИРОВАНИЯ ВНУТРИ САМОГО ФАЙЛА ---
if __name__ == '__main__':
	# Имитируем структуру вложенности с помощью тестовых функций
	def test_submodule():
		ok("Подмодуль отработал успешно!")

	def test_main():
		bgn("СТАРТ ТЕСТИРОВАНИЯ ЛОГГЕРА")
		run("Выполнение первой тестовой задачи...")
		test_submodule() # Тут автоотступ сработает сам!
		deb("Это отладочный лог", "переменная=123")
		end("ТЕСТ ЗАВЕРШЕН")

	# Запускаем тестовые функции
	print_colors()
	test_main()
