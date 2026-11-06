# v1.1.2 — Linux용 한글패처 첫 정식 릴리스

[게임 v1.1.2](https://steamcommunity.com/ogg/3101040/announcements/detail/498345684383039649)에 맞춘 최초 정식 배포입니다. Linux/Proton에서 사용자가 실제 동작을 확인했으며, Python 설치 없이 실행하는 **Linux x86_64 패처**를 제공합니다.

- `manosaba-patcher` 독립 실행 파일과 안내문을 포함한 `linux-x86_64.tar.gz` / `.zip` 배포본
- Python 3.8 이상으로 실행할 수 있는 `source.tar.gz` / `.zip` 배포본
- Steam 설치 탐색, 원본 백업, 패치 파일 SHA-256 검증, 상태 확인과 원본 복구
- 인자 없이 실행하면 터미널에서 원본 패치 ZIP 경로 입력
- 배포 파일 검증용 `SHA256SUMS`

## 다운로드 및 실행

권장 파일은 **`manosaba-korean-patch-linux-v1.1.2-linux-x86_64.tar.gz`**입니다. GitHub의 자동 생성 `Source code` 대신 이 파일 또는 같은 이름의 `.zip`을 받아 압축을 푸세요. Linux x86_64(AMD64), glibc 2.35 이상에서 사용하며 Python을 따로 설치할 필요가 없습니다.

게임과 Steam의 다운로드·업데이트를 종료한 뒤, 압축을 푼 폴더에서 터미널을 열고 실행하세요.

```bash
chmod +x manosaba-patcher
./manosaba-patcher "$HOME/Downloads/manosaba_patch_v1.1.2.zip" --dry-run
./manosaba-patcher "$HOME/Downloads/manosaba_patch_v1.1.2.zip"
```

`--dry-run`은 게임을 변경하지 않는 사전 검사입니다. 실제 적용 시 게임 폴더를 확인한 뒤 `yes`를 입력하세요. 실행 파일만 받으려면 릴리스의 **`manosaba-patcher-linux-x86_64`**를 내려받아 이름을 `manosaba-patcher`로 바꾼 뒤 같은 명령으로 실행하세요.

```bash
./manosaba-patcher --status
./manosaba-patcher --restore
```

Steam 설치를 찾지 못하면 `--game-dir "/게임/설치/폴더"`를 추가하세요. 소스 배포본은 Python 3.8 이상이 필요하며 `sh install.sh`로 같은 옵션을 사용합니다.

원본 한글패치 **`manosaba_patch_v1.1.2.zip`은 [TCR님의 마노사바 갤러리 배포글](https://gall.dcinside.com/mgallery/board/view/?id=manosaba&no=9198)에서 별도로 받아야 합니다.** 게임 파일과 원본 한글패치·번역 데이터는 이 릴리스에 포함하지 않습니다. 적용 후 게임 언어를 **중국어 간체**로 설정하세요.

원본 제작·검수·기술지원 크레딧: **한재, 비밀요원T, 챠미, 난감해, 타입문, TCR**. 각 기여와 최초·후속·최종 배포글, 설치·복구 안내는 동봉된 한국어 README에서 확인할 수 있습니다.

## 검증 범위

Linux/Proton 실제 동작 확인을 사용자로부터 받았습니다. 배포판·기기·Proton 버전별 검증 목록과 저장/불러오기 등 세부 항목의 실기 결과는 별도로 기록되지 않았습니다. 자동 테스트는 모의 데이터의 설치·복구·ZIP 검증·Steam 탐색과 릴리스 패키징을 확인하며, 빌드된 실행 파일은 내장 프로필을 읽고 실행되는지 검사합니다.
