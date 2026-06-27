import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { Image } from "expo-image";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";

import { API_BASE_URL } from "./src/config";

const CARD_RATIO = 6.3 / 8.8;

export default function App() {
  const cameraRef = useRef(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [photo, setPhoto] = useState(null);
  const [isTakingPhoto, setIsTakingPhoto] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [recognitionResult, setRecognitionResult] = useState(null);

  const normalizePhoto = (nextPhoto, source = "camera") => ({
    uri: nextPhoto.uri,
    width: nextPhoto.width,
    height: nextPhoto.height,
    source,
  });

  const takePhoto = async () => {
    if (!cameraRef.current || isTakingPhoto) {
      return;
    }

    setIsTakingPhoto(true);
    setRecognitionResult(null);

    try {
      const nextPhoto = await cameraRef.current.takePictureAsync({
        quality: 0.9,
        skipProcessing: false,
      });
      setPhoto(normalizePhoto(nextPhoto, "camera"));
    } catch (error) {
      Alert.alert("촬영 실패", "사진을 촬영하지 못했습니다.");
    } finally {
      setIsTakingPhoto(false);
    }
  };

  const uploadPhoto = async () => {
    if (!photo?.uri || isUploading) {
      return;
    }

    setIsUploading(true);
    setRecognitionResult(null);

    const formData = new FormData();
    formData.append("file", {
      uri: photo.uri,
      name: "card.jpg",
      type: "image/jpeg",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/recognition/scan-and-ocr-test`, {
        method: "POST",
        body: formData,
        headers: {
          Accept: "application/json",
        },
      });

      const data = await response.json();

      if (!data.ok) {
        Alert.alert("스캔 실패", data.message || "카드 이미지를 처리하지 못했습니다.");
        return;
      }

      setRecognitionResult(data);
    } catch (error) {
      Alert.alert(
        "서버 연결 실패",
        "iOS 시뮬레이터는 127.0.0.1:8010을 사용합니다. 실기기는 Mac의 같은 Wi-Fi IP로 서버 주소를 바꿔주세요.",
      );
    } finally {
      setIsUploading(false);
    }
  };

  if (!permission) {
    return (
      <Screen>
        <ActivityIndicator color="#e8f1ff" />
      </Screen>
    );
  }

  if (!permission.granted) {
    return (
      <Screen>
        <View style={styles.permissionPanel}>
          <Ionicons name="camera-outline" size={42} color="#e8f1ff" />
          <Text style={styles.title}>카메라 권한이 필요합니다</Text>
          <Text style={styles.body}>카드 외곽선을 프레임에 맞춰 촬영하면 서버에서 스캔 보정을 진행합니다.</Text>
          <Pressable style={styles.primaryButton} onPress={requestPermission}>
            <Text style={styles.primaryButtonText}>권한 허용</Text>
          </Pressable>
        </View>
      </Screen>
    );
  }

  if (photo) {
    const scanResult = recognitionResult?.scan;
    const ocrResult = recognitionResult?.ocr;
    const cards = recognitionResult?.cards?.results ?? [];
    const cacheKey = recognitionResult ? Date.now() : "";
    const imageUrl = (path) => `${API_BASE_URL}${path}?t=${cacheKey}`;

    return (
      <Screen>
        <ScrollView style={styles.resultScroll} contentContainerStyle={styles.resultContent}>
          <View style={styles.preview}>
            <Image source={{ uri: photo.uri }} style={styles.previewImage} contentFit="contain" />
          </View>

          <View style={styles.resultPanel}>
            {scanResult ? (
              <>
                <Text style={styles.resultTitle}>인식 테스트 완료</Text>
                <Text style={styles.resultText}>
                  {scanResult.detected ? "외곽선 검출" : "중앙 보정"} · 신뢰도 {scanResult.confidence}
                </Text>
                <Text style={styles.resultText}>
                  {scanResult.width} x {scanResult.height}
                </Text>
                <Text style={styles.resultText}>{scanResult.message}</Text>
              </>
            ) : (
              <>
                <Text style={styles.resultTitle}>촬영 이미지 확인</Text>
                <Text style={styles.resultText}>이 이미지를 서버로 보내 카드 보정과 OCR 테스트를 실행합니다.</Text>
              </>
            )}
          </View>

          {recognitionResult?.debug_images ? (
            <View style={styles.imageSection}>
              <Text style={styles.sectionTitle}>보정된 사진</Text>
              <Image
                source={{ uri: imageUrl(recognitionResult.debug_images.normalized) }}
                style={styles.normalizedImage}
                contentFit="contain"
              />
              <Text style={styles.sectionTitle}>OCR crop</Text>
              <View style={styles.cropGrid}>
                <DebugImage label="하단 gray" uri={imageUrl(recognitionResult.debug_images.ocr_bottom_gray || recognitionResult.debug_images.ocr_bottom)} />
                <DebugImage label="하단 CLAHE" uri={imageUrl(recognitionResult.debug_images.ocr_bottom_clahe || recognitionResult.debug_images.ocr_bottom)} />
                <DebugImage label="하단 adaptive" uri={imageUrl(recognitionResult.debug_images.ocr_bottom_adaptive || recognitionResult.debug_images.ocr_bottom)} />
                <DebugImage label="하단 inverted" uri={imageUrl(recognitionResult.debug_images.ocr_bottom_inverted || recognitionResult.debug_images.ocr_bottom)} />
                <DebugImage label="상단 이름" uri={imageUrl(recognitionResult.debug_images.ocr_name)} />
                <DebugImage label="에너지" uri={imageUrl(recognitionResult.debug_images.ocr_energy)} />
              </View>
            </View>
          ) : null}

          {ocrResult ? (
            <View style={styles.ocrPanel}>
              <Text style={styles.sectionTitle}>OCR 결과</Text>
              <Text style={styles.resultText}>
                번호 {ocrResult.parsed?.number || "-"} / suffix {ocrResult.parsed?.suffix || "-"} / 레어도{" "}
                {ocrResult.parsed?.rarity || "-"}
              </Text>
              <Text style={styles.resultText}>하단: {(ocrResult.bottom_lines || []).join(" · ") || "-"}</Text>
              <Text style={styles.resultText}>이름: {(ocrResult.name_lines || []).join(" · ") || "-"}</Text>
            </View>
          ) : null}

          {recognitionResult?.cards ? (
            <View style={styles.cardsPanel}>
              <Text style={styles.sectionTitle}>카드 조회 결과 {recognitionResult.cards.count}</Text>
              {cards.length > 0 ? (
                cards.slice(0, 5).map((card) => (
                  <View style={styles.cardRow} key={card.card_id}>
                    {card.image_url ? (
                      <Image source={{ uri: card.image_url }} style={styles.cardThumb} contentFit="cover" />
                    ) : null}
                    <View style={styles.cardInfo}>
                      <Text style={styles.cardName}>{card.name}</Text>
                      <Text style={styles.cardMeta}>
                        {card.card_number} · {card.set_code || "-"} · {card.rarity || "-"}
                      </Text>
                      {typeof card.name_match_score === "number" ? (
                        <Text style={styles.cardMeta}>이름 유사도 {card.name_match_score}</Text>
                      ) : null}
                    </View>
                  </View>
                ))
              ) : (
                <Text style={styles.resultText}>조회된 카드가 없습니다.</Text>
              )}
            </View>
          ) : null}
        </ScrollView>

        <View style={styles.actionRow}>
          <IconButton icon="refresh" label="다시 촬영" onPress={() => {
            setPhoto(null);
            setRecognitionResult(null);
          }} />
          <Pressable style={styles.uploadButton} onPress={uploadPhoto} disabled={isUploading}>
            {isUploading ? (
              <ActivityIndicator color="#101418" />
            ) : (
              <>
                <Ionicons name="cloud-upload-outline" size={22} color="#101418" />
                <Text style={styles.uploadButtonText}>인식 테스트</Text>
              </>
            )}
          </Pressable>
        </View>
      </Screen>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <CameraView ref={cameraRef} style={styles.camera} facing="back">
        <SafeAreaView style={styles.cameraOverlay}>
          <View style={styles.topBar}>
            <Text style={styles.title}>카드 촬영</Text>
            <Text style={styles.body}>카드 테두리를 프레임 안쪽에 맞춰주세요.</Text>
          </View>

          <View style={styles.frameWrap}>
            <View style={styles.cardFrame}>
              <View style={[styles.corner, styles.cornerTopLeft]} />
              <View style={[styles.corner, styles.cornerTopRight]} />
              <View style={[styles.corner, styles.cornerBottomLeft]} />
              <View style={[styles.corner, styles.cornerBottomRight]} />
              <View style={styles.frameCenterLine} />
            </View>
          </View>

          <View style={styles.captureBar}>
            <Pressable style={styles.shutter} onPress={takePhoto} disabled={isTakingPhoto}>
              {isTakingPhoto ? <ActivityIndicator color="#101418" /> : <View style={styles.shutterInner} />}
            </Pressable>
          </View>
        </SafeAreaView>
      </CameraView>
    </View>
  );
}

function Screen({ children }) {
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      {children}
    </SafeAreaView>
  );
}

function IconButton({ icon, label, onPress }) {
  return (
    <Pressable style={styles.iconButton} onPress={onPress}>
      <Ionicons name={icon} size={22} color="#e8f1ff" />
      <Text style={styles.iconButtonText}>{label}</Text>
    </Pressable>
  );
}

function DebugImage({ label, uri }) {
  return (
    <View style={styles.cropItem}>
      <Text style={styles.cropLabel}>{label}</Text>
      <Image source={{ uri }} style={styles.cropImage} contentFit="contain" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#101418",
    justifyContent: "center",
    padding: 20,
  },
  container: {
    flex: 1,
    backgroundColor: "#101418",
  },
  camera: {
    flex: 1,
  },
  cameraOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.18)",
    justifyContent: "space-between",
  },
  topBar: {
    paddingHorizontal: 20,
    paddingTop: 18,
  },
  title: {
    color: "#f8fbff",
    fontSize: 24,
    fontWeight: "700",
  },
  body: {
    color: "#c6d3df",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 8,
  },
  frameWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  cardFrame: {
    height: "76%",
    aspectRatio: CARD_RATIO,
    borderColor: "rgba(255, 255, 255, 0.42)",
    borderWidth: 1,
    position: "relative",
  },
  corner: {
    position: "absolute",
    width: 34,
    height: 34,
    borderColor: "#f5d451",
  },
  cornerTopLeft: {
    top: -2,
    left: -2,
    borderTopWidth: 4,
    borderLeftWidth: 4,
  },
  cornerTopRight: {
    top: -2,
    right: -2,
    borderTopWidth: 4,
    borderRightWidth: 4,
  },
  cornerBottomLeft: {
    bottom: -2,
    left: -2,
    borderBottomWidth: 4,
    borderLeftWidth: 4,
  },
  cornerBottomRight: {
    bottom: -2,
    right: -2,
    borderBottomWidth: 4,
    borderRightWidth: 4,
  },
  frameCenterLine: {
    position: "absolute",
    left: "8%",
    right: "8%",
    top: "50%",
    height: 1,
    backgroundColor: "rgba(245, 212, 81, 0.28)",
  },
  captureBar: {
    alignItems: "center",
    paddingBottom: 34,
  },
  shutter: {
    width: 78,
    height: 78,
    borderRadius: 39,
    backgroundColor: "#f8fbff",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 5,
    borderColor: "rgba(255, 255, 255, 0.45)",
  },
  shutterInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: "#f5d451",
  },
  permissionPanel: {
    gap: 14,
  },
  primaryButton: {
    marginTop: 10,
    backgroundColor: "#f5d451",
    minHeight: 50,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButtonText: {
    color: "#101418",
    fontWeight: "700",
    fontSize: 16,
  },
  preview: {
    height: 260,
    borderRadius: 8,
    overflow: "hidden",
    backgroundColor: "#07090c",
  },
  previewImage: {
    flex: 1,
  },
  resultPanel: {
    paddingVertical: 18,
  },
  resultScroll: {
    flex: 1,
    marginBottom: 14,
  },
  resultContent: {
    paddingBottom: 10,
  },
  resultTitle: {
    color: "#f8fbff",
    fontSize: 19,
    fontWeight: "700",
  },
  resultText: {
    color: "#c6d3df",
    fontSize: 14,
    lineHeight: 20,
    marginTop: 6,
  },
  actionRow: {
    flexDirection: "row",
    gap: 12,
    alignItems: "center",
  },
  iconButton: {
    minHeight: 52,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#394653",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  iconButtonText: {
    color: "#e8f1ff",
    fontWeight: "700",
  },
  uploadButton: {
    flex: 1,
    minHeight: 52,
    borderRadius: 8,
    backgroundColor: "#f5d451",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  uploadButtonText: {
    color: "#101418",
    fontSize: 16,
    fontWeight: "800",
  },
  imageSection: {
    gap: 10,
    marginBottom: 16,
  },
  sectionTitle: {
    color: "#f8fbff",
    fontSize: 16,
    fontWeight: "800",
    marginTop: 4,
  },
  normalizedImage: {
    width: "100%",
    height: 420,
    borderRadius: 8,
    backgroundColor: "#07090c",
  },
  cropGrid: {
    gap: 10,
  },
  cropItem: {
    gap: 6,
  },
  cropLabel: {
    color: "#c6d3df",
    fontSize: 13,
    fontWeight: "700",
  },
  cropImage: {
    width: "100%",
    height: 120,
    borderRadius: 8,
    backgroundColor: "#07090c",
  },
  ocrPanel: {
    borderTopWidth: 1,
    borderTopColor: "#27313b",
    paddingTop: 14,
    marginBottom: 16,
  },
  cardsPanel: {
    borderTopWidth: 1,
    borderTopColor: "#27313b",
    paddingTop: 14,
    gap: 10,
  },
  cardRow: {
    minHeight: 82,
    borderRadius: 8,
    backgroundColor: "#161d24",
    flexDirection: "row",
    alignItems: "center",
    padding: 10,
    gap: 12,
  },
  cardThumb: {
    width: 46,
    height: 64,
    borderRadius: 4,
    backgroundColor: "#07090c",
  },
  cardInfo: {
    flex: 1,
    gap: 4,
  },
  cardName: {
    color: "#f8fbff",
    fontSize: 15,
    fontWeight: "800",
  },
  cardMeta: {
    color: "#c6d3df",
    fontSize: 13,
  },
});
