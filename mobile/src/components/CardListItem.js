import { Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

export default function CardListItem({ card, onPress }) {
  return (
    <Pressable style={styles.cardRow} onPress={() => onPress?.(card)}>
      {card.image_url ? (
        <Image source={{ uri: card.image_url }} style={styles.cardThumb} contentFit="cover" />
      ) : (
        <View style={[styles.cardThumb, styles.cardThumbPlaceholder]}>
          <Ionicons name="image-outline" size={18} color="#7c8896" />
        </View>
      )}

      <View style={styles.cardInfo}>
        <Text style={styles.cardName} numberOfLines={1}>
          {card.name || "이름 미확인"}
        </Text>
        <Text style={styles.cardMeta} numberOfLines={1}>
          {card.card_number || "-"} · {card.set_code || "-"} · {card.rarity || "-"}
        </Text>
        {typeof card.name_match_score === "number" ? (
          <Text style={styles.cardMeta}>이름 유사도 {card.name_match_score}</Text>
        ) : null}
      </View>

      <Ionicons name="chevron-forward" size={18} color="#7c8896" />
    </Pressable>
  );
}

const styles = StyleSheet.create({
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
  cardThumbPlaceholder: {
    alignItems: "center",
    justifyContent: "center",
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
