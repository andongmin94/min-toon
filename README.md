# 민툰 · MinToon

**Stock Unreal. Native toon materials. No engine patches.**

런처판 Unreal Engine을 수정하지 않고 사용하는 툰 캐릭터 제작 도구의 초기 소스다.
현재 코드는 UE 5.8 및 Toon BSDF/Toon Profile API를 전제로 작성했으며,
실제 설치 엔진과 Epic 공식 문서로 해당 버전과 API를 확인하는 작업은 남아 있다.
제품 이름은 **민툰 / MinToon**, 저장소 이름은 **min-toon**으로 정했다.
MooaToon의 포크가 아니며, 해당 프로젝트의 코드·셰이더·에셋을 포함하지 않는다.

> **개발 초안 — UE 실행 검증 전.** 현재는 Toon BSDF 기반 머티리얼 생성을 의도한
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

초기 소스는 UE 5.8의 Substrate Toon Shading과 Blendable GBuffer를 가정한다.
해당 버전의 실제 지원 상태와 API는 엔진 검증 단계에서 확인해야 한다.
5.7 이하나 5.9 Preview를 위한 호환 경로는 포함하지 않는다.

명령 실행은 해당 세 에셋만 생성·저장한다. 기존 에셋이 하나라도 있으면 덮어쓰지 않고
중단한다. 같은 이름의 사본을 자동 증식시키지 않는다. 실패 시 Output Log를 확인한다.
에셋 생성 도중 네이티브 API 오류가 발생하면 일부 새 에셋이 남을 수 있다.

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

| 검증/작업 | 2026-11-15 상태 |
| --- | --- |
| Python 구문 검사 | 이전 로컬 검사 통과; 현재 원격 결과는 아래 Actions 링크에서 확인 |
| 설정·경로·버전·플러그인 선언 단위 테스트 | 이전 로컬 검사 7개 통과; Unreal 동작을 검증한 것은 아님 |
| GitHub 저장소 / 초기 소스 | 공개 저장소 `andongmin94/min-toon`의 `main`에 반영 |
| GitHub Actions | [Source checks 실행 결과](https://github.com/andongmin94/min-toon/actions/workflows/source-checks.yml); Python 소스 검사만 수행 |
| UE 5.8 설치·시작·메뉴 실행 | 미검증: 작업 환경에 UE 없음 |
| 네이티브 에셋 생성·셰이더 컴파일 | 미검증 |
| 캐릭터 적용·조명·Lumen·시간적 안정성 | 미검증 |
| Cook·패키징 실행 | 미검증 |

로컬 소스 검사에는 외부 패키지가 필요 없다.

```sh
python -m compileall -q Content/Python Tests
python -m unittest discover -s Tests -p 'test_*.py' -v
```

실제 UE의 에셋 구조 검사는 빈 테스트 프로젝트에서 `Tests/unreal_smoke.py`를
**Tools > Execute Python Script**로 실행한다. `/Game/MinToonSmoke`에 네이티브 에셋을
생성한 다음 그 테스트 폴더만 정리한다. 폴더가 이미 존재하면 실행하지 않는다.
이 검사도 이미지 품질이나 셰이더 컴파일 성공을 대신하지 않는다.

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

초기 작성 시 기록한 참고 링크 — 대상 버전과 API의 재확인이 필요함:

- [UE 5.8 release notes — Substrate NPR Shading](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US)
- [Substrate Toon BSDF C++ reference](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UMaterialExpressionSubstrateToon-?lang=en-US)
- [ToonProfile / native settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ToonProfileStruct)
- [MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary)
- [MaterialProperty / Front Material](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialProperty.html)
- [Python initialization from a plugin](https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python?lang=en-US)
- [Epic Games Japan — Blendable/Adaptive GBuffer settings](https://www.docswell.com/s/EpicGamesJapan/K8N2G7-2026-04-03-230956)
