#!/usr/bin/env python3
"""Install a separately obtained manosaba Korean patch into a Proton game.

Python 3.8+, standard library only. No translation or game assets are included.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile

VERSION = "1.1.2"
APP_ID = "3101040"
ASSET_ROOT = "manosaba_Data/StreamingAssets/aa/StandaloneWindows64"
STATE_DIR = ".manosaba-ko-linux"
CHUNK = 1024 * 1024


class PatchError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as src:
        for block in iter(lambda: src.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def parse_vdf(text):
    """Read quoted/bare KeyValues, nested objects, escapes and // comments."""
    tokens = []
    i = 0
    text = text.lstrip("\ufeff")
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end + 1
        elif c in "{}":
            tokens.append(c)
            i += 1
        elif c == '"':
            i += 1
            word = []
            while i < len(text) and text[i] != '"':
                if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in '\\"':
                    i += 1
                word.append(text[i])
                i += 1
            if i == len(text):
                raise PatchError("Steam VDF의 문자열이 끝나지 않았습니다.")
            tokens.append("".join(word))
            i += 1
        else:
            start = i
            while i < len(text) and not text[i].isspace() and text[i] not in "{}":
                i += 1
            tokens.append(text[start:i])
    pos = 0

    def obj(nested=False):
        nonlocal pos
        out = {}
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                if not nested:
                    raise PatchError("Steam VDF의 괄호가 맞지 않습니다.")
                return out
            if key == "{" or pos >= len(tokens) or tokens[pos] == "}":
                raise PatchError("Steam VDF의 키/값이 올바르지 않습니다.")
            value = tokens[pos]
            pos += 1
            out[key] = obj(True) if value == "{" else value
        if nested:
            raise PatchError("Steam VDF의 괄호가 닫히지 않았습니다.")
        return out

    return obj()


def ci_get(mapping, key, default=None):
    if not isinstance(mapping, dict):
        return default
    return next((v for k, v in mapping.items() if k.lower() == key.lower()), default)


def steamapps(root):
    direct = root / "steamapps"
    if direct.is_dir():
        return direct
    try:
        return next((p for p in root.iterdir() if p.name.lower() == "steamapps" and p.is_dir()), direct)
    except OSError:
        return direct


def default_steam_roots():
    home = Path.home()
    roots = [home / ".steam/steam", home / ".steam/root",
             Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))) / "Steam",
             home / ".local/share/Steam",
             home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
             home / "snap/steam/common/.local/share/Steam",
             home / ".snap/data/steam/common/.local/share/Steam"]
    if os.environ.get("STEAM_DIR"):
        roots.insert(0, Path(os.environ["STEAM_DIR"]).expanduser())
    return roots


def find_games(steam_roots):
    libraries = set()
    for root in steam_roots:
        root = Path(root).expanduser().resolve()
        libraries.add(root)
        vdf = steamapps(root) / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        try:
            folders = ci_get(parse_vdf(vdf.read_text(encoding="utf-8-sig")), "libraryfolders", {})
            if not isinstance(folders, dict):
                continue
            for key, value in folders.items():
                if not key.isdigit():
                    continue
                value = ci_get(value, "path") if isinstance(value, dict) else value
                if not isinstance(value, str) or not value:
                    continue
                library = Path(value).expanduser()
                if not library.is_absolute():
                    continue
                # Flatpak's private home is presented as the host user's home in VDF.
                if "com.valvesoftware.Steam" in root.parts and library == Path.home() / ".local/share/Steam":
                    library = root
                libraries.add(library.resolve())
        except (OSError, UnicodeError, PatchError) as exc:
            print("경고: Steam 라이브러리 정보를 읽지 못했습니다: {} ({})".format(vdf, exc), file=sys.stderr)
    found = set()
    for library in sorted(libraries):
        apps = steamapps(library)
        manifest = apps / ("appmanifest_" + APP_ID + ".acf")
        try:
            data = ci_get(parse_vdf(manifest.read_text(encoding="utf-8-sig")), "AppState", {})
            if str(ci_get(data, "appid", APP_ID)) != APP_ID:
                continue
            name = ci_get(data, "installdir")
            if not isinstance(name, str) or not name or name in (".", "..") or any(c in name for c in "/\\\x00"):
                continue
            game = (apps / "common" / name).resolve()
            if (game / "manosaba.exe").is_file() and (game / ASSET_ROOT).is_dir():
                found.add(game)
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError, PatchError) as exc:
            print("경고: 게임 설치 정보를 읽지 못했습니다: {} ({})".format(manifest, exc), file=sys.stderr)
    return sorted(found)


