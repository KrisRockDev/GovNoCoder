# v3.6: Hotkeys, Individual Clears, UI Tweaks
import flet as ft
import os
from pathlib import Path
import logging
import pyperclip
import threading # For async operations
from typing import Set, Dict, Optional, List, Callable

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Starting Flet application v3.6...") # Обновлена версия

# --- Константы ---
TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".html", ".htm",
    ".css", ".js", ".csv", ".log", ".ini", ".cfg", ".xml", ".sh", ".bat",
    ".gitignore", ".dockerfile", "readme", ".env"
}
IGNORE_DIRS = {
    ".git", ".venv", "venv", ".vscode", ".idea", "node_modules", "__pycache__",
    "build", "dist", "target", ".pytest_cache", ".mypy_cache"
}
LAST_DIR_KEY = "last_directory_path_v3.6" # Обновлен ключ для избежания конфликтов
# Изменяем соотношение панелей на 20/80
LEFT_PANEL_EXPAND = 2  # Фиксированное соотношение: 20%
RIGHT_PANEL_EXPAND = 8 # Фиксированное соотношение: 80% (2 + 8 = 10 total)

# Стиль для placeholder текста
HINT_STYLE = ft.TextStyle(color=ft.colors.with_opacity(0.5, ft.colors.ON_SURFACE), italic=True)

# --- Функции ---

def is_likely_text_file(file_path: Path) -> bool:
    # ... (функция без изменений) ...
    if not file_path.is_file(): return False
    if IGNORE_DIRS.intersection(set(part.lower() for part in file_path.parts)): return False
    if any(part.startswith('.') and (file_path.parent / part).is_dir() for part in file_path.parts[:-1]): return False
    ext = file_path.suffix.lower()
    name_lower = file_path.name.lower()
    if name_lower in TEXT_EXTENSIONS or ext in TEXT_EXTENSIONS: return True
    if not ext or ext not in TEXT_EXTENSIONS:
        try:
            with file_path.open("r", encoding="utf-8", errors='ignore') as f: f.read(1024)
            return True
        except Exception: return False
    return False

# --- Основное приложение ---

