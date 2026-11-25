# 민툰 · MinToon

**Stock Unreal. Native toon materials. No engine patches.**

런처판 Unreal Engine 5.8을 수정하지 않고, 엔진의 Substrate Toon BSDF·Toon Profile로
캐릭터(VRM 포함)와 배경을 같은 툰 스타일로 맞추는 에디터 저작 플러그인이다.
제품 이름은 **민툰 / MinToon**, 저장소 이름은 **min-toon**이다.
MooaToon의 포크가 아니며, 해당 프로젝트의 코드·셰이더·에셋을 포함하지 않는다.

> **개발 버전 0.1 — UE 5.8.4 Windows에서 생성·화면·패키징 확인.** 아래 "검증과 현재 상태"에
> 적힌 범위만 확인했다. Toon BSDF 자체가 Epic 기준 **Experimental**이며, 다른 플랫폼·애니메이션
> 중 안정성·Sequencer 렌더는 아직 확인하지 않았다. MooaToon과 동급 화질을 주장하지 않는다.

## 현재 구현

Python 에디터 플러그인이다. C++ 모듈·엔진 소스·셰이더 변경이 없고, 결과물은 엔진 기본
에셋(Toon Profile, Material, Material Instance)이라 게임 실행에 MinToon 코드가 필요 없다.

**Tools > MinToon** 메뉴:

| 메뉴 | 하는 일 |
| --- | --- |
| Create starter materials | `/Game/MinToon`에 `TP_MinToon`·`M_MinToon`·`MI_MinToon` 한 벌 생성 (덮어쓰지 않음) |
| Stylize selected actors | 선택한 액터의 메시 컴포넌트에 툰 재질과 외곽선을 적용 |
| Apply lighting preset | 태양·Sky Atmosphere·Sky Light·Height Fog·Post Process를 추가하거나 조정 |

**스타일 라이브러리** (`/Game/MinToon/Style`, 처음 Stylize할 때 한 번 생성):

| 파트 | 용도 | 특징 |
| --- | --- | --- |
| Body | 피부·옷 | 2단 램프, 붉은 기 도는 그림자, 작은 하이라이트 |
| Face | 얼굴·눈·입 | 명암 경계를 크게 뒤로 밀어 얼굴 대부분이 밝게 유지 |
| Hair | 머리카락 | 2단 램프, 넓은 하이라이트 띠, 강한 림라이트 |
| Background | 배경 정적 메시 | 3단 램프, 푸른 그림자, 간접광 비중 큼 |

파트마다 Toon Profile(확산·반사 램프, 간접광 배율, 그림자를 램프에 포함)과 부모 머티리얼
(`BaseColorTexture` × `BaseColor`, Roughness, Specular, Anisotropy, Fresnel 림라이트, Emissive,
알파 마스크)을 만든다. 외곽선은 메시 컴포넌트의 **Overlay Material**로 붙는 inverted hull
(`M_MinToon_Outline`, 파트별 두께 인스턴스)이다.

**Stylize 동작:** 스켈레탈 메시는 머티리얼 슬롯 이름으로 Face/Hair/Body를 고르고(VRoid·VRM
이름 규칙), 스태틱 메시는 Background를 쓴다. 기존 재질에서 알베도 텍스처와 색
(`mtoon_tex_MainTex`, `gltf_tex_diffuse`, `BaseColor` 등, 없으면 처음 쓰는 sRGB 텍스처),
반투명·마스크 여부, 양면 여부를 읽어 `/Game/MinToon/Instances/<액터>`에 인스턴스를 만든다.
**메시 에셋은 수정하지 않고** 레벨의 컴포넌트 재질만 바꾸므로 레벨을 저장해야 유지된다.

## 설치와 사용

1. 저장소 폴더를 프로젝트의 `Plugins/MinToon`으로 복사한다
   (`MyProject/Plugins/MinToon/MinToon.uplugin`).
2. UE 5.8 Plugins 창에서 MinToon을 켜고 재시작한다. 의존 플러그인은
   **Python Editor Script Plugin**, **Editor Scripting Utilities**다.
3. Project Settings > Rendering에서 **Substrate**와 **Blendable GBuffer**를 켜고 재시작한다.
   도구는 렌더링 설정을 바꾸지 않으며, 꺼져 있으면 오류 대화상자를 띄운다.
4. 레벨에서 캐릭터·배경 액터를 선택하고 **Tools > MinToon > Stylize selected actors**.
5. **Tools > MinToon > Apply lighting preset**. 그림자 영역은 직접광을 받지 않고 Sky Light만
   받으므로(Toon BSDF 동작) 레벨에 Sky Light가 있어야 그림자가 검게 뭉개지지 않는다.
