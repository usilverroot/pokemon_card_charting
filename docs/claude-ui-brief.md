# Claude UI Handoff Brief

이 문서는 Claude에게 UI 구현을 맡길 때 그대로 전달하기 위한 작업지시서다.

## 프로젝트 위치

```bash
cd /Users/a123/pokemon_card_charting
```

## 현재 상태

이 프로젝트는 포켓몬 카드 촬영/인식 앱이다.

현재 구현된 흐름:

1. iOS 앱에서 카드를 촬영한다.
2. 촬영 이미지를 FastAPI 서버로 업로드한다.
3. 서버가 카드 외곽선 검출, 투시 보정, 표준 리사이즈를 수행한다.
4. OCR 테스트 runner가 하단 번호/레어도, 상단 이름, 에너지 영역 crop을 만든다.
5. OCR 결과를 기반으로 DB에서 카드 후보를 조회한다.
6. 앱 화면에 보정된 사진, OCR crop, OCR 결과, 카드 후보를 표시한다.

현재 UI는 테스트용에 가깝고, `mobile/App.js`에 대부분의 화면이 한 파일로 들어 있다.

## Claude에게 맡길 목표

3주차 UI 1차 구현을 맡긴다.

핵심 목표:

- 카드 조회 화면 만들기
- 카드 상세 화면 만들기
- 바인더 화면 만들기
- 현재 촬영/인식 테스트 화면을 유지하되, 앱 안에서 자연스럽게 이동할 수 있게 만들기
- API가 아직 부족한 부분은 mock/local state로 먼저 구성하고, 추후 백엔드 연결이 쉬운 구조로 작성하기

## 우선순위

1. 앱 구조 정리
2. 카드 조회 UI
3. 카드 상세 UI
4. 바인더 추가/조회 UI
5. 인식 결과 화면 개선

## 현재 주요 파일

```text
mobile/App.js
mobile/src/config.js
mobile/package.json
backend/main.py
crawler/scripts/card_scan.py
crawler/scripts/ocr_test_runner.py
```

## 현재 API

### 인식 테스트

```http
POST /recognition/scan-and-ocr-test
```

앱에서 이미 사용 중이다.

반환 데이터 예시 구조:

```js
{
  ok: true,
  scan: {
    detected: true,
    method: "...",
    confidence: 0.86,
    width: 1002,
    height: 1400,
    message: "..."
  },
  ocr: {
    bottom_lines: [],
    name_lines: [],
    parsed: {
      number: "022",
      suffix: "083",
      rarity: "RR"
    },
    name_text: "...",
    energy: {}
  },
  cards: {
    count: 1,
    results: [
      {
        card_id: "...",
        name: "메가개굴닌자 ex",
        card_number: "022/083 RR",
        card_number_main: "022",
        card_number_suffix: "083",
        rarity: "RR",
        set_code: "M4",
        image_url: "...",
        detail_url: "..."
      }
    ]
  },
  debug_images: {
    normalized: "/recognition/last-scan/normalized",
    ocr_bottom_gray: "/recognition/last-scan/ocr-bottom-gray",
    ocr_bottom_clahe: "/recognition/last-scan/ocr-bottom-clahe",
    ocr_bottom_adaptive: "/recognition/last-scan/ocr-bottom-adaptive",
    ocr_bottom_inverted: "/recognition/last-scan/ocr-bottom-inverted",
    ocr_name: "/recognition/last-scan/ocr-name",
    ocr_energy: "/recognition/last-scan/ocr-energy"
  }
}
```

### 카드 후보 조회

```http
GET /cards/recognize-candidates?name=&number=&suffix=&rarity=&set_code=
```

현재는 후보 조회용이지만, 카드 검색 화면에서도 1차로 재사용 가능하다.

## UI 방향

앱은 운영 도구보다는 카드 컬렉션 앱에 가깝다. 다만 아직 베타 테스트 단계이므로 화려한 랜딩 페이지보다 실제 기능 화면을 우선한다.

원하는 톤:

- 어두운 배경 기반
- 카드 이미지가 잘 보이는 UI
- 촬영/조회/바인더 이동이 쉬운 구조
- 디버그 정보는 숨기지 말고 베타용으로 접을 수 있게 배치
- 카드 후보는 썸네일, 카드명, 번호, 세트, 레어도를 한눈에 보이게 표시

주의:

- 현재 OCR crop 표시 기능은 유지해야 한다.
- 보정된 사진 표시 기능은 유지해야 한다.
- 기존 인식 테스트 흐름을 깨면 안 된다.
- 아직 로그인 기능은 만들지 않는다.
- 서버 API가 부족하면 local state나 mock 데이터로 먼저 구현한다.

## 제안 화면 구조

### 탭

하단 탭 3개:

- 촬영
- 카드 찾기
- 바인더

### 촬영 탭

현재 `App.js`의 촬영/인식 테스트 흐름을 유지한다.

개선할 점:

- 인식 결과 카드 후보를 더 보기 좋게 표시
- 후보 카드를 누르면 카드 상세 화면으로 이동
- 디버그 이미지는 "OCR 디버그" 섹션으로 묶기

### 카드 찾기 탭

기능:

- 카드명 검색 입력
- 카드 번호 검색 입력
- 세트 코드 입력 또는 필터
- 레어도 필터
- 검색 결과 grid/list
- 결과 카드 클릭 시 상세 화면 이동

