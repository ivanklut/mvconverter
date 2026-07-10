import re
from utils.mintrslt import trslt


def clean_sort_prefix(raw_name: str) -> str:
	"""
	Чистит имя папки или файла от префиксов сортировки типа '1-', '02~' и лишних дефисов.
	Возвращает чистое русское (исходное) имя.
	"""
	clean_name = re.sub(r'^\d+[\-~]', '', raw_name).strip()
	clean_name = re.sub(r'^[\-~]', '', clean_name).strip()
	return clean_name

def make_slug(raw_name: str) -> str:
	"""
	Утилитарный помощник Билдера. 
	Чистит имя папки от префиксов сортировки и транслитерирует его в безопасный slug.
	"""
	# Вызываем нашу новую функцию очистки!
	clean_name = clean_sort_prefix(raw_name)
	
	# Возвращаем чистый латинский slug (например, "obo_mne")
	return trslt(clean_name)