6. 레벨을 저장한다. 세부 조정은 `/Game/MinToon/Style`의 `TP_MinToon_*`(램프·간접광)과
   각 인스턴스(색·림·외곽선 두께)에서 한다.

**VRM 캐릭터:** VRM 가져오기는 MinToon 범위 밖이며 [VRM4U](https://github.com/ruyo/VRM4U)
(MIT, 별도 설치)를 쓴다. VRM4U로 가져온 스켈레탈 메시를 레벨에 놓고 4번을 실행하면 MToon
텍스처를 이어받은 MinToon 재질로 바뀐다. 반투명 MToon 재질은 마스크(alpha cut)로 바뀐다.

Python 콘솔에서도 같은 기능을 쓸 수 있다.

```python
import unreal
from mintoon import apply_lighting_preset, stylize_actor

for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors():
    stylize_actor(actor, "/Game/MinToon")          # part="Hair" 등으로 강제 지정 가능
apply_lighting_preset()
```

## 검증과 현재 상태

현재 상태 문서는 이 README 하나다. 이력은 Git에 남긴다.
환경: Windows 11, UE 5.8.4 (CL 58902052, 런처판), VRM4U 5.8 (2026-11-10 릴리스).

| 검증 | 2026-11-20 결과 |
| --- | --- |
| 플러그인 로드·메뉴 | 검증 프로젝트에서 MinToon 마운트, `Tools > MinToon` 메뉴 등록 확인(GUI 에디터). 메뉴 클릭은 사람이 직접 확인하지 않음 |
| 에셋 생성·컴파일 (`Tests/unreal_smoke.py`) | 6개 테스트 통과: 스타터 에셋, 파트별 프로파일 램프 적용, 외곽선, 원본 재질의 텍스처·색·마스크·양면 이어받기, 정리 |
| VRM 적용 (`Tests/create_vrm_scene.py`) | 사용자 VRM을 VRM4U로 가져와 6개 슬롯 Stylize, 배경 8개 + 조명 프리셋, 오류 없음 |
| 화면 (`Tests/capture_views.py`) | 에디터 뷰포트 캡처로 셀 명암, 틴트 그림자, 외곽선, 배경 통일 확인 |
| Cook·패키징 | 설치 형태 복사본(`Plugins/MinToon`)으로 UAT BuildCookRun Win64 Development 성공, 두 맵 cook |
| 패키지 실행 | 패키지 exe로 두 맵 실행, 에디터와 같은 외관 확인 |
| Python 소스 검사 | 18개 Python 테스트 통과(일부는 Unreal 모의). 모의 테스트는 엔진 검증이 아님 |
| 미검증 | 애니메이션·표정 중 외곽선/그림자 안정성, Lumen, Sequencer·Movie Render Queue, Win64 외 플랫폼 |

### 알려진 한계

- **그림자 = Sky Light.** Toon BSDF는 그림자 속에 직접광을 주지 않는다. Sky Light가 없거나
  캡처가 갱신되지 않으면 그림자가 0(검정)이 된다.
- 드리운 그림자 가장자리에 얇고 어두운 테두리가 보인다(램프와 그림자 경계 처리).
- 외곽선은 정점 노멀 방향 확장이라 하드 엣지 메시(상자)는 모서리가 끊긴다. 두께는 월드 단위(cm)라
  화면 거리 보정이 없다.
- 얼굴 그림자는 램프 위치로만 조절한다. 얼굴 SDF 그림자, 헤어 그림자 투영은 없다.
- 반투명 재질은 마스크로만 바뀐다. MToon의 shade 텍스처·rim 텍스처·matcap은 쓰지 않는다.
- Toon Profile 오버라이드는 Python으로 설정할 수 없어(`ToonProfileOverride`가 편집 불가 속성)
  파트마다 부모 머티리얼을 둔다.

## 검증 절차

검증 프로젝트 `Tests/Project/MinToonValidation.uproject`는 `AdditionalPluginDirectories: ../..`로
이 checkout을 직접 참조한다. 생성 콘텐츠(`Tests/Project/Content`), 로그·캡처·패키지
(`Tests/Project/Saved`), 로컬 서드파티 플러그인(`Tests/Project/Plugins`)은 Git에서 제외한다.
`DefaultEngine.ini`가 Substrate·Blendable GBuffer와 검증 맵을, `DefaultGame.ini`가 cook 맵을 지정한다.
AndroidFileServer는 꺼 두었다(켜 두면 에디터가 매 실행 무작위 토큰을 설정 파일에 쓴다).

Unreal 없이 하는 소스 검사:

```sh
python -m compileall -q Content/Python Tests
python -m unittest discover -s Tests -p 'test_*.py' -v
```

UE 검사(PowerShell, 저장소 루트). `unittest` 출력은 stderr라 로그에 `LogPython: Error:`가 붙지만
판정은 마지막 `Ran N tests`·`OK`로 한다.

```powershell
$Repo = (Get-Location).Path
$Engine = 'C:\Program Files\Epic Games\UE_5.8'
$Project = Join-Path $Repo 'Tests\Project\MinToonValidation.uproject'
$Cmd = "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

& $Cmd $Project "-ExecutePythonScript=$Repo\Tests\unreal_smoke.py" -unattended -nosplash -log
& $Cmd $Project "-ExecutePythonScript=$Repo\Tests\create_validation_scene.py" -unattended -nosplash -log
$env:MINTOON_VRM = 'C:\path\to\character.vrm'   # VRM4U를 Tests/Project/Plugins/VRM4U에 설치한 뒤
& $Cmd $Project "-ExecutePythonScript=$Repo\Tests\create_vrm_scene.py" -unattended -nosplash -log
```

장면 스크립트는 출력 폴더가 이미 있거나 저장 안 된 변경이 있으면 아무것도 하지 않고 멈춘다.
다시 만들려면 `Tests/Project/Content/MinToonValidation` 또는 `MinToonVRM`을 지운다.

화면 캡처는 GUI 에디터가 필요하다. `-ExecutePythonScript`는 스크립트가 끝나면 바로 종료하므로
`-ExecCmds`로 실행하고, 백그라운드 창도 렌더링하도록 CPU 절약을 끈다(꺼야 Sky Light가 갱신된다).

```powershell
$env:MINTOON_MAP = '/Game/MinToonVRM/L_MinToonVRM'
& "$Engine\Engine\Binaries\Win64\UnrealEditor.exe" $Project "-ExecCmds=py $($Repo.Replace('\','/'))/Tests/capture_views.py" `
  '-ini:EditorSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
```

PNG는 `Tests/Project/Saved/MinToonCaptures`에 저장된다. SceneCapture2D 방식은 UE 5.8에서
Sky Light 없이 렌더되어 쓰지 않는다.

**패키징은 설치 형태로 한다.** UnrealBuildTool은 `AdditionalPluginDirectories`의 *하위 폴더*에서만
플러그인을 찾으므로, 코드 플러그인(VRM4U)이 있어 빌드가 필요하면 `../..`(플러그인 폴더 자체)를
찾지 못하고 실패한다. 검증 프로젝트를 임시 폴더로 복사하고(`Saved`·`Intermediate` 제외),
`MinToon.uplugin`과 `Content`를 그 안의 `Plugins/MinToon`에 넣은 뒤 `.uproject`에서
`AdditionalPluginDirectories`를 지우고 실행했다.

```powershell
& "$Engine\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$Copy\MinToonValidation.uproject" -noP4 `
  -platform=Win64 -clientconfig=Development -build -cook -stage -pak -package -archive `
  "-archivedirectory=$Repo\Tests\Project\Saved\Packaged" `
  "-map=/Game/MinToonValidation/L_MinToonValidation+/Game/MinToonVRM/L_MinToonVRM"
```

패키지 exe에 맵 경로와 `-ExecCmds="HighResShot 1600x900"`을 주면 실행 화면이
`Packaged/Windows/MinToonValidation/Saved/Screenshots`에 저장된다. 두 맵에는 PlayerStart가 없어
엔진 기본 폰(구)이 원점에 보인다.

## 다음 단계

툰 렌더링 기본 경로(재질·외곽선·VRM·배경·조명·패키징)가 확인됐다. 다음은 **Sequencer**다:
VRM에 애니메이션을 붙여 움직일 때 외곽선·그림자·얼굴 명암이 안정적인지 확인하고,
카메라 컷과 Movie Render Queue 렌더를 자동화한다. 화질 조정(얼굴 그림자, 그림자 테두리,
외곽선 화면 두께 보정)은 그 결과를 보고 우선순위를 정한다.

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
- [MeshComponent — Overlay Material](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MeshComponent)
- [AutomationLibrary — TakeHighResScreenshot](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AutomationLibrary)
- [Build operations — UAT BuildCookRun](https://dev.epicgames.com/documentation/unreal-engine/build-operations-cooking-packaging-deploying-and-running-projects-in-unreal-engine?lang=en-US)