def safe_relative(name):
    p = PurePosixPath(name)
    if (not isinstance(name, str) or not name or "\\" in name or "\x00" in name
            or p.is_absolute() or any(x in ("", ".", "..") for x in name.split("/"))
            or str(p) != name or ":" in name):
        raise PatchError("안전하지 않은 상대 경로: " + repr(name))
    return p


def checked_path(root, relative):
    parts = safe_relative(relative).parts
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise PatchError("심볼릭 링크 경로에는 쓰지 않습니다: " + str(current))
    if os.path.commonpath([str(root.resolve()), str(current.resolve())]) != str(root.resolve()):
        raise PatchError("게임 폴더 밖의 경로입니다: " + str(current))
    return current


def validate_game(game):
    if not game.is_dir() or not (game / "manosaba.exe").is_file():
        raise PatchError("Windows판 manosaba.exe가 있는 게임 폴더를 지정하세요. Linux/macOS 네이티브판은 지원하지 않습니다.")
    with open(game / "manosaba.exe", "rb") as exe:
        if exe.read(2) != b"MZ":
            raise PatchError("manosaba.exe가 Windows 실행 파일이 아닙니다.")
    if not checked_path(game, ASSET_ROOT).is_dir():
        raise PatchError("Windows 게임 데이터 폴더가 없습니다: " + ASSET_ROOT)


def validate_profile(profile):
    files = profile.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 256:
        raise PatchError("패치 프로필의 파일 목록이 올바르지 않습니다.")
    total = 0
    for name, meta in files.items():
        p = safe_relative(name)
        if str(p.parent) != ASSET_ROOT or p.suffix != ".bundle":
            raise PatchError("허용되지 않은 패치 대상: " + name)
        if not isinstance(meta, dict) or type(meta.get("size")) is not int or not 0 < meta["size"] <= 2 * 1024**3:
            raise PatchError("패치 파일 크기 정보가 올바르지 않습니다: " + name)
        if not re.fullmatch(r"[0-9a-f]{64}", str(meta.get("sha256", ""))):
            raise PatchError("패치 파일 SHA-256 정보가 올바르지 않습니다: " + name)
        total += meta["size"]
    if total > 2 * 1024**3:
        raise PatchError("패치 전체 크기가 제한을 초과합니다.")


