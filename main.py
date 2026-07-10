import os

import config_loader  # Загрузчик конфигурации


from utils import ptlog as pt
from utils.vfs import VirtualFileSystem

from builder import book_builder    # Сборщик документа
from builder import site_builder   # Построитель сайта


def main():
	pt.bgn('Старт Маркван-конвертера')	
	
	# === 
	# Шаг 1: Инициализация и валидация конфигурации
	pt.run('Инициализация параметров') 
	
	config_path = os.path.join(os.getcwd(), 'config.uno')
	cfg = config_loader.load_and_validate_config(config_path)	
	if not cfg:
		# Вся диагностика уже вывелась внутри лоадера, просто тихо выходим
		return	

	pt.fin('Инициализация окончена')

	# === Шаг 2: Создание и наполнение исходными данными виртуальной файловой системы
	pt.run('Создание и наполнение VFS')

	vfs = VirtualFileSystem()
	vfs.load_from_disk(cfg.input_path)

	pt.fin(f'VFS собрана (текстов: {vfs.get_texts_count()}, ресурсов: {vfs.get_assets_count()})')


	# === Шаг 3: Распределение задач по конвейерам сборки
	build_ok = False

	# --- А. Сборка книги
	if cfg.build_mode == 'book':
		pt.run("Старт сборки книги")

		build_ok = book_builder.build_book(vfs, cfg)

		if build_ok:
			pt.fin('Книга готова!')
		
	# --- Б. Сборка сайта
	elif cfg.build_mode == 'site':
		pt.run("Старт сборки сайта")

		build_ok = site_builder.build_site(vfs, cfg)

		if build_ok:
			pt.fin('Сайт готов!')
	# ___

	if build_ok:		
		pt.end('Маркван-конвертер завершил работу', f'Результат доступен в: {cfg.output_path}')
	else:
		pt.err('Конвертация не удалась')


if __name__ == "__main__":
	main()




