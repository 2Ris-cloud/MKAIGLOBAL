import sys
import json
import uuid
import requests
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, 
    QPropertyAnimation, QEasingCurve, QSize
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QStackedWidget, QFileDialog, QMessageBox, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import (
    QColor, QPalette, QFont, QTextCursor, QKeyEvent, 
    QLinearGradient, QPainter, QPen, QBrush
)


# ============================================================
# КОНСТАНТЫ И ТИПЫ
# ============================================================

API_URL = "http://localhost:3000/api"
SESSION_ID = str(uuid.uuid4())[:8]
COLORS = {
    'bg_primary': '#0D0D0D',       # Почти чёрный
    'bg_secondary': '#161616',     # Тёмно-серый
    'bg_tertiary': '#1F1F1F',      # Светлее
    'accent': '#2D2D2D',           # Акцент
    'text_primary': '#FFFFFF',     # Белый текст
    'text_secondary': '#888888',   # Серый текст
    'text_muted': '#555555',       # Приглушённый
    'highlight': '#3B82F6',        # Синий акцент
    'success': '#22C55E',          # Зелёный
    'border': '#2A2A2A',           # Границы
}

class Stage(Enum):
    ANALYSIS = ("analysis", "Анализ", "Постановка проблемы")
    GOALS = ("goals", "Цели", "Формулирование целей")
    PLANNING = ("planning", "План", "Планирование работы")
    RESEARCH = ("research", "Поиск", "Исследование материалов")
    WORK = ("work", "Работа", "Выполнение задач")
    SOLUTION = ("solution", "Решение", "Итоговый ответ")


# ============================================================
# МОДЕЛИ ДАННЫХ
# ============================================================

@dataclass
class Message:
    role: str  # 'user' | 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Document:
    filename: str
    content: str
    pages: int = 0


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    domain: str


# ============================================================
# API КЛИЕНТ
# ============================================================

class APIClient:
    
    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url
        self.timeout = 120
    
    def chat(self, message: str, stage: str, context: str = "", docs: List[str] = None) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "message": message,
                    "sessionId": SESSION_ID,
                    "stage": stage,
                    "context": context,
                    "documents": docs or []
                },
                timeout=self.timeout
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search(self, query: str, source: str = "general") -> List[SearchResult]:
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"q": query, "num": 10, "source": source},
                timeout=30
            )
            data = response.json()
            return [
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r.get("snippet", ""),
                    domain=r["domain"]
                )
                for r in data.get("results", [])
            ]
        except:
            return []
    
    def extract_pdf(self, file_path: str) -> Optional[Document]:
        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    f"{self.base_url}/pdf",
                    files={"file": (Path(file_path).name, f, "application/pdf")},
                    timeout=60
                )
            data = response.json()
            if data.get("success"):
                return Document(
                    filename=data["metadata"]["filename"],
                    content=data["text"],
                    pages=data["metadata"]["pages"]
                )
        except:
            pass
        return None


# ============================================================
# WORKER ПОТОКИ
# ============================================================

class ChatWorker(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, api: APIClient, message: str, stage: str, context: str, docs: List[str]):
        super().__init__()
        self.api = api
        self.message = message
        self.stage = stage
        self.context = context
        self.docs = docs
    
    def run(self):
        result = self.api.chat(self.message, self.stage, self.context, self.docs)
        self.finished.emit(result)


class SearchWorker(QThread):
    finished = pyqtSignal(list)
    
    def __init__(self, api: APIClient, query: str, source: str):
        super().__init__()
        self.api = api
        self.query = query
        self.source = source
    
    def run(self):
        results = self.api.search(self.query, self.source)
        self.finished.emit(results)


# ============================================================
# UI КОМПОНЕНТЫ
# ============================================================

class MessageBubble(QFrame):
    
    def __init__(self, message: Message, parent=None):
        super().__init__(parent)
        self.message = message
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("messageBubble")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        text_label = QLabel(self.message.content)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        if self.message.role == 'user':
            self.setStyleSheet(f"""
                #messageBubble {{
                    background-color: {COLORS['highlight']};
                    border-radius: 12px;
                    margin-left: 40px;
                }}
                QLabel {{ color: white; font-size: 13px; }}
            """)
        else:
            self.setStyleSheet(f"""
                #messageBubble {{
                    background-color: {COLORS['bg_tertiary']};
                    border-radius: 12px;
                    margin-right: 40px;
                }}
                QLabel {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            """)
        
        layout.addWidget(text_label)

        time_label = QLabel(self.message.timestamp.strftime("%H:%M"))
        time_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        layout.addWidget(time_label)