def inspect_archive(zip_path, profile):
    """Validate the complete ZIP and payload hashes, without extracting to disk."""
    validate_profile(profile)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            seen = set()
            entries = []
            for entry in archive.infolist():
                name = entry.filename.rstrip("/") if entry.is_dir() else entry.filename
                safe_relative(name)
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFDIR, stat.S_IFREG)):
                    raise PatchError("ZIP의 특수 파일/링크는 지원하지 않습니다: " + name)
                if name in seen:
                    raise PatchError("ZIP에 중복 경로가 있습니다: " + name)
                seen.add(name)
                if entry.flag_bits & 1:
                    raise PatchError("암호화된 ZIP은 지원하지 않습니다.")
                if entry.is_dir():
                    if not (ASSET_ROOT == name or ASSET_ROOT.startswith(name + "/")):
                        raise PatchError("ZIP에 예상하지 않은 폴더가 있습니다: " + name)
                    continue
                meta = profile["files"].get(name)
                if meta is None or entry.file_size != meta["size"]:
                    raise PatchError("지원하는 패치와 파일 목록/크기가 다릅니다: " + name)
                h = hashlib.sha256()
                count = 0
                with archive.open(entry) as src:
                    for block in iter(lambda: src.read(CHUNK), b""):
                        count += len(block)
                        if count > meta["size"]:
                            raise PatchError("ZIP 파일 크기가 제한을 초과합니다: " + name)
                        h.update(block)
                if count != meta["size"] or h.hexdigest() != meta["sha256"]:
                    raise PatchError("패치 SHA-256이 일치하지 않습니다: " + name)
                entries.append(entry)
            if {entry.filename for entry in entries} != set(profile["files"]):
                raise PatchError("ZIP에 필요한 패치 파일이 빠져 있습니다.")
            return entries
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise PatchError("ZIP을 읽을 수 없습니다: " + str(exc)) from exc


