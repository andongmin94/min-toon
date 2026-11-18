# 민툰 · MinToon

**Stock Unreal. Native toon materials. No engine patches.**

런처판 Unreal Engine을 수정하지 않고 사용하는 툰 캐릭터 제작 도구의 초기 소스다.
현재 코드는 UE 5.8을 대상으로 작성했다. Toon BSDF/Toon Profile과 주요 Python API를
Epic 공식 문서에서 대조했고, UE 5.8.4에서 네이티브 에셋 생성 smoke 검사를 통과했다.
화면 품질·cook·패키징 검증은 남아 있다.
제품 이름은 **민툰 / MinToon**, 저장소 이름은 **min-toon**으로 정했다.
MooaToon의 포크가 아니며, 해당 프로젝트의 코드·셰이더·에셋을 포함하지 않는다.

> **개발 초안 — 에셋 생성만 UE에서 확인, 시각·cook 검증 전.** 현재는 Toon BSDF 기반 머티리얼 생성을 의도한
> 에디터 저작 도구 초안이다. 자체 툰 렌더러, 완성형 캐릭터 셰이더, 검증된 배포 제품이 아니다.
> MooaToon과 동급이거나 더 좋은 화질·성능을 확보했다는 주장은 하지 않는다.

## 현재 구현

`Tools > MinToon > Create starter materials` 명령으로 다음 세 에셋을 생성하는 코드가 있다.

| 에셋 | 역할 |
| --- | --- |
| `TP_MinToon` | 엔진 기본 Toon Profile. 간접 확산광·반사광 강도의 초기값을 지정한다. |
| `M_MinToon` | Substrate Toon BSDF를 Front Material에 연결하도록 작성한 부모 머티리얼. |
| `MI_MinToon` | BaseColor, Roughness, Specular, Anisotropy를 편집하는 머티리얼 인스턴스. |

명암·하이라이트 램프는 기본 Toon Profile 팩토리 값을 사용한다. 생성 후 프로파일에서 직접
편집한다. 자체 얼굴 그림자·헤어 모델·외곽선·스타일 프리셋은 아직 없다.
기존 캐릭터의 텍스처를 자동 변환하거나 기존 머티리얼을 자동 교체하지 않는다.

초기에는 **Python 기반 에디터 플러그인**으로 구성했다. C++ 모듈, 엔진 소스,
설치본 셰이더 변경, DLL/BuildId 우회가 없다. 생성 결과는 엔진 기본 에셋이므로
게임 실행 시 저작 스크립트가 필요한 구조가 아니다. 실제 cook·패키징 성공은 별도 검증한다.

## 설치와 사용

아래는 초기 소스가 의도한 사용 절차이며, 실제 엔진에서 검증되지 않았다.

1. 저장소 폴더를 프로젝트의 `Plugins/MinToon`으로 복사한다.
   `MyProject/Plugins/MinToon/MinToon.uplugin` 경로가 되어야 한다.
2. UE 5.8 에디터의 Plugins 창에서 MinToon을 켜고 재시작한다.
   의존 플러그인은 **Python Editor Script Plugin**, **Editor Scripting Utilities**다.
3. Project Settings > Rendering에서 **Substrate**와 **Blendable GBuffer**를 설정한다.
   변경했다면 에디터를 재시작한다. 도구는 렌더링 설정을 임의 변경하지 않는다.
4. `Tools > MinToon > Create starter materials`를 실행한다.
5. `/Game/MinToon`에서 `MI_MinToon`을 테스트 메시의 재질 슬롯에 직접 적용한다.
   셰이더 컴파일 오류, 실제 조명 반응, 원하는 외관을 확인한다.
6. `TP_MinToon`에서 명암/하이라이트 램프와 간접광을 조절한다.

Epic의 UE 5.8 릴리스 노트는 Substrate Toon Shading을 **Experimental** 기능이며
Blendable GBuffer 기반이라고 명시한다. 이 문서 확인은 MinToon의 실제 실행 검증과 별개다.
UE 5.8 이외 버전을 위한 호환 경로는 포함하지 않는다.

명령 실행은 해당 세 에셋만 생성·저장한다. 기존 에셋이 하나라도 있으면 덮어쓰지 않고
중단한다. 같은 이름의 사본을 자동 증식시키지 않는다. 실패 시 Output Log를 확인한다.
부모 머티리얼 컴파일에서 오류가 반환되면 오류 내용을 알리고 인스턴스 생성과 에셋 저장을
중단한다. 이미 생성된 프로파일·부모 머티리얼은 남을 수 있으므로 Output Log와 생성 경로를
확인한다. 현재 에디터의 컴파일 오류 확인이 실제 외관이나 다른 플랫폼의 cook 성공을 보장하지는 않는다.

