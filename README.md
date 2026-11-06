# manosaba-korean-patch-linux

**마법소녀의 마녀재판(마노사바)의 Windows용 한글패치를 Linux의 Steam/Proton 설치에 적용하는 도구입니다.**

사용자가 별도로 구한 `manosaba_patch_v1.1.2.zip`의 경로를 입력하면 Steam에서 게임을 찾아 원본 파일을 백업하고 패치 파일을 적용합니다. **Linux x86_64용 실행 파일은 Python을 따로 설치하지 않고 사용할 수 있습니다.** ZIP 안의 프로그램은 실행하지 않습니다.

**Linux/Proton에서 사용자가 실제 동작을 확인했습니다. 게임 v1.1.2에 맞춘 최초 정식 배포이며, 패처 릴리스 버전도 v1.1.2입니다.**

## 다운로드와 빠른 시작

[**최신 정식 릴리스 다운로드**](https://github.com/UESENPAI/manosaba-korean-patch-linux/releases/latest)

| 다운로드 파일 | 용도 |
| --- | --- |
| [Linux x86_64 `.tar.gz`](https://github.com/UESENPAI/manosaba-korean-patch-linux/releases/download/v1.1.2/manosaba-korean-patch-linux-v1.1.2-linux-x86_64.tar.gz) / [`.zip`](https://github.com/UESENPAI/manosaba-korean-patch-linux/releases/download/v1.1.2/manosaba-korean-patch-linux-v1.1.2-linux-x86_64.zip) | 권장: 실행 파일과 한국어 안내가 들어 있는 Linux x86_64 패처 |
| [`manosaba-patcher-linux-x86_64`](https://github.com/UESENPAI/manosaba-korean-patch-linux/releases/latest/download/manosaba-patcher-linux-x86_64) | 압축 해제 없이 받는 독립 실행 파일 |
| `*-source.tar.gz` 또는 `*-source.zip` | Python 3.8 이상으로 직접 실행하는 소스 배포본 |
| `SHA256SUMS` | 배포 파일의 SHA-256 체크섬 |

1. Linux x86_64 패처를 내려받아 압축을 풉니다. GitHub가 자동으로 제공하는 `Source code` 대신 위의 `linux-x86_64` 파일을 선택하세요.
2. [원본 한글패치 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198)에서 `manosaba_patch_v1.1.2.zip`을 별도로 받습니다. 이 ZIP은 미리 풀지 않아도 됩니다.
3. 게임을 종료하고 Steam의 다운로드·업데이트를 멈춘 뒤, 패처 폴더에서 터미널을 엽니다.

```bash
tar -xzf manosaba-korean-patch-linux-v1.1.2-linux-x86_64.tar.gz
cd manosaba-korean-patch-linux-v1.1.2
chmod +x manosaba-patcher
./manosaba-patcher "$HOME/Downloads/manosaba_patch_v1.1.2.zip" --dry-run
./manosaba-patcher "$HOME/Downloads/manosaba_patch_v1.1.2.zip"
```

`--dry-run` 명령은 ZIP과 설치 경로를 검사하며 게임 파일이나 백업 폴더를 변경하지 않습니다. 적용 명령에서는 탐색한 게임 폴더를 확인한 뒤 `yes`를 입력하세요. ZIP 압축파일은 파일 관리자에서 풀어도 됩니다. 독립 실행 파일만 받았다면 파일 이름을 `manosaba-patcher`로 바꾸고 `chmod +x manosaba-patcher` 후 같은 명령으로 실행합니다.

`./manosaba-patcher --check-runtime`으로 게임이나 원본 ZIP 없이 실행 파일과 내장 프로필을 점검할 수 있습니다. 인자 없이 `./manosaba-patcher`를 실행하면 터미널에서 원본 패치 ZIP 경로를 입력할 수 있습니다. 동봉된 `sh install.sh`로도 실행할 수 있습니다.

적용 후 Steam에서 평소처럼 게임을 실행합니다. **원본 배포글의 안내대로 게임 설정의 언어를 중국어 간체로 변경하세요.** 이 ZIP은 `zhhans` 텍스트 리소스를 교체합니다.

실행 파일은 Ubuntu 22.04의 x86_64 환경에서 빌드합니다. ARM 기기나 glibc 2.35보다 오래된 배포판에서는 아래의 소스 실행 방법을 사용하세요. Steam Deck에서는 데스크톱 모드의 터미널에서 실행할 수 있으며, SteamOS 버전별 실기 검증 목록은 아직 없습니다.

## 소스로 실행하기

소스 배포본 또는 복제한 저장소에서는 Python 3.8 이상으로 실행합니다. 별도 pip 패키지를 설치할 필요는 없습니다.

```bash
sh install.sh "$HOME/Downloads/manosaba_patch_v1.1.2.zip" --dry-run
sh install.sh "$HOME/Downloads/manosaba_patch_v1.1.2.zip"
# Python으로 직접 실행하는 경우
python3 manosaba_linux_patch.py "$HOME/Downloads/manosaba_patch_v1.1.2.zip"
```

`install.sh`는 같은 폴더에 있는 `manosaba-patcher`를 우선 사용하고, 실행 파일이 없는 소스 배포본에서는 `python3`로 실행합니다. 아래의 모든 `./manosaba-patcher` 예시는 소스 배포본에서 `sh install.sh`로 바꾸어 사용할 수 있습니다.

## 원본 한글패치와의 관계

이 프로젝트는 원본 한글패치 제작에 참여하지 않은 별도의 설치 보조 도구입니다. 게임 파일, 번역 데이터, 원본 패치 ZIP을 포함하거나 다운로드하지 않습니다. 원본 패치는 제작자의 배포처에서 직접 준비하고, 사용 조건과 안내를 따라 주세요.

저장소에 포함된 `patch_profile.json`은 지원하는 패치의 파일명·크기·SHA-256 정보만 담고 있습니다. 원본 한글패치와 게임의 권리는 각 권리자에게 있습니다. 이 저장소의 MIT 라이선스는 별도로 작성한 설치 도구와 문서에만 적용됩니다.

## 지원 범위

| 항목 | 지원 내용 |
| --- | --- |
| 게임 | Steam App ID `3101040`, `manosaba.exe`가 있는 Windows판 |
| 게임 버전 | [공식 Steam v1.1.2 업데이트 공지](https://steamcommunity.com/ogg/3101040/announcements/detail/498345684383039649)에 대응 |
| 실행 환경 | Linux에서 Steam/Proton으로 Windows판 실행 |
| 한글패치 | 검사한 `manosaba_patch_v1.1.2.zip`의 파일 내용과 일치하는 패치 |
| 실행 파일 | Linux x86_64(AMD64), glibc 2.35 이상, Python 별도 설치 불필요 |
| 소스 실행 | Python 3.8 이상, 별도 pip 패키지 불필요 |
| 설치 탐색 | 일반 Steam, Flatpak Steam, Snap Steam, 추가 라이브러리 |

원본 ZIP에는 `manosaba_Data/StreamingAssets/aa/StandaloneWindows64/` 아래의 Unity 번들 **28개**, 압축 해제 기준 **1,134,800,388바이트(약 1.06 GiB)**가 들어 있습니다. DLL이나 실행 파일이 없으므로 파일 교체 방식으로 적용하며 DLL 오버라이드 설정은 추가하지 않습니다.

이 도구는 Windows 번들을 Linux용 번들로 변환하지 않습니다. Windows판을 Proton으로 실행하는 설치가 대상입니다. 원본 게임의 정확한 버전별 파일 해시를 확보하지 않았으므로, 파일 경로가 맞더라도 게임 업데이트에 따른 호환성까지 보장할 수 없습니다.

## 원본 한글패치 다운로드

원본 한글패치는 **TCR님의 [마노사바 갤러리 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198)**에서 `manosaba_patch_v1.1.2.zip`을 직접 받아 준비하세요. 해당 글에는 2026년 2월 5일 v1.1.2 대응 패치 반영이 안내되어 있습니다.

- [원본 배포글 — 한글 패치 최종본](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198)
- [원본 배포글에서 안내하는 Google Drive 다운로드](https://drive.google.com/file/d/1VJluwJExmo7CNpf5Iw0oYgB2LM8LHURn/view?usp=sharing)

배포 링크가 바뀌면 원본 게시글의 최신 안내를 확인하세요. 이 저장소와 릴리즈에는 한글패치 ZIP을 첨부하지 않습니다.

## 원본 한글패치 제작자 크레딧과 게시글 출처

원본 한글패치는 여러 분의 작업을 이어 받아 제작·보완되었습니다. 아래는 각 배포글에서 확인한 참여자와 기여입니다.

| 참여자 | 기여 | 출처 |
| --- | --- | --- |
| **한재** | 초기 기계번역 초안 제작 | [최초 초벌 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=313), [최종본 크레딧](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198) |
| **비밀요원T** | 게임 업데이트 대응, 이미지 제작, 번역·표시 문제 보완 | [후속 패치 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=2236), [최종본 크레딧](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198) |
| **챠미** | Unity 관련 기술 도움 | [후속 패치의 감사·크레딧](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=2236) |
| **난감해** | 오역 제보 | [최종본 크레딧](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198) |
| **타입문** | 최종 검수와 수정 | [최종본 크레딧](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198) |
| **TCR** | 최종본 배포글 작성·배포 | [최종본 및 v1.1.2 대응 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198) |

마노사바 갤러리 원문 출처:

1. [한재 — 기계번역 초벌](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=313)
2. [비밀요원T — 버전 대응 및 추가 패치](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=2236)
3. [TCR — 한글패치 최종본 배포, v1.1.2 대응](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198)

후속 패치 배포글의 출처 표시 요청을 존중하여 최초 초안과 후속·최종 배포글을 함께 연결합니다. 이 저장소는 Linux용 설치·백업·복구 코드만 별도로 작성했으며, 원본 번역 제작 참여를 주장하지 않습니다.

아카라이브의 동일 패치 배포 원문은 주소와 출처 관계를 확인하지 못했습니다. 현재 출처 목록은 위에서 확인한 마노사바 갤러리 원문을 기준으로 작성했습니다.

## 설치 경로를 찾지 못할 때

Steam → 게임 속성 → 설치된 파일 → 찾아보기에서 `manosaba.exe`가 있는 폴더를 확인합니다. 공백이 있는 경로는 따옴표로 감싸 주세요.

```bash
./manosaba-patcher "$HOME/Downloads/manosaba_patch_v1.1.2.zip" \
  --game-dir "/mnt/games/SteamLibrary/steamapps/common/실제 게임 폴더명"
```

추가 라이브러리 루트를 직접 탐색 대상으로 넣을 수도 있습니다.

```bash
./manosaba-patcher --list --steam-root "/mnt/games/SteamLibrary"
```

기본적으로 다음 위치와 각 위치의 `steamapps/libraryfolders.vdf`를 읽고, `appmanifest_3101040.acf`의 설치 폴더를 찾습니다. 디스크 전체를 검색하지 않습니다.

- `~/.steam/steam`, `~/.steam/root`
- `~/.local/share/Steam`, `$XDG_DATA_HOME/Steam`
- `~/.var/app/com.valvesoftware.Steam/.local/share/Steam`
- `~/snap/steam/common/.local/share/Steam`
- `~/.snap/data/steam/common/.local/share/Steam`
- `$STEAM_DIR` 또는 `--steam-root`로 지정한 추가 위치

여러 설치가 발견되면 자동으로 하나를 선택하지 않고 `--game-dir` 지정을 요청합니다. Flatpak Steam을 사용하더라도 설치 도구는 호스트의 터미널에서 실행하세요. 외부 드라이브에서 게임 자체를 실행하려면 Steam에도 해당 경로의 접근 권한이 있어야 합니다.

## 상태 확인과 원본 복구

```bash
./manosaba-patcher --status
./manosaba-patcher --restore
```

복구에는 원본 ZIP이 필요하지 않습니다. 자동 탐색이 어려우면 두 명령에도 `--game-dir`을 추가합니다. 확인 입력을 생략하려면 `--yes`를 사용할 수 있습니다.

게임 폴더의 `.manosaba-ko-linux/backups/<작업 ID>/originals/`에 원본을 보관합니다. 복구가 끝나도 백업 기록과 파일은 남습니다. 백업은 게임 원본을 외부로 업로드하지 않고 해당 게임 폴더 안에 저장합니다.

적용 중 오류가 나면 자동 원복을 시도합니다. 프로세스가 강제 종료된 경우 `--restore`로 복구할 수 있습니다. Steam 업데이트나 다른 모드로 대상 파일이 변경된 경우에는 자동으로 덮어쓰지 않고 중단하며 백업을 보존합니다.

**게임 업데이트 전에는 원본 복구를 권장합니다.** 업데이트 뒤 파일이 바뀌었다는 오류가 나면 백업 폴더를 보존하고 Steam의 파일 무결성 검사로 게임을 복구한 뒤 새 게임 버전과 패치의 호환성을 확인하세요. 무결성 검사는 패치 파일도 원본으로 되돌릴 수 있습니다. 이때 남아 있는 활성 상태 파일은 설치 도구가 임의로 제거하지 않습니다.

## 검증과 디스크 공간

- ZIP의 전체 파일 목록, 크기, 각 파일의 SHA-256을 프로필과 대조합니다. 다른 패치 버전은 거부합니다.
- 경로 이탈, 중복 경로, 심볼릭 링크, 암호화된 ZIP, 예상하지 않은 파일을 거부합니다.
- 대상 파일이 모두 존재하는지 검사하고, 원본 백업과 패치 준비를 마친 뒤 파일별로 교체합니다.
- 백업의 해시를 확인한 뒤 복구하고, 같은 패치의 중복 적용도 검사합니다.
- 작업 잠금으로 이 도구의 동시 실행을 막습니다. Steam과 게임 자체의 쓰기 작업은 막지 못하므로 종료 후 진행해야 합니다.

추가 여유 공간은 **대상 원본 전체 크기 + 패치 압축 해제 크기 + 64 MiB** 이상 필요합니다. 원본과 패치의 크기가 비슷하다면 약 2.2 GiB이며, 게임 버전에 따라 달라집니다. 복구 중에도 원본 파일 하나를 임시 복사할 공간이 필요합니다. 준비 중 중단된 작업의 폴더는 검사할 수 있도록 보존합니다.

원본 ZIP의 SHA-256:

```text
0df199c70c6b92a34c658ba02796120b60dbbb7d5316dac17b62c9313d7128f7
```

ZIP 전체 해시는 참고값이며 실제 지원 여부는 내부 28개 파일의 경로·크기·해시로 판단합니다. ZIP을 다시 압축했더라도 동일한 내부 경로와 파일 내용이면 검증할 수 있습니다.

## 개발 및 테스트

테스트는 작은 모의 번들과 가짜 Steam 라이브러리로 실행하므로 게임이나 한글패치 ZIP이 필요하지 않습니다.

```bash
python3 -m unittest discover -s tests -v
sh -n install.sh
```

테스트 범위에는 설치·복구, 일부 교체 후 자동 원복, 중단된 작업 복구, 저용량 복구, ZIP 검증, 손상된 백업 거부, 변경된 게임 파일 보호, Steam VDF 탐색이 포함됩니다. 이 테스트의 통과는 실제 게임 실행 검증을 대신하지 않습니다.

검증 범위:

- Linux/Proton 실제 동작 확인을 사용자로부터 받아 README와 정식 릴리스에 반영했습니다. 확인 환경과 세부 시나리오는 별도로 기록되지 않았습니다.
- 모의 번들과 Steam 라이브러리를 사용하는 자동 테스트로 설치·복구·ZIP 검사·경로 탐색을 검증합니다.
- 실제 v1.1.2 ZIP의 28개 파일을 검증하고 Windows의 임시 모의 게임 폴더에서 적용·상태 확인·원복을 완료했습니다.
- 릴리스 작업에서 배포 압축파일의 내용·실행 권한·체크섬을 검사하고, 독립 실행 파일의 시작과 내장 패치 프로필 로딩을 확인합니다.

GitHub Actions는 모의 테스트와 셸 문법 검사를 수행합니다. `Release v1.1.2`로 시작하는 main 브랜치 커밋에서는 테스트 통과 후 Linux x86_64 실행 파일과 소스 배포본을 빌드해 정식 릴리스를 발행합니다. 배포 파일에는 `SHA256SUMS`를 함께 제공합니다.

## 참고

- [Valve Proton](https://github.com/ValveSoftware/Proton): Linux에서 Windows 게임을 실행하는 호환성 도구
- [게임 Steam 상점](https://store.steampowered.com/app/3101040/)
- [Unity의 플랫폼별 AssetBundle 안내](https://docs.unity.com/en-us/engine/6000.7/manual/assets-and-media/assets-managing-runtime/assetbundles-section/platforms)
- [Protontricks의 Steam 설치 탐색 구현](https://github.com/Matoking/protontricks/blob/master/src/protontricks/steam.py)
- [Flatpak Steam의 외부 드라이브 안내](https://github.com/flathub/com.valvesoftware.Steam/wiki#i-want-to-add-external-disk-for-steam-libraries)