def atomic_json(path, value):
    fd, tmp = tempfile.mkstemp(prefix=".json-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dst:
            json.dump(value, dst, ensure_ascii=False, indent=2)
            dst.write("\n")
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(tmp, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sync_directory(path):
    if os.name != "nt":
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def sync_prepared_backup(transaction, game):
    # Persist every new directory entry before publishing a recovery journal.
    for directory, _, _ in os.walk(transaction, topdown=False):
        sync_directory(Path(directory))
    sync_directory(transaction.parent)
    sync_directory(transaction.parent.parent)
    sync_directory(game)


def durable_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as source, open(dst, "wb") as target:
        shutil.copyfileobj(source, target, CHUNK)
        target.flush()
        os.fsync(target.fileno())
    shutil.copystat(src, dst)


@contextlib.contextmanager
def game_lock(game):
    state_dir = checked_path(game, STATE_DIR)
    state_dir.mkdir(exist_ok=True)
    lock_path = checked_path(state_dir, "lock")
    with open(lock_path, "a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                if not lock.read(1):
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise PatchError("다른 패치 작업이 실행 중입니다.") from exc
        try:
            yield state_dir
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_state(game):
    state_dir = checked_path(game, STATE_DIR)
    active = checked_path(state_dir, "active.json")
    if not active.exists():
        return None
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        if (data.get("format") != 1 or data.get("phase") not in ("installing", "installed", "restoring")
                or not re.fullmatch(r"[0-9a-f]{32}", data.get("transaction", ""))):
            raise ValueError("state header")
        validate_profile({"files": {name: {"size": meta["patched_size"], "sha256": meta["patched_sha256"]}
                                    for name, meta in data["files"].items()}})
        for meta in data["files"].values():
            if not re.fullmatch(r"[0-9a-f]{64}", meta["original_sha256"]):
                raise ValueError("original hash")
        return data
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise PatchError("백업 상태 파일이 손상되었습니다. .manosaba-ko-linux 폴더를 보존하세요.") from exc


def check_current(game, state, allow_original=False):
    for name, meta in state["files"].items():
        target = checked_path(game, name)
        accepted = {meta["patched_sha256"]}
        if allow_original:
            accepted.add(meta["original_sha256"])
        if not target.is_file() or sha256_file(target) not in accepted:
            raise PatchError("적용 후 파일이 변경되었거나 없어졌습니다: {}. 게임 업데이트/다른 모드를 확인하세요. 백업은 보존됩니다.".format(name))


def _restore_unlocked(game, state_dir):
    state = read_state(game)
    if state is None:
        return "복구할 활성 백업이 없습니다."
    # Accept old hashes as well: a power loss may leave a partial apply/restore.
    check_current(game, state, allow_original=True)
    transaction = checked_path(state_dir, "backups/" + state["transaction"])
    for name, meta in state["files"].items():
        original = checked_path(transaction, "originals/" + name)
        if not original.is_file() or sha256_file(original) != meta["original_sha256"]:
            raise PatchError("원본 백업이 손상되었거나 없습니다: " + name)
    changed = [name for name, meta in state["files"].items()
               if sha256_file(checked_path(game, name)) != meta["original_sha256"]]
    needed = max((checked_path(transaction, "originals/" + name).stat().st_size for name in changed), default=0)
    if changed and shutil.disk_usage(game).free < needed + 16 * CHUNK:
        raise PatchError("원본 복구 임시 파일을 위한 여유 공간이 부족합니다.")
    state["phase"] = "restoring"
    atomic_json(state_dir / "active.json", state)
    for name, meta in state["files"].items():
        target = checked_path(game, name)
        current = sha256_file(target)
        if current == meta["original_sha256"]:
            continue
        if current != meta["patched_sha256"]:
            raise PatchError("복구 도중 대상 파일이 변경되었습니다: " + name)
        tmp = checked_path(transaction, "restore.tmp")
        durable_copy(checked_path(transaction, "originals/" + name), tmp)
        os.replace(tmp, target)
        sync_directory(target.parent)
    state["phase"] = "restored"
    atomic_json(transaction / "record.json", state)
    (state_dir / "active.json").unlink()
    sync_directory(state_dir)
    return "원본 파일 복구 완료. 백업 기록: " + str(transaction)


def restore_patch(game):
    game = Path(game).expanduser().resolve()
    validate_game(game)
    with game_lock(game) as state_dir:
        return _restore_unlocked(game, state_dir)


def status(game):
    game = Path(game).expanduser().resolve()
    validate_game(game)
    state = read_state(game)
    if state is None:
        return "이 도구로 적용한 활성 패치가 없습니다."
    if state["phase"] != "installed":
        return "중단된 작업({})이 있습니다. --restore로 원본을 복구하세요.".format(state["phase"])
    check_current(game, state)
    return "{} 적용됨: {}개 파일 정상".format(state["profile"], len(state["files"]))


def install_patch(game, zip_path, profile):
    game = Path(game).expanduser().resolve()
    zip_path = Path(zip_path).expanduser().resolve()
    validate_game(game)
    entries = inspect_archive(zip_path, profile)
    with game_lock(game) as state_dir:
        active = read_state(game)
        if active is not None:
            if (active["phase"] == "installed" and set(active["files"]) == set(profile["files"])
                    and all(active["files"][n]["patched_sha256"] == m["sha256"] for n, m in profile["files"].items())):
                check_current(game, active)
                return "같은 패치가 이미 정상 적용되어 있습니다."
            raise PatchError("기존 패치/중단된 작업이 있습니다. --restore로 복구한 다음 적용하세요.")
        originals_size = 0
        for entry in entries:
            target = checked_path(game, entry.filename)
            if not target.is_file():
                raise PatchError("게임에 패치 대상 파일이 없습니다: {}. 게임 버전/설치 위치를 확인하세요.".format(entry.filename))
            originals_size += target.stat().st_size
        needed = originals_size + sum(e.file_size for e in entries) + 64 * CHUNK
        if shutil.disk_usage(game).free < needed:
            raise PatchError("백업과 준비 파일을 위한 여유 공간이 부족합니다. 약 {:.2f} GiB가 필요합니다.".format(needed / 1024**3))
        transaction_id = uuid.uuid4().hex
        transaction = checked_path(state_dir, "backups/" + transaction_id)
        transaction.mkdir(parents=True)
        data = {"format": 1, "phase": "installing", "profile": profile["id"],
                "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "transaction": transaction_id, "files": {}}
        journal_written = False
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for entry in entries:
                    name = entry.filename
                    target = checked_path(game, name)
                    backup = checked_path(transaction, "originals/" + name)
                    before = sha256_file(target)
                    durable_copy(target, backup)
                    if sha256_file(backup) != before or sha256_file(target) != before:
                        raise PatchError("백업 도중 게임 파일이 변경되었습니다. 게임과 Steam을 종료하세요: " + name)
                    staged = checked_path(transaction, "staged/" + name)
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as src, open(staged, "wb") as dst:
                        count = 0
                        while True:
                            block = src.read(CHUNK)
                            if not block:
                                break
                            count += len(block)
                            if count > profile["files"][name]["size"]:
                                raise PatchError("패치 ZIP이 검증 이후 변경되었습니다: " + name)
                            dst.write(block)
                        dst.flush()
                        os.fsync(dst.fileno())
                    meta = profile["files"][name]
                    if count != meta["size"] or sha256_file(staged) != meta["sha256"]:
                        raise PatchError("패치 ZIP이 검증 이후 변경되었습니다: " + name)
                    os.chmod(staged, stat.S_IMODE(target.stat().st_mode))
                    data["files"][name] = {"original_sha256": before, "patched_sha256": meta["sha256"], "patched_size": meta["size"]}
            atomic_json(transaction / "record.json", data)
            sync_prepared_backup(transaction, game)
            atomic_json(state_dir / "active.json", data)
            journal_written = True
            for name, meta in data["files"].items():
                target = checked_path(game, name)
                if sha256_file(target) != meta["original_sha256"]:
                    raise PatchError("적용 도중 게임 파일이 변경되었습니다: " + name)
                os.replace(checked_path(transaction, "staged/" + name), target)
                sync_directory(target.parent)
            data["phase"] = "installed"
            atomic_json(state_dir / "active.json", data)
            atomic_json(transaction / "record.json", data)
        except (Exception, KeyboardInterrupt) as exc:
            if journal_written:
                try:
                    _restore_unlocked(game, state_dir)
                except (Exception, KeyboardInterrupt) as rollback:
                    raise PatchError("적용이 중단되었습니다: {}. 자동 복구도 완료하지 못했습니다: {}. 백업을 보존하고 --restore를 다시 실행하세요.".format(exc, rollback)) from exc
                raise PatchError("적용이 중단되어 원본으로 자동 복구했습니다: " + str(exc)) from exc
            # No game file has been replaced. Keep prepared backups for inspection.
            raise PatchError("게임 파일 변경 전에 중단되었습니다: {}. 준비 파일: {}".format(exc, transaction)) from exc
        return "한글패치 {} 적용 완료: {}개 파일. 원본 백업: {}".format(profile["id"], len(entries), transaction)


def load_profile():
    path = Path(__file__).resolve().with_name("patch_profile.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        validate_profile(data)
        return data
    except (OSError, ValueError) as exc:
        raise PatchError("동봉된 patch_profile.json을 읽을 수 없습니다: " + str(exc)) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="사용자가 가진 ZIP으로 마노사바 Windows판에 한글패치 적용 (Linux/Proton)")
    parser.add_argument("--version", action="version", version="manosaba-patcher " + VERSION)
    parser.add_argument("zip", nargs="?", type=Path, help="원본 manosaba_patch_v1.1.2.zip 경로")
    parser.add_argument("--game-dir", type=Path, help="manosaba.exe가 있는 게임 폴더 (자동 탐색 대신 사용)")
    parser.add_argument("--steam-root", type=Path, action="append", default=[], help="추가 Steam/라이브러리 루트 (반복 가능)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="ZIP/대상 검증만 수행, 파일 쓰기 없음")
    mode.add_argument("--restore", action="store_true", help="원본 파일로 복구 (ZIP 불필요)")
    mode.add_argument("--status", action="store_true", help="적용 상태와 파일 해시 확인")
    mode.add_argument("--list", action="store_true", help="Steam 설치 경로 탐색 결과만 표시")
    mode.add_argument("--check-runtime", action="store_true", help="게임 파일 변경 없이 실행 환경과 내장 패치 프로필 검사")
    parser.add_argument("-y", "--yes", action="store_true", help="확인 입력 없이 적용/복구")
    args = parser.parse_args(argv)
    if args.zip and (args.restore or args.status or args.list or args.check_runtime):
        parser.error("--restore/--status/--list/--check-runtime에는 ZIP 경로를 함께 지정하지 마세요.")
    if not (args.restore or args.status or args.list or args.check_runtime) and not args.zip and not sys.stdin.isatty():
        parser.error("ZIP 경로를 지정하세요. 예: ./manosaba-patcher ~/Downloads/manosaba_patch_v1.1.2.zip")
    try:
        if args.check_runtime:
            profile = load_profile()
            print("manosaba-patcher " + VERSION)
            print("패치 프로필: {} / {}개 파일".format(profile["id"], len(profile["files"])))
            return 0
        if not (args.restore or args.status or args.list) and not args.zip:
            print("마노사바 Linux/Proton 한글패처 " + VERSION)
            print("원본 배포처에서 받은 manosaba_patch_v1.1.2.zip을 준비하세요.")
            entered = input("패치 ZIP 경로 (빈 입력: 취소): ").strip()
            if not entered:
                print("취소했습니다.")
                return 0
            if len(entered) >= 2 and entered[0] == entered[-1] and entered[0] in ("'", '"'):
                entered = entered[1:-1]
            args.zip = Path(entered).expanduser()
        games = [args.game_dir.expanduser().resolve()] if args.game_dir else find_games(default_steam_roots() + args.steam_root)
        if args.list:
            print("\n".join(str(p) for p in games) if games else "Steam에서 대상 게임을 찾지 못했습니다.")
            return 0 if games else 1
        if not games:
            raise PatchError("Steam에서 게임을 찾지 못했습니다. --game-dir '/게임/설치/폴더'로 직접 지정하세요.")
        if len(games) != 1:
            raise PatchError("여러 설치가 발견되었습니다. --game-dir로 하나를 지정하세요:\n" + "\n".join(map(str, games)))
        game = games[0]
        validate_game(game)
        print("게임 폴더: " + str(game), flush=True)
        if args.status:
            print(status(game))
            return 0
        profile = None
        if not args.restore:
            profile = load_profile()
            print("ZIP 내용과 SHA-256 검증 중 (약 1.1 GiB 압축 해제 검사)...", flush=True)
            entries = inspect_archive(args.zip.expanduser(), profile)
            for entry in entries:
                if not checked_path(game, entry.filename).is_file():
                    raise PatchError("게임에 패치 대상 파일이 없습니다: " + entry.filename)
            print("검증 완료: {} / {}개 파일 / {:.2f} GiB".format(profile["id"], len(entries), sum(e.file_size for e in entries) / 1024**3), flush=True)
            if args.dry_run:
                print(status(game))
                print("검사 완료. 게임 파일 및 백업 폴더를 변경하지 않았습니다. 게임 원본 버전 호환성/실행 여부는 이 검사로 확인할 수 없습니다.")
                return 0
        if not args.yes:
            print("게임과 Steam의 다운로드/업데이트를 종료한 후 진행하세요.")
            action = "원본 복구" if args.restore else "한글패치 적용 및 원본 백업"
            if not sys.stdin.isatty():
                raise PatchError("확인 입력을 받을 수 없습니다. 직접 실행하거나 --yes를 지정하세요.")
            if input(action + "을 진행하려면 yes 입력: ").strip().lower() != "yes":
                print("취소했습니다.")
                return 0
        print(restore_patch(game) if args.restore else install_patch(game, args.zip, profile))
        return 0
    except (PatchError, OSError, zipfile.BadZipFile) as exc:
        print("오류: " + str(exc), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("중단했습니다. 활성 작업이 남았다면 --restore로 복구하세요.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