프로젝트별로 별도 경로와 초기값이 필요하면 에디터 Python 콘솔에서:

```python
from mintoon import ToonSettings, create_starter_assets

assets = create_starter_assets(
    "/Game/Characters/HeroLook",
    ToonSettings(
        base_color=(0.65, 0.35, 0.18),  # linear RGB, not sRGB
        roughness=0.6,
        specular=0.35,
        anisotropy=0.0,
        diffuse_indirect_scale=0.35,
        specular_indirect_scale=0.2,
    ),
)
```

## 검증과 현재 상태

현재 상태를 기록하는 문서는 이 README 하나로 유지한다. 변경 이력은 Git에 남긴다.

| 검증/작업 | 2026-11-19 상태 |
| --- | --- |
| 주요 UE 5.8 API·렌더링 전제 | Epic 공식 문서 대조; 실제 엔진 동작은 미검증 |
| Python 구문 검사 | 현재 원격 결과는 아래 Actions 링크에서 확인 |
| 설정·경로·버전·플러그인 선언 및 오류 처리 단위 테스트 | 순수 Python 검사; Unreal API를 모의 처리한 검사는 엔진 실행 검증이 아님 |
| GitHub 저장소 / 초기 소스 | 공개 저장소 `andongmin94/min-toon`의 `main`에 반영 |
| GitHub Actions | [Source checks 실행 결과](https://github.com/andongmin94/min-toon/actions/workflows/source-checks.yml); Python 소스 검사만 수행 |
| 전용 UE 검증 프로젝트 | UE 5.8.4(CL 58902052)에서 로드 확인. 외부 플러그인 MinToon 마운트, Substrate·Blendable GBuffer CVar 적용 로그 확인 |
| UE 5.8 시작·메뉴 실행 | `UnrealEditor-Cmd` 무인 실행에서 `init_unreal.py` 오류 없이 실행. 메뉴 표시·클릭은 GUI에서 미확인 |
| 네이티브 에셋 생성·셰이더 컴파일 | `Tests/unreal_smoke.py` 4개 테스트 통과, 테스트 폴더 정리 성공. `recompile_material` 오류 없음(PCD3D_SM5 에디터). 다른 플랫폼 미검증 |
| 시각·cook 검증용 장면 생성 | `Tests/create_validation_scene.py` 작성; 실제 UE 실행 미검증 |
| 캐릭터 적용·조명·Lumen·시간적 안정성 | 미검증 |
| Cook·패키징 실행 | 미검증 |

### 전용 Unreal 검증 프로젝트

`Tests/Project/MinToonValidation.uproject`를 UE 5.8로 열어 기존 스크립트를 실행할 수 있도록
최소 프로젝트를 함께 제공한다. `AdditionalPluginDirectories`의 `../..`는 이 프로젝트에서
저장소 루트를 가리킨다. 현재 checkout의 `MinToon.uplugin`을 직접 참조하므로 플러그인
복사본을 만들 필요가 없다. Python과 Editor Scripting 의존성은 플러그인 선언을 사용한다.

| 파일 | 지정한 내용 |
| --- | --- |
| `MinToonValidation.uproject` | UE 5.8 연결, 저장소의 MinToon 활성화 |
| `Config/DefaultEngine.ini` | Substrate·Blendable GBuffer, 생성될 검증 맵을 Game Default Map으로 지정 |
| `Config/DefaultGame.ini` | `/Game/MinToonValidation/L_MinToonValidation`을 cook 대상 맵으로 지정 |

**프로젝트 파일과 설정만 포함되어 있다.** 첫 checkout에는 검증 맵이나 재질이 없으므로
아래의 에셋 검사와 장면 생성이 패키징보다 먼저다. 아직 없는 맵을 에디터 시작 맵으로
강제하지 않는다. 실제 프로젝트 로드·플러그인 발견·설정 적용도 엔진 검증 대상이다.

이 프로젝트에서 생성한 맵과 재질은 `Tests/Project/Content`에, 로그와 패키징 출력은
`Tests/Project/Saved`에 남긴다. 생성 결과는 Git에서 제외하고 소스·프로젝트 설정을 추적한다.
프로젝트를 열기만 해서는 에셋 생성 스크립트를 자동 실행하지 않는다.

### Python 소스 검사

로컬 소스 검사에는 외부 패키지가 필요 없다. 다음 명령은 Unreal을 실행하지 않는다.

```sh
python -m compileall -q Content/Python Tests
python -m unittest discover -s Tests -p 'test_*.py' -v
```

### Unreal 에셋 구조 검사

실제 UE의 에셋 구조 검사는 위 전용 프로젝트에서 `Tests/unreal_smoke.py`를
**Tools > Execute Python Script**로 실행한다. `/Game/MinToonSmoke`에 네이티브 에셋을
생성한 다음 그 테스트 폴더만 정리한다. 폴더가 이미 존재하면 실행하지 않는다.
테스트 폴더 정리에 실패하면 검사도 실패로 처리하며 성공 로그를 출력하지 않는다.
이 스크립트는 생성 중 현재 에디터가 반환하는 컴파일 오류도 확인한다. 2026-11-19 UE 5.8.4에서
아래 표준 명령에 `-unattended -nosplash`를 더해 실행했고 통과했다. 이미지 품질이나 다른 플랫폼의 셰이더·cook 검증을 대신하지 않는다.
Python `unittest` 출력은 stderr로 나가므로 Output Log에서 `LogPython: Error:` 접두어가 붙지만,
결과 판정은 마지막 `Ran N tests`·`OK`와 MinToon 성공 로그로 한다.

메뉴 재등록은 에디터 Python 콘솔에서 `from mintoon.menu import register_menu` 후
`register_menu()`를 두 번 실행하고 `Create starter materials` 항목이 하나인지 확인한다.

### 시각·패키징 검증용 장면

`Tests/create_validation_scene.py`는 기본 도형과 조명이 있는 맵을 생성하고 보존하는
스크립트다. 현재는 코드와 공식 API를 확인한 단계이며, 실제 UE에서 실행하지 않았다.
생성 성공 로그는 렌더링·cook·패키징 검증 결과를 뜻하지 않는다.

1. `Tests/Project/MinToonValidation.uproject`를 UE 5.8로 열어 시작한다.
   저장하지 않은 맵이나 콘텐츠 변경은 먼저 저장하거나 폐기한다.
2. **Tools > Execute Python Script**로 `Tests/create_validation_scene.py`를 실행한다.
3. `/Game/MinToonValidation`에 `TP_MinToon`, `M_MinToon`, `MI_MinToon`과
   `L_MinToonValidation` 맵을 생성한다. 기존 `/Game/MinToon`의 재질은 사용하거나 변경하지 않는다.
4. 구와 상자의 곡면·평면 명암, 하이라이트, 바닥 그림자를 확인한다.
   `Fill Point` 또는 `Key Directional`의 Intensity를 0으로 바꿔 단일 광원과 다중 광원을 비교한다.
5. `Validation Camera`를 pilot하여 구도를 확인한다. 카메라는 Player 0 자동 활성화로
   설정하며, 에디터 뷰포트도 같은 위치와 방향으로 이동한다.
6. 맵을 저장하고 에디터 재시작 후 다시 연다. 전용 프로젝트에는 이미 생성될 맵이
   Game Default Map과 cook 대상으로 지정되어 있다. 장면 생성과 시각 확인이 끝나면
   대상 플랫폼으로 패키징하고 실제 실행 화면을 확인한다.

구성은 엔진 기본 구·상자 메시, 얇은 상자로 만든 바닥, Movable 방향광·점광원,
카메라다. 메시의 컴포넌트에만 재질을 적용하며 엔진 메시 원본을 수정하지 않는다.
별도 런타임 코드나 외부 에셋은 추가하지 않는다. 캐릭터·헤어·애니메이션 검증은 이 장면의 범위 밖이다.

출력 폴더가 이미 있거나 저장하지 않은 맵·콘텐츠 변경이 있으면 생성 전에 중단한다.
맵 전환이 성공한 뒤에만 민툰 에셋을 생성하고, 생성한 에셋과 맵만 저장한다.
생성 도중 실패하면 신규 폴더에 일부 에셋이 남을 수 있다. 자동 삭제하거나 덮어쓰지 않으므로
Output Log와 해당 테스트 폴더를 확인한다.

### 표준 에디터·패키징 명령

다음은 저장소 루트에서 사용하는 Windows PowerShell 실행 예시다. 엔진 경로는 실제 설치
위치에 맞춘다. 이 명령을 현재 작업 환경에서 실행한 것은 아니다.

```powershell
$MinToonRepo = (Get-Location).Path
$MinToonEngine = 'C:\Program Files\Epic Games\UE_5.8'
$MinToonProject = Join-Path $MinToonRepo 'Tests\Project\MinToonValidation.uproject'

& "$MinToonEngine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" $MinToonProject "-ExecutePythonScript=$MinToonRepo\Tests\unreal_smoke.py" -log
```

Output Log에서 에셋 검사와 정리 성공을 확인한 다음, 장면 생성 스크립트를 실행한다.

```powershell
& "$MinToonEngine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" $MinToonProject "-ExecutePythonScript=$MinToonRepo\Tests\create_validation_scene.py" -log
```

`-ExecutePythonScript`는 전체 에디터와 시작 레벨을 로드한 뒤 스크립트를 실행하고 종료하는
공식 실행 방식이다. 장면 생성 후 프로젝트를 에디터로 다시 열어 저장된 맵의 외관과
카메라를 확인한다. 프로세스 종료만으로 시각 검증이 끝난 것으로 처리하지 않는다.

맵 생성·저장·시각 확인 후, 엔진에 포함된 UAT로 Windows Development 패키징을 실행할 수 있다.
추가 실행 스크립트나 별도 검증 프레임워크는 사용하지 않는다.

```powershell
& "$MinToonEngine\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$MinToonProject" -noP4 -platform=Win64 -clientconfig=Development -build -cook -stage -pak -package -archive "-archivedirectory=$MinToonRepo\Tests\Project\Saved\Packaged"
```

UAT 결과와 로그를 확인하고 `Tests/Project/Saved/Packaged` 아래에 실제로 생성된 실행 파일을
열어 검증 장면이 표시되는지 확인한다. 일반 전체 패키징을 검증 대상으로 삼는다.
외부 플러그인 경로를 사용하는 cook 후 IDE 직접 실행·Zenstore 실행의 알려진 제한은
[Epic UE-209807](https://issues.unrealengine.com/issue/UE-209807)을 참고한다.

**다음 단계는 엔진 검증이다.** 메뉴 → 에셋 생성 → 단일/다중 광원 아래 메시 적용 →
셰이더 오류 확인 → 저장·재시작 → 해당 메시를 포함한 맵의 cook·패키징 실행을 확인한다.
그 전에는 기능을 많이 늘리거나 렌더링 품질을 홍보하지 않는다.
이 기본 경로가 확인되면 텍스처 입력, 얼굴·헤어 표현, 외곽선을 실제 비교 결과에 따라 추가한다.

## 저장소

공개 저장소는 [andongmin94/min-toon](https://github.com/andongmin94/min-toon)이며,
기본 브랜치는 `main`이다. `MinToon.uplugin`은 저장소 루트에 있다.

## 라이선스와 참고

배포 라이선스는 아직 지정하지 않았다. 소유자가 선택하기 전 MIT/Apache 등의 라이선스를
임의로 붙이지 않는다. 이 저장소는 Epic 엔진 소스나 다른 프로젝트의 에셋을 배포하지 않는다.

2026-11-15 Epic의 UE 5.8 문서에서 대조한 주요 API와 렌더링 전제:

- [UE 5.8 release notes — Substrate NPR Shading](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US)
- [Substrate Toon BSDF C++ reference](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UMaterialExpressionSubstrateToon-?lang=en-US)
- [Substrate Toon BSDF Python reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialExpressionSubstrateToonBSDF)
- [Toon Profile factory](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToonProfileFactory)
- [Toon Profile asset](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToonProfile)
- [ToonProfile / native settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToonProfileStruct)
- [MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary)
- [RecompileMaterial — compiler error return value](https://dev.epicgames.com/documentation/unreal-engine/API/Editor/MaterialEditor/UMaterialEditingLibrary/RecompileMaterial)
- [MaterialProperty / Front Material](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialProperty.html)
- [Python initialization from a plugin](https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python?lang=en-US)
- [ToolMenuEntry owner](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToolMenuEntry)
- [ToolMenuOwner](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToolMenuOwner)
- [Unregister Owner by Name](https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/ToolMenus/UnregisterOwnerbyName)
- [EditorLoadingAndSavingUtils — map creation, dirty packages and saving](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils)
- [EditorActorSubsystem — scene actors](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.8)
- [UnrealEditorSubsystem — viewport camera](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/UnrealEditorSubsystem)
- [CameraActor — Player 0 activation](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CameraActor)
- [FProjectDescriptor — AdditionalPluginDirectories](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Projects/FProjectDescriptor)
- [Configuration files — rendering settings and GameDefaultMap](https://dev.epicgames.com/documentation/unreal-engine/configuration-files-in-unreal-engine?lang=en-US)
- [Build operations — UAT BuildCookRun](https://dev.epicgames.com/documentation/unreal-engine/build-operations-cooking-packaging-deploying-and-running-projects-in-unreal-engine?lang=en-US)
