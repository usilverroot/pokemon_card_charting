import { Linking, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

export default function CardDetailScreen({ card, onBack, onAddToBinder, onRemoveFromBinder, isInBinder }) {
  if (!card) return null;

  const toggleBinder = () => {
    if (isInBinder) {
      onRemoveFromBinder?.(card.card_id);
    } else {
      onAddToBinder?.(card);
    }
  };

  const openDetailUrl = () => {
    if (card.detail_url) {
      Linking.openURL(card.detail_url).catch(() => {});
    }
  };

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <Ionicons name="chevron-back" size={22} color="#e8f1ff" />
          <Text style={styles.backText}>뒤로</Text>
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.imageWrap}>
          {card.image_url ? (
            <Image source={{ uri: card.image_url }} style={styles.image} contentFit="contain" />
          ) : (
            <View style={[styles.image, styles.imagePlaceholder]}>
              <Ionicons name="image-outline" size={32} color="#5b6673" />
            </View>
          )}
        </View>

        <Text style={styles.cardName}>{card.name || "이름 미확인"}</Text>

        <View style={styles.infoPanel}>
          <InfoRow label="카드 번호" value={card.card_number} />
          <InfoRow label="세트 코드" value={card.set_code} />
          <InfoRow label="레어도" value={card.rarity} />
          <InfoRow label="타입" value={card.card_type || card.type} />
          <InfoRow label="분류" value={card.category || card.classification} />
          <InfoRow label="일러스트레이터" value={card.illustrator} />
        </View>

        {card.detail_url ? (
          <Pressable style={styles.linkRow} onPress={openDetailUrl}>
            <Ionicons name="open-outline" size={16} color="#f5d451" />
            <Text style={styles.linkText} numberOfLines={1}>
              원본 페이지 열기
            </Text>
          </Pressable>
        ) : null}

        <View style={styles.placeholderPanel}>
          <Text style={styles.placeholderTitle}>참고 시세</Text>
          <Text style={styles.placeholderText}>시세 데이터 준비 중</Text>
          <Text style={styles.placeholderSubText}>최근 거래 기반 참고 가격을 표시할 예정입니다.</Text>
        </View>

        <View style={styles.placeholderPanel}>
          <Text style={styles.placeholderTitle}>가격 추이</Text>
          <View style={styles.chartPlaceholder}>
            <Ionicons name="trending-up-outline" size={26} color="#394653" />
          </View>
          <Text style={styles.placeholderSubText}>가격 추이 데이터가 준비되면 이 영역에 표시됩니다.</Text>
        </View>
      </ScrollView>

      <View style={styles.actionBar}>
        <Pressable
          style={[styles.binderButton, isInBinder && styles.binderButtonActive]}
          onPress={toggleBinder}
        >
          <Ionicons
            name={isInBinder ? "checkmark-circle" : "add-circle-outline"}
            size={20}
            color={isInBinder ? "#101418" : "#101418"}
          />
          <Text style={styles.binderButtonText}>
            {isInBinder ? "바인더에 추가됨 (탭하여 제거)" : "바인더에 추가"}
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue} numberOfLines={1}>
        {value || "-"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#101418",
  },
  header: {
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  backButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingVertical: 6,
    paddingHorizontal: 6,
    alignSelf: "flex-start",
  },
  backText: {
    color: "#e8f1ff",
    fontSize: 15,
    fontWeight: "600",
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 120,
    gap: 16,
  },
  imageWrap: {
    width: "100%",
    aspectRatio: 6.3 / 8.8,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "#07090c",
    alignSelf: "center",
    maxWidth: 320,
  },
  image: {
    width: "100%",
    height: "100%",
  },
  imagePlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  cardName: {
    color: "#f8fbff",
    fontSize: 22,
    fontWeight: "800",
    textAlign: "center",
  },
  infoPanel: {
    backgroundColor: "#161d24",
    borderRadius: 10,
    padding: 14,
    gap: 10,
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  infoLabel: {
    color: "#7c8896",
    fontSize: 13,
  },
  infoValue: {
    color: "#e8f1ff",
    fontSize: 14,
    fontWeight: "600",
    flexShrink: 1,
    textAlign: "right",
  },
  linkRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "center",
  },
  linkText: {
    color: "#f5d451",
    fontSize: 14,
    fontWeight: "600",
  },
  placeholderPanel: {
    backgroundColor: "#161d24",
    borderRadius: 10,
    padding: 14,
    gap: 6,
  },
  placeholderTitle: {
    color: "#f8fbff",
    fontSize: 15,
    fontWeight: "800",
  },
  placeholderText: {
    color: "#c6d3df",
    fontSize: 14,
    fontWeight: "700",
    marginTop: 4,
  },
  placeholderSubText: {
    color: "#7c8896",
    fontSize: 13,
    lineHeight: 18,
  },
  chartPlaceholder: {
    height: 100,
    borderRadius: 8,
    backgroundColor: "#0e1318",
    alignItems: "center",
    justifyContent: "center",
    marginVertical: 4,
    borderWidth: 1,
    borderColor: "#27313b",
    borderStyle: "dashed",
  },
  actionBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 24,
    backgroundColor: "#101418",
    borderTopWidth: 1,
    borderTopColor: "#27313b",
  },
  binderButton: {
    minHeight: 52,
    borderRadius: 8,
    backgroundColor: "#f5d451",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  binderButtonActive: {
    backgroundColor: "#8fe3a5",
  },
  binderButtonText: {
    color: "#101418",
    fontSize: 15,
    fontWeight: "800",
  },
});
