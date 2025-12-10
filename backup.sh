#!/bin/bash

# Caminho do backend
DIR="/var/www/maritima"

# Nome da branch de backup
BRANCH="backup_vps"

# Ir para o diretório
cd $DIR || { echo "Diretório $DIR não encontrado"; exit 1; }

# Inicializa git caso não exista
git init

# Pega informações do GitHub
git fetch origin

# Cria/força a branch de backup
git checkout -B $BRANCH

# Adiciona todos os arquivos
git add .

# Commit com data e hora
git commit -m "Backup do backend da VPS $(date '+%Y-%m-%d %H:%M:%S')" || true

# Push para o GitHub usando SSH
git push -u origin $BRANCH --force

echo "✅ Backup concluído!"