처음에는 `/cards/recognize-candidates` API를 재사용한다.

### 카드 상세 화면

표시:

- 큰 카드 이미지
- 카드명
- 카드 번호
- 세트 코드
- 레어도
- 타입/분류
- 일러스트레이터
- detail URL
- 참고 시세 영역 placeholder
- 가격 추이 영역 placeholder
- 바인더에 추가 버튼

가격 영역은 아직 실제 데이터가 없으므로 다음 문구와 mock UI만 둔다.

```text
시세 데이터 준비 중
최근 거래 기반 참고 가격을 표시할 예정입니다.
```

### 바인더 탭

기능:

- 바인더에 추가한 카드 목록 표시
- 카드 grid 형태
- 카드 클릭 시 상세 화면
- 삭제 버튼 또는 long press 삭제

저장은 우선 앱 local state로 구현한다. AsyncStorage는 필요하면 추가하되, 의존성 추가가 크면 local state만으로 충분하다.

## 구현 방식 제안

현재는 `mobile/App.js` 하나에 전부 있으므로, 다음처럼 나누는 것을 추천한다.

```text
mobile/App.js
mobile/src/config.js
mobile/src/api/cards.js
mobile/src/components/CardListItem.js
mobile/src/components/CardGridItem.js
mobile/src/components/DebugImage.js
mobile/src/screens/ScanScreen.js
mobile/src/screens/SearchScreen.js
mobile/src/screens/BinderScreen.js
mobile/src/screens/CardDetailScreen.js
```

단, 너무 큰 리팩터링으로 기존 기능이 깨질 것 같으면 `App.js` 안에서 screen state 방식으로 먼저 구현해도 된다.

## 성공 기준

Claude 작업 후 다음이 가능해야 한다.

1. 앱을 켜면 하단 탭 또는 유사한 네비게이션이 보인다.
2. 촬영 탭에서 기존 인식 테스트가 계속 동작한다.
3. 카드 후보를 누르면 상세 화면을 볼 수 있다.
4. 카드 찾기 탭에서 이름/번호로 카드 검색을 할 수 있다.
5. 카드 상세에서 바인더에 추가할 수 있다.
6. 바인더 탭에서 추가한 카드가 보인다.
7. 앱 번들이 깨지지 않는다.

검증 명령:

```bash
cd /Users/a123/pokemon_card_charting/mobile
npm run ios:export
```

## Claude에게 그대로 넣을 프롬프트

```text
너는 React Native/Expo 앱 UI 구현 담당이야.

프로젝트는 /Users/a123/pokemon_card_charting 에 있고, 모바일 앱은 mobile 폴더에 있어.

목표는 포켓몬 카드 인식 앱의 3주차 UI 1차 구현이야.

현재 mobile/App.js에는 촬영, 서버 업로드, 보정 이미지 표시, OCR crop 표시, 카드 후보 표시가 한 파일에 구현되어 있어. 이 기존 인식 테스트 흐름은 반드시 유지해줘.

추가로 구현할 화면은 다음이야.

1. 카드 찾기 화면
- 카드명 검색
- 카드 번호 검색
- 세트 코드/레어도 필터는 간단 입력으로 시작
- /cards/recognize-candidates API를 재사용
- 결과는 카드 이미지, 이름, 번호, 세트, 레어도 표시

2. 카드 상세 화면
- 큰 카드 이미지
- 카드명, 카드 번호, 세트 코드, 레어도, 타입, 분류, 일러스트레이터 표시
- 시세 영역 placeholder
- 가격 추이 영역 placeholder
- 바인더에 추가 버튼

3. 바인더 화면
- 바인더에 추가한 카드 grid 표시
- 우선 local state로 저장
- 카드 클릭 시 상세 화면
- 삭제 기능은 간단 버튼으로 구현해도 됨

4. 촬영/인식 결과 화면 개선
- 기존 보정 이미지와 OCR crop 표시 유지
- 카드 후보를 누르면 상세 화면으로 이동
- OCR 디버그 영역은 보기 좋게 정리

UI 톤은 어두운 배경, 카드 이미지 중심, 베타 테스트용으로 실용적인 화면이면 돼. 랜딩 페이지는 만들지 말고 바로 기능 화면이 나오게 해줘.

가능하면 파일을 분리해줘.
추천 구조:
- mobile/App.js
- mobile/src/api/cards.js
- mobile/src/components/CardListItem.js
- mobile/src/components/CardGridItem.js
- mobile/src/components/DebugImage.js
- mobile/src/screens/ScanScreen.js
- mobile/src/screens/SearchScreen.js
- mobile/src/screens/BinderScreen.js
- mobile/src/screens/CardDetailScreen.js

작업 후 npm run ios:export 가 통과하는지 확인해줘.
불필요한 iOS native 폴더, dist, node_modules, debug 이미지 파일은 커밋하지 마.
```

## Codex와 Claude 협업 방식

Claude가 UI 작업을 끝내면 Codex에게 다음을 요청한다.

```text
Claude가 UI 작업한 변경사항 검토해줘.
기존 촬영/인식 테스트 흐름이 깨졌는지 확인하고,
npm run ios:export를 실행해서 앱 번들 검증한 뒤,
문제가 있으면 수정하고 커밋/푸시해줘.
```

이렇게 하면 Claude는 UI 구현에 집중하고, Codex는 코드 리뷰/검증/백엔드 연결/커밋 정리를 담당할 수 있다.