def main(page: ft.Page):
    page.title = "File Content Aggregator v3.6" # Обновлен заголовок
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.window_width = 1300 # Немного увеличим ширину для кнопок
    page.window_height = 850 # Немного увеличим высоту для полей промпта

    # --- Состояние приложения ---
    selected_directory_text = ft.Text("Директория не выбрана", selectable=True, expand=True, no_wrap=True, tooltip="Выбранная директория")
    current_scan_path: Optional[Path] = None
    selected_paths: Set[Path] = set()
    expanded_nodes: Set[Path] = set()
    filter_text: str = ""

    # --- UI Компоненты ---

    # 1. Выбор директории и Запоминание (без изменений в логике)
    def load_app_state():
        nonlocal current_scan_path
        last_dir_str = page.client_storage.get(LAST_DIR_KEY)
        if last_dir_str:
            last_dir_path = Path(last_dir_str)
            if last_dir_path.is_dir():
                logging.info(f"Loaded last directory: {last_dir_path}")
                current_scan_path = last_dir_path
                selected_directory_text.value = f"Выбрано: {last_dir_str}"
                update_ui_after_selection()
            else:
                logging.warning(f"Last directory path not found or invalid: {last_dir_str}")
                page.client_storage.remove(LAST_DIR_KEY)
                clear_ui_on_error()
        else:
             clear_ui_on_error()

        if 'left_panel' in locals() and left_panel: left_panel.expand = LEFT_PANEL_EXPAND
        if 'right_panel' in locals() and right_panel: right_panel.expand = RIGHT_PANEL_EXPAND
        page.update() # Обновление после загрузки состояния

    def save_last_directory(path: Path):
        try:
             page.client_storage.set(LAST_DIR_KEY, str(path))
             logging.info(f"Saved last directory: {path}")
        except Exception as e:
             logging.error(f"Failed to save last directory: {e}")

    def pick_directory_result(e: ft.FilePickerResultEvent):
        nonlocal current_scan_path
        page.splash = ft.ProgressBar()
        page.update()
        if e.path:
            new_path = Path(e.path)
            if new_path.is_dir():
                selected_directory_text.value = f"Выбрано: {e.path}"
                current_scan_path = new_path
                logging.info(f"Directory selected: {current_scan_path}")
                save_last_directory(current_scan_path)
                selected_paths.clear()
                expanded_nodes.clear()
                filter_input.value = ""
                start_prompt_input.value = ""
                end_prompt_input.value = ""
                content_display.value = "" # Очищаем основное поле тоже
                update_ui_after_selection()
            else:
                 selected_directory_text.value = "Выбранный путь не является директорией."
                 current_scan_path = None
                 clear_ui_on_error()
        else:
            selected_directory_text.value = "Выбор директории отменен"
            if current_scan_path is None:
                 clear_ui_on_error()
        page.splash = None
        page.update()

    file_picker = ft.FilePicker(on_result=pick_directory_result)
    page.overlay.append(file_picker)

    # -- Кнопки Верхней Панели --
    # Определяем кнопки ДО их использования в layout и обработчиках
    pick_dir_button = ft.IconButton( # Изменено на IconButton
        icon=ft.icons.FOLDER_OPEN,
        tooltip="Выбрать директорию [Ctrl+O]",
        on_click=lambda _: file_picker.get_directory_path(dialog_title="Выберите директорию проекта"),
    )
    select_all_button = ft.IconButton(
        icon=ft.icons.SELECT_ALL,
        tooltip="Выбрать все видимые [Ctrl+A]",
        on_click=None, # Назначается позже
        disabled=True
    )
    deselect_all_button = ft.IconButton(
        icon=ft.icons.DESELECT,
        tooltip="Снять весь выбор [Esc]",
        on_click=None, # Назначается позже
        disabled=True
    )
    show_content_button = ft.IconButton( # Изменено на IconButton
        icon=ft.icons.VISIBILITY,
        tooltip="Показать/Собрать контент [Enter]",
        on_click=None,
        disabled=True,
    )
    refresh_button = ft.IconButton( # Изменено на IconButton
        icon=ft.icons.REFRESH,
        tooltip="Обновить дерево [Ctrl+R]",
        on_click=None,
        disabled=True,
    )
    copy_button = ft.IconButton(
        icon=ft.icons.CONTENT_COPY,
        tooltip="Копировать всё [Ctrl+C]",
        on_click=None,
        disabled=True,
    )
    # Кнопки очистки полей
    clear_start_prompt_button = ft.IconButton(
        icon=ft.icons.CLEAR, tooltip="Очистить начальный промпт", on_click=None, disabled=True, icon_size=16
    )
    clear_content_display_button = ft.IconButton(
        icon=ft.icons.CLEAR, tooltip="Очистить основное поле", on_click=None, disabled=True, icon_size=16
    )
    clear_end_prompt_button = ft.IconButton(
        icon=ft.icons.CLEAR, tooltip="Очистить конечный промпт", on_click=None, disabled=True, icon_size=16
    )
    clear_all_button = ft.IconButton( # Переименована из clear_content_button
        icon=ft.icons.CLEAR_ALL,
        tooltip="Очистить все поля [Ctrl+X]",
        on_click=None,
        disabled=True,
    )
    progress_ring = ft.ProgressRing(visible=False, width=16, height=16, stroke_width=2)


    # 2. Поиск/Фильтр (Левая панель)
    def handle_filter_change(e):
        nonlocal filter_text
        filter_text = e.control.value.lower()
        logging.info(f"Filter changed: '{filter_text}'")
        populate_tree_view()
        update_select_buttons_state() # Кнопки select/deselect теперь в верхней панели
        page.update()

    filter_input = ft.TextField(
        label="Фильтр дерева", hint_text="Введите часть имени...",
        prefix_icon=ft.icons.SEARCH, on_change=handle_filter_change,
        dense=True, filled=False, border_radius=5, text_size=13,
        hint_style=HINT_STYLE # Стиль для placeholder
    )

    # Функции select_all_visible и deselect_all теперь привязаны к кнопкам в верхней панели
    def select_all_visible(e):
        if not current_scan_path: return
        logging.info("Selecting all visible items...")
        visible_paths = get_current_visible_paths()
        for path in visible_paths:
             selected_paths.add(path)
        populate_tree_view() # Обновляем дерево для отображения галочек
        update_button_states() # Обновляем все кнопки
        page.update()

    def deselect_all(e):
        if not current_scan_path: return
        logging.info("Deselecting all items...")
        selected_paths.clear()
        populate_tree_view() # Обновляем дерево
        update_button_states() # Обновляем все кнопки
        page.update()

    select_all_button.on_click = select_all_visible
    deselect_all_button.on_click = deselect_all

    # select_buttons_row больше не нужен в левой панели

    def update_select_buttons_state():
        # Эта функция теперь часть общей update_button_states
        pass

    # 3. Кастомное Дерево Файлов (Левая панель - без изменений в логике)
    dir_tree_container = ft.ListView(expand=1, spacing=0, padding=ft.padding.only(top=5), auto_scroll=True) # Добавлен padding
    _current_visible_paths_cache: Set[Path] = set()

    def get_current_visible_paths() -> Set[Path]:
        return _current_visible_paths_cache

    def toggle_expand(e):
        node_path = e.control.data
        if node_path in expanded_nodes:
            expanded_nodes.remove(node_path)
            logging.debug(f"Node collapsed: {node_path}")
        else:
            expanded_nodes.add(node_path)
            logging.debug(f"Node expanded: {node_path}")
        populate_tree_view() # Перестраиваем дерево
        update_button_states() # Обновляем кнопки
        page.update()

    def checkbox_changed(e: ft.ControlEvent):
        item_path = e.control.data
        if e.control.value:
            selected_paths.add(item_path)
            logging.debug(f"Added to selection: {item_path}")
        else:
            selected_paths.discard(item_path)
            logging.debug(f"Removed from selection: {item_path}")
        update_button_states() # Обновляем кнопки

    def build_tree_node(item_path: Path, is_visible: bool, visible_paths_set: Set[Path]) -> Optional[ft.Control]:
        # ... (функция build_tree_node без изменений) ...
        if not is_visible: return None
        is_dir = item_path.is_dir(); is_expanded = item_path in expanded_nodes; is_selected = item_path in selected_paths
        expand_icon=None
        if is_dir: expand_icon = ft.IconButton(icon=ft.icons.ARROW_DROP_DOWN if is_expanded else ft.icons.ARROW_RIGHT, icon_size=18, tooltip="Развернуть/Свернуть", on_click=toggle_expand, data=item_path, style=ft.ButtonStyle(padding=0))
        else: expand_icon = ft.Container(width=24, height=24)
        checkbox = ft.Checkbox(value=is_selected, data=item_path, on_change=checkbox_changed)
        icon = ft.Icon(ft.icons.FOLDER if is_dir else ft.icons.INSERT_DRIVE_FILE_OUTLINED, size=16, opacity=0.8)
        text = ft.Text(item_path.name, size=12, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.BOLD if is_dir else ft.FontWeight.NORMAL)
        node_row = ft.Row([expand_icon, checkbox, icon, text], spacing=2, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=False)
        children_container = ft.Column(spacing=0, visible=is_dir and is_expanded)
        if is_dir and is_expanded:
            try:
                children = sorted(list(item_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
                for child_path in children:
                    child_visible = child_path in visible_paths_set; child_node = build_tree_node(child_path, child_visible, visible_paths_set)
                    if child_node: children_container.controls.append(ft.Container(content=child_node, padding=ft.padding.only(left=20)))
            except Exception as e: children_container.controls.append(ft.Text(f" Ошибка чтения: {e}", color=ft.colors.RED, size=10))
        return ft.Column([node_row, children_container], spacing=0)

    def filter_paths(base_path: Path, current_filter: str) -> Set[Path]:
        # ... (функция filter_paths без изменений) ...
        visible_paths = set()
        if not base_path or not base_path.is_dir(): return visible_paths
        try:
            all_items = list(base_path.rglob('*')); all_items.append(base_path)
            for item in all_items:
                if IGNORE_DIRS.intersection(set(p.lower() for p in item.parts)): continue
                try:
                    relative_parts = item.relative_to(base_path).parts
                    if any(p.startswith('.') and (base_path / Path(*relative_parts[:i+1])).is_dir() for i, p in enumerate(relative_parts)): continue
                except ValueError: pass
                common_parent = base_path
                try:
                    check_path = item.parent
                    while check_path != common_parent and check_path is not None and check_path.is_relative_to(common_parent):
                        if check_path.name.startswith('.'): break
                        check_path = check_path.parent
                    else: pass
                    if check_path != common_parent and check_path is not None and check_path.is_relative_to(common_parent): continue
                except Exception as path_err: logging.warning(f"Path check error for {item}: {path_err}")
                if not current_filter or current_filter in item.name.lower():
                    visible_paths.add(item); parent = item.parent
                    while parent is not None and parent.is_relative_to(base_path.parent) and parent != base_path.parent:
                         if IGNORE_DIRS.intersection(set(p.lower() for p in parent.parts)): break
                         try:
                             parent_relative_parts = parent.relative_to(base_path).parts
                             if any(p.startswith('.') and (base_path / Path(*parent_relative_parts[:i+1])).is_dir() for i, p in enumerate(parent_relative_parts)): break
                         except ValueError: pass
                         visible_paths.add(parent); parent = parent.parent
                    visible_paths.add(base_path)
        except PermissionError: logging.error(f"Permission denied while filtering paths under: {base_path}")
        except Exception as e: logging.error(f"Error filtering paths under {base_path}: {e}")
        return visible_paths

    def populate_tree_view():
        # ... (функция populate_tree_view без изменений в логике) ...
        nonlocal _current_visible_paths_cache
        logging.info(f"Populating tree view for: {current_scan_path} with filter: '{filter_text}'")
        dir_tree_container.controls.clear()
        if not current_scan_path or not current_scan_path.is_dir():
            dir_tree_container.controls.append(ft.Text("Директория не выбрана.", size=12))
            _current_visible_paths_cache = set()
            return
        visible_paths = filter_paths(current_scan_path, filter_text)
        _current_visible_paths_cache = visible_paths
        logging.info(f"Found {len(visible_paths)} visible items after filtering.")
        try:
            root_items = sorted([item for item in current_scan_path.iterdir() if item in visible_paths], key=lambda x: (not x.is_dir(), x.name.lower()))
            if not visible_paths and current_scan_path: message = f"Ничего не найдено по запросу '{filter_text}'." if filter_text else "Папка пуста или все отфильтровано."; dir_tree_container.controls.append(ft.Text(message, size=12))
            else:
                for item_path in root_items: node = build_tree_node(item_path, True, visible_paths); (dir_tree_container.controls.append(node) if node else None)
                if not root_items and visible_paths and filter_text: dir_tree_container.controls.append(ft.Text(f"Элементы найдены в подпапках.", size=12))
        except PermissionError: dir_tree_container.controls.append(ft.Text("Нет прав доступа к директории.", color=ft.colors.RED, size=12)); (page.show_snack_bar(ft.SnackBar(ft.Text(f"Нет прав доступа к {current_scan_path}"), open=True, bgcolor=ft.colors.RED_200)) if page else None)
        except Exception as e: dir_tree_container.controls.append(ft.Text(f"Ошибка построения дерева: {e}", color=ft.colors.RED, size=12)); logging.error(f"Error building tree: {e}")
        # Обновление кнопок происходит из вызывающей функции (update_ui_after_selection, refresh_data и т.д.)


    # --- Правая панель: Поля и их кнопки очистки ---
    def _create_field_with_clear_button(textfield: ft.TextField, clear_button: ft.IconButton):
        # Helper для создания строки с полем и кнопкой очистки
        return ft.Row(
            [textfield, clear_button],
            vertical_alignment=ft.CrossAxisAlignment.START, # Кнопка сверху
            spacing=0 # Убрать лишний отступ
        )

    # 4. Поля для промптов и основного контента
    start_prompt_input = ft.TextField(
        label="Начальный промпт:", multiline=True, min_lines=3, max_lines=8, # Увеличена высота
        dense=True, text_size=12, border_radius=5, hint_text="Добавьте текст перед содержимым файлов...",
        hint_style=HINT_STYLE, expand=True, # expand=True чтобы заполнить Row
        on_change=lambda e: setattr(clear_start_prompt_button, 'disabled', not bool(e.control.value)) or (clear_start_prompt_button.update() if clear_start_prompt_button.page else None) or update_button_states() # Обновляем общие кнопки тоже
    )
    content_display = ft.TextField(
        multiline=True, read_only=True, expand=True, # Основное поле растягивается в Column
        border=ft.InputBorder.NONE, text_size=13, min_lines=15, # Оставим побольше строк
        hint_text="Содержимое выбранных файлов появится здесь...", hint_style=HINT_STYLE,
        on_change=lambda e: setattr(clear_content_display_button, 'disabled', not bool(e.control.value)) or (clear_content_display_button.update() if clear_content_display_button.page else None) or update_button_states()
    )
    end_prompt_input = ft.TextField(
        label="Завершающий промпт:", multiline=True, min_lines=3, max_lines=8, # Увеличена высота
        dense=True, text_size=12, border_radius=5, hint_text="Добавьте текст после содержимого файлов...",
        hint_style=HINT_STYLE, expand=True,
        on_change=lambda e: setattr(clear_end_prompt_button, 'disabled', not bool(e.control.value)) or (clear_end_prompt_button.update() if clear_end_prompt_button.page else None) or update_button_states()
    )

    # --- Функции управления UI и данными ---
    def clear_field(textfield: ft.TextField, button: ft.IconButton):
        """Очищает указанное текстовое поле и обновляет кнопки."""
        textfield.value = ""
        button.disabled = True
        if textfield.page: textfield.update()
        if button.page: button.update()
        update_button_states() # Обновляем общие кнопки (Copy, Clear All)

    clear_start_prompt_button.on_click = lambda _: clear_field(start_prompt_input, clear_start_prompt_button)
    clear_content_display_button.on_click = lambda _: clear_field(content_display, clear_content_display_button)
    clear_end_prompt_button.on_click = lambda _: clear_field(end_prompt_input, clear_end_prompt_button)

    def clear_all_fields(e):
        """Очищает все три поля."""
        logging.info("Clearing all fields.")
        clear_field(start_prompt_input, clear_start_prompt_button)
        clear_field(content_display, clear_content_display_button)
        clear_field(end_prompt_input, clear_end_prompt_button)
        # Кнопка Clear All тоже должна стать disabled, это произойдет в update_button_states()
        # update_button_states() вызывается из clear_field

    clear_all_button.on_click = clear_all_fields # Назначаем обработчик для Clear All

    def update_button_states():
        """Обновляет состояние ВСЕХ кнопок на основе текущего состояния приложения."""
        # Состояния
        is_dir_selected = current_scan_path and current_scan_path.is_dir()
        is_anything_selected_in_tree = bool(selected_paths)
        has_items_in_tree = bool(dir_tree_container.controls and isinstance(dir_tree_container.controls[0], ft.Column))
        has_start_prompt = bool(start_prompt_input.value)
        has_content = bool(content_display.value)
        has_end_prompt = bool(end_prompt_input.value)
        has_any_content_to_manage = has_start_prompt or has_content or has_end_prompt

        # Кнопки верхней панели
        # pick_dir_button - всегда активна
        select_all_button.disabled = not (has_items_in_tree and is_dir_selected)
        deselect_all_button.disabled = not (is_anything_selected_in_tree and is_dir_selected) # Активна если что-то выбрано
        show_content_button.disabled = not (is_anything_selected_in_tree and is_dir_selected)
        refresh_button.disabled = not is_dir_selected
        copy_button.disabled = not has_any_content_to_manage
        clear_all_button.disabled = not has_any_content_to_manage

        # Кнопки очистки полей
        clear_start_prompt_button.disabled = not has_start_prompt
        clear_content_display_button.disabled = not has_content
        clear_end_prompt_button.disabled = not has_end_prompt

        # Обновление UI кнопок (если страница отрисована)
        buttons_to_update = [
            select_all_button, deselect_all_button, show_content_button,
            refresh_button, copy_button, clear_all_button,
            clear_start_prompt_button, clear_content_display_button, clear_end_prompt_button
        ]
        for btn in buttons_to_update:
            if btn.page:
                try:
                    btn.update()
                except Exception as update_err:
                    # Иногда может возникать ошибка при обновлении, если элемент удален
                    logging.warning(f"Could not update button state: {update_err}")
        if progress_ring.page: progress_ring.update() # На всякий случай

    def clear_ui_on_error():
        dir_tree_container.controls.clear()
        dir_tree_container.controls.append(ft.Text("Выберите корректную директорию."))
        # Очищаем поля
        clear_field(start_prompt_input, clear_start_prompt_button)
        clear_field(content_display, clear_content_display_button)
        clear_field(end_prompt_input, clear_end_prompt_button)
        selected_paths.clear()
        expanded_nodes.clear()
        _current_visible_paths_cache.clear()
        # Обновляем состояние всех кнопок
        update_button_states()
        # Обновляем остальные компоненты
        if dir_tree_container.page: dir_tree_container.update()
        if filter_input.page: filter_input.update()
        if selected_directory_text.page: selected_directory_text.update() # Текст мог измениться

    def update_ui_after_selection():
        populate_tree_view()
        content_display.value = "Выберите файлы/папки в дереве слева и нажмите 'Показать' [Enter]." # Обновлено сообщение с подсказкой hotkey
        # Не сбрасываем промпты здесь
        # Обновляем состояние всех кнопок
        update_button_states()
        # Обновляем компоненты
        if content_display.page: content_display.update()
        if start_prompt_input.page: start_prompt_input.update()
        if end_prompt_input.page: end_prompt_input.update()
        if filter_input.page: filter_input.update()
        if selected_directory_text.page: selected_directory_text.update()


    # --- Логика сканирования ---
    def scan_and_display_content_sync(
        target_page: ft.Page, paths_to_scan: Set[Path], base_path: Optional[Path],
        display_control: ft.TextField, prog_ring: ft.ProgressRing
        # Кнопки больше не передаем, используем глобальные ссылки и update_button_states
    ):
        # ... (Внутренняя логика сканирования файлов без изменений) ...
        if not paths_to_scan:
             logging.warning("scan_and_display_content_sync called with empty selection.")
             final_text = "Ошибка: Не выбраны файлы или папки для отображения."
             scan_error = None
             display_control.value = final_text
             prog_ring.visible = False
             update_button_states() # Обновляем состояние кнопок
             try: target_page.update()
             except Exception as update_err: logging.error(f"Error updating page from thread (no paths): {update_err}")
             return

        logging.info(f"Scanning content for {len(paths_to_scan)} selected items.")
        all_content_parts = []
        processed_files_scan: Set[Path] = set()
        files_to_process: List[Path] = []
        scan_error = None
        final_text = ""
        try:
            # 1. Сбор файлов
            sorted_selection = sorted(list(paths_to_scan), key=lambda p: p.parts)
            for item_path in sorted_selection:
                if item_path.is_file() and is_likely_text_file(item_path):
                    if item_path not in processed_files_scan: files_to_process.append(item_path); processed_files_scan.add(item_path)
                elif item_path.is_dir():
                    try:
                         if IGNORE_DIRS.intersection(set(p.lower() for p in item_path.parts)): continue
                         try:
                             if base_path:
                                 relative_parts = item_path.relative_to(base_path).parts
                                 if any(p.startswith('.') and (base_path / Path(*relative_parts[:i+1])).is_dir() for i, p in enumerate(relative_parts)): continue
                         except ValueError: pass
                         for sub_item in item_path.rglob('*'):
                             if not sub_item.is_file(): continue
                             if IGNORE_DIRS.intersection(set(p.lower() for p in sub_item.parts)): continue
                             try:
                                 if base_path:
                                     sub_relative_parts = sub_item.relative_to(base_path).parts
                                     if any(p.startswith('.') and (base_path / Path(*sub_relative_parts[:i+1])).is_dir() for i, p in enumerate(sub_relative_parts[:-1])): continue
                             except ValueError: pass
                             if is_likely_text_file(sub_item):
                                 if sub_item not in processed_files_scan: files_to_process.append(sub_item); processed_files_scan.add(sub_item)
                    except PermissionError as dir_perm_err:
                         logging.warning(f"Permission denied scanning directory {item_path}: {dir_perm_err}")
                         relative_path_err = item_path.relative_to(base_path) if base_path else item_path.name
                         all_content_parts.append(f"{relative_path_err} (ДИРЕКТОРИЯ)\n```\n[ОШИБКА ДОСТУПА: {dir_perm_err}]\n```\n\n")
                    except Exception as dir_scan_err:
                         logging.warning(f"Error scanning directory {item_path}: {dir_scan_err}")
                         relative_path_err = item_path.relative_to(base_path) if base_path else item_path.name
                         all_content_parts.append(f"{relative_path_err} (ДИРЕКТОРИЯ)\n```\n[ОШИБКА СКАНИРОВАНИЯ ПАПКИ: {dir_scan_err}]\n```\n\n")
            total_files_count = len(files_to_process); logging.info(f"Total text files to read: {total_files_count}")
            # 2. Чтение файлов
            for i, file_path in enumerate(files_to_process):
                try:
                    relative_path = file_path.relative_to(base_path) if base_path else file_path.name; logging.debug(f"Reading file ({i+1}/{total_files_count}): {relative_path}")
                    file_content = file_path.read_text(encoding='utf-8', errors='ignore')
                    file_block = f"{relative_path}\n```\n{file_content.strip()}\n```\n\n"; all_content_parts.append(file_block)
                except Exception as read_err:
                    logging.warning(f"Could not read file {file_path}: {read_err}"); relative_path_err = file_path.relative_to(base_path) if base_path else file_path.name
                    error_block = f"{relative_path_err}\n```\n[НЕ УДАЛОСЬ ПРОЧИТАТЬ ФАЙЛ: {read_err}]\n```\n\n"; all_content_parts.append(error_block)
        except Exception as general_scan_err: logging.error(f"Error during selected content scan preparation: {general_scan_err}"); scan_error = general_scan_err
        finally:
            # --- Обновление UI ---
            if scan_error: final_text = f"Произошла ошибка при сканировании:\n\n{scan_error}"
            elif not all_content_parts: final_text = "Не найдено текстовых файлов в выбранных элементах (или они были отфильтрованы)."
            else: final_text = "".join(all_content_parts).strip()
            display_control.value = final_text
            prog_ring.visible = False
            update_button_states() # Обновляем все кнопки
            logging.info("Selected content scanning complete. Requesting page update.")
            try: target_page.update()
            except Exception as final_update_err: logging.error(f"Error updating page from thread (finally): {final_update_err}")

    def start_scan_async(e):
        if not selected_paths or show_content_button.disabled: return # Проверяем доступность кнопки
        progress_ring.visible = True
        # Блокируем кнопки на время сканирования
        show_content_button.disabled = True
        refresh_button.disabled = True
        copy_button.disabled = True
        clear_all_button.disabled = True
        clear_start_prompt_button.disabled = True
        clear_content_display_button.disabled = True
        clear_end_prompt_button.disabled = True
        select_all_button.disabled = True
        deselect_all_button.disabled = True
        content_display.value = "Подготовка к сканированию..."
        page.update() # Обновляем UI перед запуском потока
        paths_to_scan_copy = selected_paths.copy()
        thread = threading.Thread(
            target=scan_and_display_content_sync,
            args=(page, paths_to_scan_copy, current_scan_path, content_display, progress_ring),
            daemon=True
        )
        thread.start()

    show_content_button.on_click = start_scan_async

    def refresh_data(e):
        if refresh_button.disabled: return # Не выполнять если кнопка неактивна
        if current_scan_path and current_scan_path.is_dir():
            logging.info(f"Refreshing data for: {current_scan_path}")
            page.splash = ft.ProgressBar(); page.update()
            selected_paths.clear(); expanded_nodes.clear()
            filter_input.value = ""; filter_text = ""
            populate_tree_view()
            content_display.value = "Дерево обновлено. Выберите элементы и нажмите 'Показать' [Enter]."
            # Не сбрасываем промпты
            update_button_states() # Обновляем кнопки
            logging.info("Refresh complete.")
            page.splash = None; page.update()
        else:
            logging.warning("Refresh clicked but no valid directory selected.")
            clear_ui_on_error(); page.update()

    refresh_button.on_click = refresh_data

    def copy_to_clipboard(e):
        if copy_button.disabled: return
        start_prompt = start_prompt_input.value or ""
        main_content = content_display.value or ""
        end_prompt = end_prompt_input.value or ""
        parts = []
        if start_prompt.strip(): parts.append(start_prompt.strip())
        if main_content.strip(): parts.append(main_content.strip())
        if end_prompt.strip(): parts.append(end_prompt.strip())
        full_text_to_copy = "\n\n".join(parts)
        if full_text_to_copy:
            logging.info(f"Copying {len(full_text_to_copy)} chars (incl. prompts) to clipboard.")
            try:
                pyperclip.copy(full_text_to_copy)
                page.show_snack_bar(ft.SnackBar(ft.Text("Промпты и текст скопированы!"), open=True))
            except Exception as clip_err:
                 logging.error(f"Clipboard error: {clip_err}")
                 try:
                     page.set_clipboard(full_text_to_copy)
                     page.show_snack_bar(ft.SnackBar(ft.Text("Промпты и текст скопированы (Flet)!"), open=True))
                 except Exception as flet_clip_err:
                     logging.error(f"Flet Clipboard error: {flet_clip_err}")
                     page.show_snack_bar(ft.SnackBar(ft.Text(f"Ошибка копирования: {flet_clip_err}"), open=True, bgcolor=ft.colors.RED_200))
        else:
            logging.info("Copy clicked, but nothing to copy."); page.show_snack_bar(ft.SnackBar(ft.Text("Нет текста для копирования."), open=True))

    copy_button.on_click = copy_to_clipboard

    # --- Обработчик Горячих Клавиш ---
    def on_keyboard(e: ft.KeyboardEvent):
        logging.debug(f"Keyboard event: key={e.key}, shift={e.shift}, ctrl={e.ctrl}, alt={e.alt}, meta={e.meta}")
        if e.ctrl:
            if e.key == "O": # Ctrl + O - Выбрать директорию
                logging.info("Hotkey Ctrl+O detected.")
                pick_dir_button.on_click(None) # Вызываем обработчик кнопки
            elif e.key == "A": # Ctrl + A - Выбрать все
                 logging.info("Hotkey Ctrl+A detected.")
                 if not select_all_button.disabled:
                     select_all_visible(None)
            elif e.key == "R": # Ctrl + R - Обновить
                 logging.info("Hotkey Ctrl+R detected.")
                 if not refresh_button.disabled:
                     refresh_data(None)
            elif e.key == "C": # Ctrl + C - Копировать все
                 logging.info("Hotkey Ctrl+C detected.")
                 if not copy_button.disabled:
                     copy_to_clipboard(None)
            elif e.key == "X": # Ctrl + X - Очистить все
                 logging.info("Hotkey Ctrl+X detected.")
                 if not clear_all_button.disabled:
                     clear_all_fields(None)
        elif e.key == "Enter": # Enter - Показать содержимое
             logging.info("Hotkey Enter detected.")
             if not show_content_button.disabled:
                 start_scan_async(None)
        elif e.key == "Escape": # Esc - Снять выбор
             logging.info("Hotkey Escape detected.")
             if not deselect_all_button.disabled:
                 deselect_all(None)

        # Обновляем UI после возможного изменения состояния кнопок
        page.update()

    page.on_keyboard_event = on_keyboard

    # --- Сборка Layout ---

    # Левая панель
    left_panel = ft.Container(
        content=ft.Column([
            filter_input,
            # select_buttons_row убран отсюда
            # ft.Divider(height=5), # Разделитель больше не нужен здесь
            dir_tree_container # Дерево сразу под фильтром
        ], expand=True, spacing=5),
        padding=10, border=ft.border.all(1, ft.colors.with_opacity(0.3, ft.colors.OUTLINE)),
        border_radius=ft.border_radius.all(5), expand=LEFT_PANEL_EXPAND, # 20%
    )

    # Правая панель
    right_panel = ft.Container(
         content=ft.Column([
            _create_field_with_clear_button(start_prompt_input, clear_start_prompt_button),
            ft.Divider(height=1, thickness=0.5), # Тонкий разделитель
            # Оборачиваем основное поле и кнопку в Row, чтобы кнопка была сбоку
            # Но основное поле должно растягиваться по высоте, поэтому оно остается в Column
             ft.Row(
                 [content_display], # Основное поле занимает всю ширину строки
                 expand=True # Row растягивается по высоте Column
             ),
            ft.Row([ft.Container(expand=True), clear_content_display_button], spacing=0), # Кнопка очистки под полем справа
            ft.Divider(height=1, thickness=0.5),
            _create_field_with_clear_button(end_prompt_input, clear_end_prompt_button),
         ],
         expand=True, spacing=2), # Уменьшим spacing
        padding=10, border=ft.border.all(1, ft.colors.with_opacity(0.3, ft.colors.OUTLINE)),
        border_radius=ft.border_radius.all(5), expand=RIGHT_PANEL_EXPAND, # 80%
    )

    # --- Основной Layout страницы ---
    page.add(
        ft.Column([
            # Верхняя панель с кнопками
            ft.Row(
                [
                    pick_dir_button,
                    ft.VerticalDivider(width=10), # Разделитель
                    selected_directory_text, # Растягивается
                    ft.VerticalDivider(width=10),
                    # Группа кнопок выбора
                    select_all_button,
                    deselect_all_button,
                    ft.VerticalDivider(width=10),
                    # Группа кнопок действий
                    show_content_button,
                    refresh_button,
                    copy_button,
                    clear_all_button, # Общая очистка здесь
                    progress_ring, # Индикатор рядом с кнопками действий
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2 # Уменьшим spacing между кнопками
            ),
            ft.Divider(height=5),
            # Основная строка с панелями
            ft.Row(
                [
                    left_panel,
                    ft.VerticalDivider(width=1),
                    right_panel,
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True
            )
        ], expand=True)
    )

    # Загрузка состояния при старте
    load_app_state()
    update_button_states() # Устанавливаем начальное состояние кнопок

    # Финальное обновление страницы
    page.update()

# --- Запуск приложения ---
if __name__ == "__main__":
    try: import pyperclip
    except ImportError: print("WARNING: pyperclip library not found.")
    ft.app(target=main)
    logging.info("Flet application finished.")