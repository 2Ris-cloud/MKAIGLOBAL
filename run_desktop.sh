#!/bin/bash
# TaskSolver AI — Запуск
# ======================

cd "$(dirname "$0")"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       TaskSolver AI • Desktop         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo

# Проверка Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}✗ Python не установлен${NC}"
    exit 1
fi

# Проверка зависимостей
echo -e "${CYAN}Проверка зависимостей...${NC}"
$PYTHON -c "import PyQt6, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${CYAN}Установка зависимостей...${NC}"
    pip install PyQt6 requests
fi

# Проверка сервера
echo -e "${CYAN}Проверка сервера API...${NC}"
if curl -s http://localhost:3000/api > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Сервер запущен${NC}"
else
    echo -e "${RED}✗ Сервер не запущен!${NC}"
    echo -e "  Запустите сервер: cd /home/z/my-project && bun run dev"
    echo
    read -p "Продолжить без сервера? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo
echo -e "${GREEN}Запуск приложения...${NC}"
$PYTHON task_solver_desktop.py
