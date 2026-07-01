import { API_BASE_URL } from "../config";

/**
 * 카드 후보 조회.
 * 현재는 /cards/recognize-candidates 를 카드 찾기 화면에서도 재사용한다.
 * 백엔드에 전용 검색 API가 생기면 이 함수 내부만 교체하면 된다.
 */
export async function fetchCardCandidates({
  name = "",
  number = "",
  suffix = "",
  rarity = "",
  setCode = "",
} = {}) {
  const params = new URLSearchParams();
  const normalizedNumber = number.trim();
  let numberValue = normalizedNumber;
  let suffixValue = suffix.trim();

  if (normalizedNumber.includes("/")) {
    const [mainNumber, rest] = normalizedNumber.split("/");
    numberValue = mainNumber.trim();

    const restParts = rest.trim().split(/\s+/);
    suffixValue = suffixValue || restParts[0] || "";
    if (!rarity.trim() && restParts[1]) {
      rarity = restParts[1];
    }
  }

  if (name.trim()) params.append("name", name.trim());
  if (numberValue) params.append("number", numberValue);
  if (suffixValue) params.append("suffix", suffixValue);
  if (rarity.trim()) params.append("rarity", rarity.trim());
  if (setCode.trim()) params.append("set_code", setCode.trim());

  const url = `${API_BASE_URL}/cards/recognize-candidates?${params.toString()}`;

  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`카드 조회 실패 (status ${response.status})`);
  }

  const data = await response.json();
  return data?.results ?? data?.cards?.results ?? [];
}

/**
 * 인식 테스트 API가 반환하는 debug_images 상대 경로를 절대 URL로 변환.
 * cacheKey를 넘기면 캐시 버스팅용 쿼리스트링이 붙는다.
 */
export function buildDebugImageUrl(path, cacheKey = "") {
  if (!path) return null;
  return `${API_BASE_URL}${path}${cacheKey ? `?t=${cacheKey}` : ""}`;
}

export { API_BASE_URL };
