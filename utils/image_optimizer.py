import os
from PIL import Image
# Предполагаем, что утилита вывода pt импортирована
# from utils import pt 

# Четкие настройки наших пресетов (Ширина, Качество сжатия WebP)
# Ограничивающий контейнер: максимальный размер по длинной стороне и качество
PRESETS_CONFIG = {
    "thumb":    {"max_side": 300,  "quality": 75},
    "view":     {"max_side": 800,  "quality": 82},
    "flscreen": {"max_side": 1920, "quality": 88}
}

def generate_image_presets(src_file_path: str, dest_folder_path: str, slug_name_no_ext: str) -> bool:
    """
    Создает легкие WebP-пресеты, автоматически вписывая изображение
    в ограничивающий контейнер по длинной стороне (и для вертикальных, и для горизонтальных фото).
    """
    if not os.path.exists(src_file_path):
        return False

    try:
        os.makedirs(dest_folder_path, exist_ok=True)

        with Image.open(src_file_path) as img:
            
            for preset_name, config in PRESETS_CONFIG.items():
                max_side = config["max_side"]
                quality_val = config["quality"]

                # Чтобы не испортить исходный объект в цикле, делаем чистую копию в памяти
                resized_img = img.copy()

                # УМНОЕ РЕШЕНИЕ: Задаем ограничивающий куб (max_side x max_side)
                # Метод thumbnail сам поймет, вертикальный файл или горизонтальный, 
                # и зажмет его по длинной стороне с сохранением пропорций автора!
                # Используем качественное сглаживание Resampling.LANCZOS
                resized_img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

                # Формируем имя файла: mauerlat~view.webp
                new_file_name = f"{slug_name_no_ext}~{preset_name}.webp"
                final_dest_path = os.path.join(dest_folder_path, new_file_name)

                # Сохраняем с поддержкой прозрачности (для PNG исходников)
                if resized_img.mode in ('RGBA', 'LA'):
                    resized_img.save(final_dest_path, "WEBP", quality=quality_val, lossless=False)
                else:
                    resized_img.save(final_dest_path, "WEBP", quality=quality_val)

        return True

    except Exception as e:
        print(f"Ошибка умной оптимизации изображения {src_file_path}: {e}")
        return False