class StageButton(QPushButton):
    
    def __init__(self, stage: Stage, is_active: bool = False, is_completed: bool = False):
        super().__init__()
        self.stage = stage
        self.is_active = is_active
        self.is_completed = is_completed
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setText(f"{self.stage.value[1]}")

        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['highlight']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)
        elif self.is_completed:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent']};
                    color: {COLORS['text_primary']};
                }}
            """)


# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================

class TaskSolverWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.api = APIClient()
        self.messages: List[Message] = []
        self.documents: List[Document] = []
        self.search_results: List[SearchResult] = []
        self.current_stage = Stage.ANALYSIS
        self.chat_worker: Optional[ChatWorker] = None
        self.search_worker: Optional[SearchWorker] = None
        
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_window(self):
        self.setWindowTitle("MKAI")
        self.setMinimumSize(1200, 800)

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg_primary']};
            }}
            QWidget {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['bg_secondary']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        chat_container = QWidget()
        chat_container.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(24, 20, 24, 20)
        chat_layout.setSpacing(16)

        header = QLabel("MKAI")
        header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            padding: 4px 0;
        """)
        chat_layout.addWidget(header)

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(12)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.messages_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS['bg_primary']};
            }}
        """)
        chat_layout.addWidget(self.scroll_area, 1)

        self._show_welcome()

        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(16, 12, 12, 12)
        input_layout.setSpacing(12)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите сообщение...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        input_layout.addWidget(self.input_field, 1)
        
        self.send_btn = QPushButton("→")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['highlight']};
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_muted']};
            }}
        """)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(input_container)
        
        main_layout.addWidget(chat_container, 4)

        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        main_layout.addWidget(separator)

        self._setup_sidebar(main_layout)
    
    def _setup_sidebar(self, parent_layout):
        sidebar = QWidget()
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(280)
        sidebar.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 16)
        sidebar_layout.setSpacing(20)

        stages_label = QLabel("ЭТАПЫ")
        stages_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            color: {COLORS['text_muted']};
            letter-spacing: 1.5px;
        """)
        sidebar_layout.addWidget(stages_label)
        
        self.stage_buttons: List[StageButton] = []
        for stage in Stage:
            btn = StageButton(
                stage=stage,
                is_active=stage == self.current_stage
            )
            btn.clicked.connect(lambda checked, s=stage: self._set_stage(s))
            self.stage_buttons.append(btn)
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addSpacing(12)

        actions_label = QLabel("ДЕЙСТВИЯ")
        actions_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            color: {COLORS['text_muted']};
            letter-spacing: 1.5px;
        """)
        sidebar_layout.addWidget(actions_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 10px 12px;
                color: {COLORS['text_primary']};
                font-size: 12px;
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        sidebar_layout.addWidget(self.search_input)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        self.search_btn = self._create_action_button("🔍  Веб-поиск")
        self.scholar_btn = self._create_action_button("📚  Научные статьи")
        self.upload_btn = self._create_action_button("📄  Загрузить PDF")
        
        actions_layout.addWidget(self.search_btn)
        actions_layout.addWidget(self.scholar_btn)
        actions_layout.addWidget(self.upload_btn)
        
        sidebar_layout.addLayout(actions_layout)

        sidebar_layout.addSpacing(12)
        
        self.docs_label = QLabel("ДОКУМЕНТЫ: 0")
        self.docs_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            color: {COLORS['text_muted']};
            letter-spacing: 1.5px;
        """)
        sidebar_layout.addWidget(self.docs_label)
        
        self.docs_list = QWidget()
        self.docs_layout = QVBoxLayout(self.docs_list)
        self.docs_layout.setContentsMargins(0, 0, 0, 0)
        self.docs_layout.setSpacing(4)
        sidebar_layout.addWidget(self.docs_list)
        
        sidebar_layout.addStretch()

        model_info = QLabel("GLM-5 • Zhipu AI")
        model_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_info.setStyleSheet(f"""
            font-size: 10px;
            color: {COLORS['text_muted']};
            padding: 8px;
        """)
        sidebar_layout.addWidget(model_info)
        
        parent_layout.addWidget(sidebar, 1)
    
    def _create_action_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_primary']};
                border-color: {COLORS['highlight']};
            }}
        """)
        return btn
    
    def _connect_signals(self):
        self.send_btn.clicked.connect(self._send_message)
        self.input_field.returnPressed.connect(self._send_message)
        self.search_btn.clicked.connect(self._do_search)
        self.scholar_btn.clicked.connect(lambda: self._do_search(scholar=True))
        self.upload_btn.clicked.connect(self._upload_pdf)
    
    def _show_welcome(self):
        welcome = Message(
            role='assistant',
            content='Привет! Я MKAI — интеллектуальный ассистент для решения задач.\n\n'
                   'Опишите вашу задачу, и я помогу решить её, следуя структурированной методологии:\n'
                   '• Анализ проблемы\n'
                   '• Формулирование целей\n'
                   '• Планирование\n'
                   '• Исследование\n'
                   '• Выполнение\n'
                   '• Решение'
        )
        self._add_message(welcome)
    
    def _add_message(self, message: Message):
        self.messages.append(message)
        bubble = MessageBubble(message)
        self.messages_layout.addWidget(bubble)

        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text or (self.chat_worker and self.chat_worker.isRunning()):
            return

        user_msg = Message(role='user', content=text)
        self._add_message(user_msg)
        self.input_field.clear()

        context = ""
        if self.search_results:
            context = "\n".join([
                f"[{r.domain}] {r.title}: {r.snippet[:150]}"
                for r in self.search_results[:5]
            ])
        
        docs = [d.content[:3000] for d in self.documents]

        self.chat_worker = ChatWorker(
            self.api, text, self.current_stage.value[0], context, docs
        )
        self.chat_worker.finished.connect(self._on_chat_response)
        self.chat_worker.start()
        
        self.send_btn.setEnabled(False)
    
    def _on_chat_response(self, result: dict):
        self.send_btn.setEnabled(True)
        
        if result.get("success"):
            assistant_msg = Message(role='assistant', content=result["response"])
        else:
            assistant_msg = Message(
                role='assistant',
                content=f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}"
            )
        
        self._add_message(assistant_msg)
    
    def _set_stage(self, stage: Stage):
        self.current_stage = stage

        for btn in self.stage_buttons:
            btn.is_active = btn.stage == stage
            btn.is_completed = list(Stage).index(btn.stage) < list(Stage).index(stage)
            btn._setup_ui()
    
    def _do_search(self, scholar: bool = False):
        query = self.search_input.text().strip()
        if not query:
            return
        
        source = "scholar" if scholar else "general"
        self.search_worker = SearchWorker(self.api, query, source)
        self.search_worker.finished.connect(self._on_search_results)
        self.search_worker.start()
        
        self.search_btn.setEnabled(False)
        self.scholar_btn.setEnabled(False)
    
    def _on_search_results(self, results: List[SearchResult]):
        self.search_btn.setEnabled(True)
        self.scholar_btn.setEnabled(True)
        self.search_results = results
        
        if results:
            msg = Message(
                role='assistant',
                content=f"🔍 Найдено {len(results)} результатов. Топ-3:\n\n" +
                       "\n\n".join([
                           f"**{r.title}**\n{r.domain}\n{r.snippet[:200]}..."
                           for r in results[:3]
                       ])
            )
            self._add_message(msg)
        else:
            msg = Message(role='assistant', content="Ничего не найдено.")
            self._add_message(msg)
    
    def _upload_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите PDF файл", "", "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        doc = self.api.extract_pdf(file_path)
        if doc:
            self.documents.append(doc)
            self._update_docs_list()
            
            msg = Message(
                role='assistant',
                content=f"📄 Загружен документ: {doc.filename}\n"
                       f"Страниц: {doc.pages} | Символов: {len(doc.content):,}"
            )
            self._add_message(msg)
        else:
            msg = Message(role='assistant', content="❌ Ошибка загрузки документа")
            self._add_message(msg)
    
    def _update_docs_list(self):
        while self.docs_layout.count():
            self.docs_layout.takeAt(0).widget().deleteLater()

        for doc in self.documents:
            label = QLabel(f"• {doc.filename[:20]}...")
            label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            self.docs_layout.addWidget(label)
        
        self.docs_label.setText(f"ДОКУМЕНТЫ: {len(self.documents)}")


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = TaskSolverWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
