# Обновление прода (Frappe Pilot): frappe_books + fadl_books

## 0. Откуда что тянется

| Репозиторий | remote | Ветка прод-загрузки |
|---|---|---|
| `frappe_books` | `origin` → `git@github.com:qosimjon123/frappe-books.git` | `develop` (трекинг `origin/develop`) |
| | `upstream` → `https://github.com/frappe/frappe-books.git` | только для merge |
| `fadl_books` | `origin` → `git@github.com:qosimjon123/fadl-books.git` | `develop` (трекинг `origin/develop`) |

Прод делает `git pull` с этих GitHub-репозиториев, поэтому локальные коммиты без пуша на нём не появятся.

## 1. Пуш с dev-машины

```bash
cd /workspace/development/frappe-bench-books/apps/frappe_books
git add yarn.lock && git commit -m "FadlBook: lockfile after upstream merge"
git push origin develop

cd ../fadl_books
git add -A && git commit -m "FadlBook: drop default record renames from install"
git push origin develop
```

## 2. На сервере — только Pilot

Имя бенча (`-b`) посмотреть: `ls /home/frappe/pilot/benches`. Ниже — `books`.

```bash
B=books; S=books.example.com

pilot -b $B git fadl_books    pull --ff-only origin develop
pilot -b $B git frappe_books  pull --ff-only origin develop

pilot -b $B frappe --site $S backup --with-files
pilot -b $B frappe --site $S migrate
pilot -b $B build
pilot -b $B frappe --site $S compile-po-to-mo --app fadl_books --locale ru --force
pilot -b $B frappe --site $S clear-cache
pilot -b $B restart
```

`pilot build` — сборка assets из текущего исходника (полный rebuild, prebuilt-бандл не берётся);
именно он нужен для правок во `frontend/**`. `pilot restart` работает только на production-бенче.
Перед `pilot build` на ~1 ГБ RAM — `free -m`.

## 3. Проверка

```bash
pilot -b $B git frappe_books log -1 --oneline   # должен быть HEAD из origin/develop
pilot -b $B git fadl_books  log -1 --oneline
```

В браузере жёсткое обновление (Ctrl+Shift+R) — SPA меняется только через assets-билд.

## Примечание по текущей дельте

Незапушенные коммиты `frappe_books` — только `frontend/**` (POS cart race, spread mount points,
sidebar): схемы не тронуты, `migrate` почти no-op, ключевой шаг — `pilot build`.
В `fadl_books` — тест + правка `install.py`; хук `after_install` закомментирован, так что
`install.execute()` на проде сам не запускается.
