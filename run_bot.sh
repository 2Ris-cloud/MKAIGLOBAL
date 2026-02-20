#!/bin/bash
# Запуск чат-бота для решения задач
# ================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🧠 НЕЙРОСЕТЬ-ЧАТБОТ ДЛЯ РЕШЕНИЯ ЗАДАЧ (GLM-5)           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверяем, что сервер запущен
echo -e "${YELLOW}Проверка сервера...${NC}"
if curl -s http://localhost:3000/api > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Сервер запущен${NC}"
else
    echo -e "${RED}✗ Сервер не запущен!${NC}"
    echo -e "${YELLOW}Запустите сервер командой: bun run dev${NC}"
    exit 1
fi

# Проверяем Python
echo -e "${YELLOW}Проверка Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}✗ Python не установлен!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python найден: $($PYTHON_CMD --version)${NC}"

# Проверяем зависимости Python
echo -e "${YELLOW}Проверка зависимостей...${NC}"
$PYTHON_CMD -c "import requests, rich" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Установка зависимостей...${NC}"
    pip install requests rich
fi
echo -e "${GREEN}✓ Зависимости установлены${NC}"

# Запускаем бота
echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════"
echo "                      Запуск чат-бота                         "
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

cd "$(dirname "$0")"
$PYTHON_CMD task_solver_bot.py
