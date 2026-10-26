#!/usr/bin/env bash
# Сканирование безопасности Trivy: зависимости, секреты, конфигурации, Docker-образы.
# Нужны только docker и bash. Запуск:  ./scripts/trivy-scan.sh
# Код возврата 1, если найдены уязвимости HIGH/CRITICAL (для которых уже есть исправление).
set -uo pipefail

# Версия закреплена: v0.69.3 — последняя проверенная разработчиками (см. README, раздел про CI).
# Не использовать тег latest: в марте 2026 он указывал на скомпрометированный релиз.
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.69.3}"
SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"
OUT=reports/trivy
mkdir -p "$OUT"

trivy() {
  docker run --rm \
    -v "$PWD":/work -w /work \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v trivy-cache:/root/.cache \
    "$TRIVY_IMAGE" "$@"
}

status=0

# scan <имя> <команда> <цель> [доп. флаги]
scan() {
  local name=$1 cmd=$2 target=$3; shift 3
  echo "::group::Trivy: $name"
  # 1) отчёт SARIF для вкладки Security на GitHub (не валит сборку)
  trivy "$cmd" --format sarif --output "$OUT/$name.sarif" --severity "$SEVERITY" "$@" "$target" >/dev/null
  # 2) читаемая таблица в лог + проверка порога
  trivy "$cmd" --format table --severity "$SEVERITY" --exit-code 1 "$@" "$target" || status=1
  echo "::endgroup::"
}

# Файлы проекта: зависимости (requirements.txt, package-lock.json),
# секреты в коде и ошибки конфигурации Dockerfile
scan repo fs . \
  --scanners vuln,secret,misconfig --ignore-unfixed \
  --skip-dirs node_modules --skip-dirs .git --skip-dirs reports \
  --ignorefile .trivyignore

# Собранные образы (собирает docker compose, см. image: в docker-compose.yml)
docker compose build backend frontend || exit 1
scan backend-image image flower-delivery-backend:ci --ignore-unfixed --ignorefile .trivyignore
scan frontend-image image flower-delivery-frontend:ci --ignore-unfixed --ignorefile .trivyignore

if [ "$status" -ne 0 ]; then
  echo "Trivy нашёл уязвимости уровня $SEVERITY — см. таблицы выше."
fi
exit "$status"
